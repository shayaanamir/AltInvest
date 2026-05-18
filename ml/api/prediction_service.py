"""
prediction_service.py
─────────────────────────────────────────────────────────────────────────────
FastAPI prediction service for AltInvest ML pipeline.

Serves pre-trained Prophet + RandomForest + LSTM models via HTTP on port 8001.

Start command (from repo root):
    uvicorn ml.api.prediction_service:app --port 8001 --reload

Or from inside ml/:
    uvicorn api.prediction_service:app --port 8001 --reload

Endpoints
─────────
    GET /                          — health check
    GET /health                    — detailed system health
    GET /prediction/{asset}        — main prediction (Prophet) endpoint
    GET /risk/{asset}              — dedicated risk + Sharpe ratio endpoint
    GET /models/{asset}            — A/B comparison: Prophet vs LSTM
    GET /assets                    — list supported assets
    POST /retrain/{asset}          — trigger fresh training (reloads cache)

Callable functions (importable without HTTP)
────────────────────────────────────────────
    get_prediction(asset: str) -> dict   — mirrors GET /prediction/{asset}
    get_risk(asset: str)       -> dict   — mirrors GET /risk/{asset}

Output contract for GET /prediction/{asset}:
    {
        "asset":              "BTC",
        "predicted_price":    106152.16,
        "prediction_30d":     12.5,
        "lower_bound":        103476.59,
        "upper_bound":        108942.28,
        "confidence":         0.95,
        "risk_score":         32.8,         # contract score = 100 - internal
        "timestamp":          "2026-05-18T14:00:00Z",
        "trend":              "Bullish",    # Bullish | Bearish | Neutral
        "agreement":          true,          # Prophet & LSTM same direction?
        "signal":             "STRONG_BUY", # STRONG_BUY | STRONG_SELL | UNCERTAIN
        "boosted_confidence": 0.95,          # 0.95 if agreement else 0.60
        "ensemble_price":     106152.16     # confidence-weighted Prophet+LSTM avg
    }

Output contract for GET /risk/{asset}:
    {
        "asset":        "BTC",
        "risk_score":   32.8,   # [0,100] where higher = lower risk (better)
        "volatility":   0.18,
        "sharpe_ratio": 1.4,
        "timestamp":    "2026-05-18T14:00:00Z"
    }

Architecture
────────────
- Models are loaded ONCE at startup into ModelCache (not per request).
- On cache miss (asset not trained yet), the API triggers just-in-time training.
- /retrain/{asset} reloads the cache for a specific asset without restart.

Author : ML Engineer (Person C) — dev-shail branch
"""

import sys
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# ─── Path setup ───────────────────────────────────────────────────────────────
_ML_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ML_ROOT))

import uvicorn
from fastapi import FastAPI, HTTPException, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from models.forecaster  import ProphetForecaster
from models.classifier  import RiskClassifier, compute_sharpe_ratio
from models              import lstm as lstm_module
from features.feature_engineering import load_raw_csv, build_features
from training.train import run_training

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("prediction_service")

# ─── Constants ────────────────────────────────────────────────────────────────
ARTIFACTS_DIR   = _ML_ROOT / "models" / "artifacts"
SUPPORTED_ASSETS = ["btc", "eth", "sol"]


# ══════════════════════════════════════════════════════════════════════════════
#  Pydantic response models — strict typing for the backend contract
# ══════════════════════════════════════════════════════════════════════════════

class PredictionResponse(BaseModel):
    """Exact schema the backend expects from GET /prediction/{asset}."""
    # ── Core forecast fields (unchanged) ──────────────────────────────────────
    asset:           str   = Field(..., example="BTC")
    predicted_price: float = Field(..., example=106152.16, description="Predicted absolute price in USD after 30 days")
    prediction_30d:  float = Field(..., example=12.5,      description="% price change from current price over 30 days")
    lower_bound:     float = Field(..., example=103476.59, description="80% prediction interval lower bound")
    upper_bound:     float = Field(..., example=108942.28, description="80% prediction interval upper bound")
    confidence:      float = Field(..., ge=0.0, le=1.0, example=0.95, description="Model confidence 0–1")
    risk_score:      float = Field(..., ge=0.0, le=100.0, example=32.8,
                                  description="Contract risk score 0–100 where higher = lower risk (100 - internal score)")
    timestamp:       str   = Field(..., example="2026-05-18T14:00:00Z", description="UTC time of prediction")
    # ── Signal fields (Task A) ────────────────────────────────────────────────
    trend:              str  = Field(..., example="Bullish",
                                    description="Bullish if prediction_30d > 5, Bearish if < -5, else Neutral")
    agreement:          bool = Field(..., example=True,
                                    description="True if Prophet and LSTM predict the same direction")
    signal:             str  = Field(..., example="STRONG_BUY",
                                    description="STRONG_BUY | STRONG_SELL | UNCERTAIN")
    boosted_confidence: float = Field(..., ge=0.0, le=1.0, example=0.95,
                                     description="0.95 when models agree, 0.60 when they disagree")
    # ── Ensemble field (Task B) ───────────────────────────────────────────────
    ensemble_price:     float = Field(..., example=106152.16,
                                     description="Confidence-weighted average of Prophet and LSTM price forecasts")

    class Config:
        json_schema_extra = {
            "example": {
                "asset":              "BTC",
                "predicted_price":    106152.16,
                "prediction_30d":     12.5,
                "lower_bound":        103476.59,
                "upper_bound":        108942.28,
                "confidence":         0.95,
                "risk_score":         32.8,
                "timestamp":          "2026-05-18T14:00:00Z",
                "trend":              "Bullish",
                "agreement":          True,
                "signal":             "STRONG_BUY",
                "boosted_confidence": 0.95,
                "ensemble_price":     106152.16,
            }
        }


class RiskResponse(BaseModel):
    """Schema for GET /risk/{asset} — dedicated risk endpoint."""
    asset:        str   = Field(..., example="BTC")
    risk_score:   float = Field(
        ..., ge=0.0, le=100.0, example=32.8,
        description="Contract risk score [0,100] where HIGHER = LOWER risk (better)",
    )
    volatility:   float = Field(..., example=0.18, description="14-day rolling volatility (std of hourly log-returns)")
    sharpe_ratio: float = Field(..., example=1.4,  description="Annualised Sharpe ratio from daily returns")
    timestamp:    str   = Field(..., example="2026-05-18T14:00:00Z", description="UTC time of calculation")

    class Config:
        json_schema_extra = {
            "example": {
                "asset":        "BTC",
                "risk_score":   32.8,
                "volatility":   0.18,
                "sharpe_ratio": 1.4,
                "timestamp":    "2026-05-18T14:00:00Z",
            }
        }


class HealthResponse(BaseModel):
    status:          str
    loaded_assets:   list[str]
    artifacts_dir:   str
    supported_assets: list[str]


class ModelCompareResponse(BaseModel):
    """Side-by-side Prophet vs LSTM output for A/B evaluation."""
    asset:   str
    prophet: dict
    lstm:    Optional[dict] = Field(None, description="None if LSTM not yet trained for this asset")


class RetrainResponse(BaseModel):
    asset:   str
    status:  str
    message: str
    duration_sec: float


# ══════════════════════════════════════════════════════════════════════════════
#  Model Cache — singleton loaded at startup
# ══════════════════════════════════════════════════════════════════════════════

class ModelCache:
    """
    Holds one (forecaster, classifier, features_df) triplet per asset.

    Loading strategy:
    1. Try to load pre-trained .pkl artifacts (fast, ~0.1s)
    2. On cache miss, run full training pipeline and cache results
    3. /retrain endpoint invalidates + reloads a specific asset
    """

    def __init__(self):
        # { "btc": {"forecaster": ..., "classifier": ..., "features_df": ..., "lstm_report": ...} }
        self._cache: dict = {}

    def load_asset(self, asset: str) -> None:
        """Load Prophet, RF classifier, and LSTM report for an asset."""
        asset = asset.lower()
        log.info("[%s] Loading models into cache ...", asset.upper())

        forecaster_path  = ARTIFACTS_DIR / f"{asset}_prophet.pkl"
        classifier_path  = ARTIFACTS_DIR / f"{asset}_rf_classifier.pkl"
        lstm_report_path = ARTIFACTS_DIR / f"{asset}_lstm_report.json"

        # ── Forecaster ────────────────────────────────────────────────────
        if forecaster_path.exists():
            forecaster = ProphetForecaster.load(forecaster_path)
            log.info("[%s] Prophet loaded from artifact.", asset.upper())
        else:
            log.warning("[%s] No artifact found — training Prophet now ...", asset.upper())
            raw = load_raw_csv(asset)
            features_df = build_features(raw)
            asset_df = features_df[features_df["asset"] == asset].copy()
            forecaster = ProphetForecaster()
            forecaster.fit(asset_df)
            forecaster.save()

        # ── Classifier ────────────────────────────────────────────────────
        if classifier_path.exists():
            classifier = RiskClassifier.load(classifier_path)
            log.info("[%s] Classifier loaded from artifact.", asset.upper())
        else:
            log.warning("[%s] No artifact found — training Classifier now ...", asset.upper())
            raw = load_raw_csv(asset)
            features_df = build_features(raw)
            asset_df = features_df[features_df["asset"] == asset].copy()
            classifier = RiskClassifier()
            classifier.fit(asset_df)
            classifier.save()

        # ── Feature data (for classifier inference on latest row) ─────────
        raw = load_raw_csv(asset)
        features_df = build_features(raw)
        asset_df = features_df[features_df["asset"] == asset].copy()

        # ── LSTM report (optional — populated when lstm.py has been run) ──
        lstm_report = None
        if lstm_report_path.exists():
            import json
            with open(lstm_report_path) as f:
                lstm_report = json.load(f)
            log.info("[%s] LSTM report loaded from artifact.", asset.upper())
        else:
            log.info("[%s] No LSTM artifact found — run: python models/lstm.py --asset %s",
                     asset.upper(), asset)

        self._cache[asset] = {
            "forecaster":   forecaster,
            "classifier":   classifier,
            "features_df":  asset_df,
            "lstm_report":  lstm_report,
        }
        log.info("[%s] Cache loaded successfully.", asset.upper())

    def get(self, asset: str) -> dict:
        """Return cached models for asset. Raises KeyError if not loaded."""
        return self._cache[asset]

    def evict(self, asset: str) -> None:
        """Remove asset from cache (before reloading)."""
        self._cache.pop(asset, None)

    @property
    def loaded_assets(self) -> list[str]:
        return list(self._cache.keys())


# Global cache instance
cache = ModelCache()


# ══════════════════════════════════════════════════════════════════════════════
#  App lifecycle — load models once at startup
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all available model artifacts into cache at startup."""
    log.info("=" * 55)
    log.info("  AltInvest Prediction Service — starting up")
    log.info("  Artifacts dir: %s", ARTIFACTS_DIR)
    log.info("=" * 55)

    for asset in SUPPORTED_ASSETS:
        forecaster_path = ARTIFACTS_DIR / f"{asset}_prophet.pkl"
        classifier_path = ARTIFACTS_DIR / f"{asset}_rf_classifier.pkl"

        if forecaster_path.exists() or classifier_path.exists():
            try:
                cache.load_asset(asset)
            except Exception as exc:
                log.error("[%s] Failed to load — %s", asset.upper(), exc)
        else:
            log.warning(
                "[%s] No artifacts found. Run: python training/train.py --asset %s",
                asset.upper(), asset,
            )

    log.info("Startup complete. Loaded assets: %s", cache.loaded_assets)
    yield
    log.info("Shutting down prediction service.")


# ══════════════════════════════════════════════════════════════════════════════
#  FastAPI app
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AltInvest ML Prediction Service",
    description=(
        "Serves 30-day price forecasts and risk classifications "
        "for BTC, ETH, and SOL. Powered by Prophet + RandomForest."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Person B's backend to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten to backend URL in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "AltInvest ML Prediction Service", "status": "running", "port": 8001}


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    tags=["System"],
)
async def health():
    """
    Returns service health and which assets currently have loaded models.
    Use this to verify the service is ready before calling /prediction/{asset}.
    """
    return HealthResponse(
        status="healthy" if cache.loaded_assets else "degraded",
        loaded_assets=cache.loaded_assets,
        artifacts_dir=str(ARTIFACTS_DIR),
        supported_assets=SUPPORTED_ASSETS,
    )


@app.get(
    "/assets",
    summary="List supported assets",
    tags=["System"],
)
async def list_assets():
    """Returns which assets have trained models ready."""
    return {
        "supported":  SUPPORTED_ASSETS,
        "ready":      cache.loaded_assets,
        "not_ready":  [a for a in SUPPORTED_ASSETS if a not in cache.loaded_assets],
    }


@app.get(
    "/prediction/{asset}",
    response_model=PredictionResponse,
    summary="Get 30-day price prediction + risk classification",
    tags=["Prediction"],
    responses={
        200: {"description": "Prediction returned successfully"},
        404: {"description": "Asset not found or not supported"},
        503: {"description": "Model not loaded — run training first"},
    },
)
async def get_prediction(
    asset: str = FPath(
        ...,
        description="Asset ticker (btc, eth, or sol)",
        example="btc",
    ),
) -> PredictionResponse:
    """
    Returns a 30-day price forecast, risk classification, agreement signal,
    and ensemble price for the given asset.

    **New fields added to the contract:**

    - `trend` — direction derived from `prediction_30d`: Bullish / Bearish / Neutral
    - `agreement` — True if Prophet and LSTM predict the same price direction
    - `signal` — STRONG_BUY | STRONG_SELL | UNCERTAIN
    - `boosted_confidence` — 0.95 when models agree, 0.60 when they disagree
    - `ensemble_price` — confidence-weighted average of Prophet + LSTM price forecasts
    """
    asset = asset.lower()

    # 1. Validate asset name
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset}' is not supported. Supported: {SUPPORTED_ASSETS}",
        )

    # 2. Check cache
    if asset not in cache.loaded_assets:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Models for '{asset}' are not loaded. "
                f"Run: python training/train.py --asset {asset}  "
                f"then POST /retrain/{asset} to reload."
            ),
        )

    t0 = time.perf_counter()

    try:
        entry       = cache.get(asset)
        forecaster  = entry["forecaster"]
        classifier  = entry["classifier"]
        features_df = entry["features_df"]

        # 3. Prophet forecast
        forecast = forecaster.predict()

        # 4. Risk classification
        risk = classifier.predict_latest(features_df)

        # 5. LSTM result — try cache first, then live inference
        lstm_result = entry.get("lstm_report")
        if lstm_result is None:
            lstm_path     = ARTIFACTS_DIR / f"{asset}_lstm.keras"
            lstm_fallback = ARTIFACTS_DIR / f"{asset}_lstm_fallback.pkl"
            if lstm_path.exists() or lstm_fallback.exists():
                try:
                    lstm_result = lstm_module.predict(asset)
                    log.info("[%s] LSTM live inference for /prediction.", asset.upper())
                except Exception as exc:
                    log.warning("[%s] LSTM inference failed: %s — using None.", asset.upper(), exc)
                    lstm_result = None

    except Exception as exc:
        log.error("[%s] Prediction failed: %s", asset.upper(), exc)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error for '{asset}': {str(exc)}",
        )

    # ── Task A: Agreement signal ───────────────────────────────────────────────
    prophet_30d = forecast["prediction_30d"]   # % change

    # trend from Prophet direction
    if prophet_30d > 5:
        trend = "Bullish"
    elif prophet_30d < -5:
        trend = "Bearish"
    else:
        trend = "Neutral"

    # agreement requires both models to be available and same direction
    if lstm_result is not None:
        lstm_30d  = lstm_result.get("prediction_30d", 0.0)
        agreement = (prophet_30d > 0) == (lstm_30d > 0)   # same sign = same direction
    else:
        agreement = False
        lstm_30d  = None

    if agreement and trend == "Bullish":
        signal = "STRONG_BUY"
    elif agreement and trend == "Bearish":
        signal = "STRONG_SELL"
    else:
        signal = "UNCERTAIN"

    boosted_confidence = 0.95 if agreement else 0.60

    # ── Task B: Weighted ensemble price ───────────────────────────────────────
    prophet_price = forecast["predicted_price"]
    prophet_conf  = forecast.get("confidence", 0.95)

    if lstm_result is not None:
        lstm_price = lstm_result.get("predicted_price") or lstm_result.get("prediction_30d", prophet_price)
        lstm_conf  = lstm_result.get("confidence", 0.85)
        total_conf = prophet_conf + lstm_conf
        ensemble_price = round(
            (prophet_price * prophet_conf / total_conf) +
            (lstm_price    * lstm_conf    / total_conf),
            2,
        )
    else:
        ensemble_price = round(prophet_price, 2)   # fallback: Prophet only

    # ── Risk score inversion ──────────────────────────────────────────────────
    contract_risk_score = round(100.0 - risk["risk_score"], 1)

    elapsed = time.perf_counter() - t0
    log.info(
        "[%s] /prediction in %.3fs  $%.2f (%+.2f%%)  risk=%.1f  "
        "trend=%s  agreement=%s  signal=%s  ensemble=$%.2f",
        asset.upper(), elapsed,
        prophet_price, prophet_30d,
        contract_risk_score,
        trend, agreement, signal, ensemble_price,
    )

    return PredictionResponse(
        asset               = forecast["asset"],
        predicted_price     = prophet_price,
        prediction_30d      = prophet_30d,
        lower_bound         = forecast["lower_bound"],
        upper_bound         = forecast["upper_bound"],
        confidence          = prophet_conf,
        risk_score          = contract_risk_score,
        timestamp           = forecast["timestamp"],
        trend               = trend,
        agreement           = agreement,
        signal              = signal,
        boosted_confidence  = boosted_confidence,
        ensemble_price      = ensemble_price,
    )


@app.get(
    "/models/{asset}",
    response_model=ModelCompareResponse,
    summary="A/B comparison: Prophet vs LSTM forecasts",
    tags=["Prediction"],
    responses={
        200: {"description": "Both model results returned"},
        404: {"description": "Asset not supported"},
        503: {"description": "Prophet model not loaded"},
    },
)
async def compare_models(
    asset: str = FPath(
        ...,
        description="Asset ticker (btc, eth, or sol)",
        example="btc",
    ),
) -> ModelCompareResponse:
    """
    Returns side-by-side predictions from Prophet and LSTM for A/B evaluation.

    - **prophet** — always present (loaded at startup from .pkl artifact)
    - **lstm** — present only if `python models/lstm.py --asset {asset}` has been run

    Both share the same output schema so the backend can swap transparently:
        prediction_30d, lower_bound, upper_bound, confidence
    """
    asset = asset.lower()

    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset}' not supported. Supported: {SUPPORTED_ASSETS}",
        )

    if asset not in cache.loaded_assets:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Models for '{asset}' are not loaded. "
                f"Run: python training/train.py --asset {asset}"
            ),
        )

    entry      = cache.get(asset)
    forecaster = entry["forecaster"]

    # Prophet forecast
    try:
        prophet_result = forecaster.predict()
    except Exception as exc:
        log.error("[%s] Prophet prediction failed: %s", asset.upper(), exc)
        raise HTTPException(status_code=500, detail=f"Prophet error: {exc}")

    # LSTM — use cached report if available, otherwise attempt live inference
    lstm_result = entry.get("lstm_report")
    if lstm_result is None:
        lstm_path = ARTIFACTS_DIR / f"{asset}_lstm.keras"
        lstm_fallback = ARTIFACTS_DIR / f"{asset}_lstm_fallback.pkl"
        if lstm_path.exists() or lstm_fallback.exists():
            try:
                lstm_result = lstm_module.predict(asset)
                log.info("[%s] LSTM live inference complete.", asset.upper())
            except Exception as exc:
                log.warning("[%s] LSTM inference failed: %s", asset.upper(), exc)
                lstm_result = None

    log.info(
        "[%s] /models comparison served. Prophet=%.2f  LSTM=%s",
        asset.upper(),
        prophet_result["prediction_30d"],
        lstm_result["prediction_30d"] if lstm_result else "N/A",
    )

    return ModelCompareResponse(
        asset   = asset,
        prophet = prophet_result,
        lstm    = lstm_result,
    )


@app.get(
    "/risk/{asset}",
    response_model=RiskResponse,
    summary="Get dedicated risk metrics for an asset",
    tags=["Risk"],
    responses={
        200: {"description": "Risk metrics returned successfully"},
        404: {"description": "Asset not found or not supported"},
        503: {"description": "Model not loaded — run training first"},
    },
)
async def get_risk_endpoint(
    asset: str = FPath(
        ...,
        description="Asset ticker (btc, eth, or sol)",
        example="btc",
    ),
) -> RiskResponse:
    """
    Returns dedicated risk metrics for the given asset.

    **Contract note** — ``risk_score`` range is [0, 100] where:
    - **higher score = lower risk (better)**
    - This is the INVERSE of the internal classifier score.

    ``volatility`` is the most recent 14-day rolling std of 1-hour log-returns.
    ``sharpe_ratio`` is annualised using daily returns and 252 trading days.
    """
    asset = asset.lower()

    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset}' is not supported. Supported: {SUPPORTED_ASSETS}",
        )

    if asset not in cache.loaded_assets:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Models for '{asset}' are not loaded. "
                f"Run: python training/train.py --asset {asset}"
            ),
        )

    try:
        entry       = cache.get(asset)
        classifier  = entry["classifier"]
        features_df = entry["features_df"]
        forecast    = entry["forecaster"].predict()

        risk         = classifier.predict_latest(features_df)
        sharpe       = risk.get("sharpe_ratio", compute_sharpe_ratio(features_df))
        volatility   = round(float(features_df["volatility_14d"].iloc[-1]), 6)

        # Contract inversion: higher = lower risk
        contract_risk_score = round(100.0 - risk["risk_score"], 1)

    except Exception as exc:
        log.error("[%s] Risk calculation failed: %s", asset.upper(), exc)
        raise HTTPException(
            status_code=500,
            detail=f"Risk calculation error for '{asset}': {str(exc)}",
        )

    log.info(
        "[%s] /risk served  contract_score=%.1f  volatility=%.6f  sharpe=%.4f",
        asset.upper(), contract_risk_score, volatility, sharpe,
    )

    return RiskResponse(
        asset        = asset.upper(),
        risk_score   = contract_risk_score,
        volatility   = volatility,
        sharpe_ratio = sharpe,
        timestamp    = forecast["timestamp"],
    )


@app.post(
    "/retrain/{asset}",
    response_model=RetrainResponse,
    summary="Retrain models and reload cache",
    tags=["System"],
)
async def retrain(
    asset: str = FPath(..., description="Asset to retrain (btc, eth, or sol)", example="btc"),
):
    """
    Triggers full retraining for the given asset and reloads the model cache.

    Use this when:
    - New data has arrived from Person A
    - You want to refresh the model without restarting the server

    This is a synchronous operation (~5-10s). In production this would be
    dispatched to a background task queue (Celery/RQ).
    """
    asset = asset.lower()

    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset}' not supported. Supported: {SUPPORTED_ASSETS}",
        )

    log.info("[%s] Retrain triggered via API ...", asset.upper())
    t0 = time.perf_counter()

    try:
        # Run full pipeline
        run_training(asset=asset, dry_run=False)

        # Evict old cached models + reload fresh artifacts
        cache.evict(asset)
        cache.load_asset(asset)

        elapsed = round(time.perf_counter() - t0, 2)
        log.info("[%s] Retrain + cache reload complete in %.1fs", asset.upper(), elapsed)

        return RetrainResponse(
            asset=asset,
            status="success",
            message=f"Models retrained and reloaded for {asset.upper()}.",
            duration_sec=elapsed,
        )

    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        log.error("[%s] Retrain failed: %s", asset.upper(), exc)
        raise HTTPException(
            status_code=500,
            detail=f"Retrain failed for '{asset}': {str(exc)}",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Callable Python functions — importable without HTTP server
# ══════════════════════════════════════════════════════════════════════════════
#
#  Person B can use these directly:
#
#      from ml.api.prediction_service import get_prediction, get_risk
#
#      result = get_prediction("BTC")
#      risk   = get_risk("BTC")
#
#  Both functions lazy-load the model cache on first call (same as the API
#  startup does) so they are safe to import in any Python context.
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_asset_loaded(asset: str) -> None:
    """
    Load model artifacts into the global cache if not already present.
    Safe to call multiple times — noop if already cached.
    """
    if asset not in cache.loaded_assets:
        log.info(
            "[%s] Cache miss on callable — loading models now ...", asset.upper()
        )
        cache.load_asset(asset)


def get_prediction(asset: str) -> dict:
    """
    Return a 30-day price forecast + risk classification for *asset*.

    This is the **callable** equivalent of ``GET /prediction/{asset}``.
    Person B can import and call this directly without running the HTTP server:

        from ml.api.prediction_service import get_prediction
        result = get_prediction("BTC")

    Parameters
    ----------
    asset : str
        Asset ticker — ``"btc"``, ``"eth"``, or ``"sol"`` (case-insensitive).

    Returns
    -------
    dict matching PredictionResponse:
        {
            "asset":              str,
            "predicted_price":    float,
            "prediction_30d":     float,   # % change
            "lower_bound":        float,
            "upper_bound":        float,
            "confidence":         float,
            "risk_score":         float,   # 0–100, HIGHER = LOWER risk (contract)
            "timestamp":          str,
            "trend":              str,     # "Bullish" | "Bearish" | "Neutral"
            "agreement":          bool,    # Prophet & LSTM same direction?
            "signal":             str,     # "STRONG_BUY" | "STRONG_SELL" | "UNCERTAIN"
            "boosted_confidence": float,   # 0.95 if agreement else 0.60
            "ensemble_price":     float,   # confidence-weighted Prophet+LSTM avg
        }

    Raises
    ------
    ValueError    — if asset is not supported.
    RuntimeError  — if models cannot be loaded.
    """
    asset = asset.lower()

    if asset not in SUPPORTED_ASSETS:
        raise ValueError(
            f"Asset '{asset}' not supported. Supported: {SUPPORTED_ASSETS}"
        )

    _ensure_asset_loaded(asset)

    entry       = cache.get(asset)
    forecaster  = entry["forecaster"]
    classifier  = entry["classifier"]
    features_df = entry["features_df"]

    forecast = forecaster.predict()
    risk     = classifier.predict_latest(features_df)

    # LSTM — cache first, then live
    lstm_result = entry.get("lstm_report")
    if lstm_result is None:
        lstm_path     = ARTIFACTS_DIR / f"{asset}_lstm.keras"
        lstm_fallback = ARTIFACTS_DIR / f"{asset}_lstm_fallback.pkl"
        if lstm_path.exists() or lstm_fallback.exists():
            try:
                lstm_result = lstm_module.predict(asset)
            except Exception:
                lstm_result = None

    # Agreement signal
    prophet_30d = forecast["prediction_30d"]
    if prophet_30d > 5:
        trend = "Bullish"
    elif prophet_30d < -5:
        trend = "Bearish"
    else:
        trend = "Neutral"

    if lstm_result is not None:
        lstm_30d  = lstm_result.get("prediction_30d", 0.0)
        agreement = (prophet_30d > 0) == (lstm_30d > 0)
    else:
        agreement = False

    if agreement and trend == "Bullish":
        signal = "STRONG_BUY"
    elif agreement and trend == "Bearish":
        signal = "STRONG_SELL"
    else:
        signal = "UNCERTAIN"

    boosted_confidence = 0.95 if agreement else 0.60

    # Weighted ensemble price
    prophet_price = forecast["predicted_price"]
    prophet_conf  = forecast.get("confidence", 0.95)

    if lstm_result is not None:
        lstm_price = lstm_result.get("predicted_price") or lstm_result.get("prediction_30d", prophet_price)
        lstm_conf  = lstm_result.get("confidence", 0.85)
        total_conf = prophet_conf + lstm_conf
        ensemble_price = round(
            (prophet_price * prophet_conf / total_conf) +
            (lstm_price    * lstm_conf    / total_conf),
            2,
        )
    else:
        ensemble_price = round(prophet_price, 2)

    # Contract risk inversion
    contract_risk_score = round(100.0 - risk["risk_score"], 1)

    return {
        "asset":              forecast["asset"],
        "predicted_price":    prophet_price,
        "prediction_30d":     prophet_30d,
        "lower_bound":        forecast["lower_bound"],
        "upper_bound":        forecast["upper_bound"],
        "confidence":         prophet_conf,
        "risk_score":         contract_risk_score,
        "timestamp":          forecast["timestamp"],
        "trend":              trend,
        "agreement":          agreement,
        "signal":             signal,
        "boosted_confidence": boosted_confidence,
        "ensemble_price":     ensemble_price,
    }


def get_risk(asset: str) -> dict:
    """
    Return dedicated risk metrics for *asset*.

    This is the **callable** equivalent of ``GET /risk/{asset}``:

        from ml.api.prediction_service import get_risk
        result = get_risk("BTC")

    Parameters
    ----------
    asset : str
        Asset ticker — ``"btc"``, ``"eth"``, or ``"sol"`` (case-insensitive).

    Returns
    -------
    dict matching RiskResponse:
        {
            "asset":        str,
            "risk_score":   float,  # [0,100] HIGHER = LOWER risk (contract)
            "volatility":   float,  # 14-day rolling std of 1h log-returns
            "sharpe_ratio": float,  # annualised Sharpe from daily returns
            "timestamp":    str,
        }

    Raises
    ------
    ValueError    — if asset is not supported.
    RuntimeError  — if models cannot be loaded.
    """
    asset = asset.lower()

    if asset not in SUPPORTED_ASSETS:
        raise ValueError(
            f"Asset '{asset}' not supported. Supported: {SUPPORTED_ASSETS}"
        )

    _ensure_asset_loaded(asset)

    entry       = cache.get(asset)
    classifier  = entry["classifier"]
    features_df = entry["features_df"]
    forecast    = entry["forecaster"].predict()

    risk       = classifier.predict_latest(features_df)
    sharpe     = risk.get("sharpe_ratio", compute_sharpe_ratio(features_df))
    volatility = round(float(features_df["volatility_14d"].iloc[-1]), 6)

    # Contract inversion: higher = lower risk
    contract_risk_score = round(100.0 - risk["risk_score"], 1)

    return {
        "asset":        asset.upper(),
        "risk_score":   contract_risk_score,
        "volatility":   volatility,
        "sharpe_ratio": sharpe,
        "timestamp":    forecast["timestamp"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Dev entrypoint  —  python api/prediction_service.py
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "api.prediction_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )

