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
    GET /models/{asset}            — A/B comparison: Prophet vs LSTM
    GET /assets                    — list supported assets
    POST /retrain/{asset}          — trigger fresh training (reloads cache)

Output contract for GET /prediction/{asset}:
    {
        "asset":          "btc",
        "prediction_30d": 106152.16,
        "lower_bound":    103476.59,
        "upper_bound":    108942.28,
        "confidence":     0.95,
        "risk_label":     "high",
        "risk_score":     67.2
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
from models.classifier  import RiskClassifier
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
SUPPORTED_ASSETS = ["btc", "eth"]


# ══════════════════════════════════════════════════════════════════════════════
#  Pydantic response models — strict typing for the backend contract
# ══════════════════════════════════════════════════════════════════════════════

class PredictionResponse(BaseModel):
    """Exact schema the backend expects from GET /prediction/{asset}."""
    asset:          str   = Field(..., example="btc")
    prediction_30d: float = Field(..., example=106152.16, description="30-day price forecast in USD")
    lower_bound:    float = Field(..., example=103476.59, description="80% prediction interval lower bound")
    upper_bound:    float = Field(..., example=108942.28, description="80% prediction interval upper bound")
    confidence:     float = Field(..., ge=0.0, le=1.0, example=0.95, description="Model confidence 0–1")
    risk_label:     str   = Field(..., example="high", description="low | medium | high")
    risk_score:     float = Field(..., ge=0.0, le=100.0, example=67.2, description="Continuous risk 0–100")

    class Config:
        json_schema_extra = {
            "example": {
                "asset":          "btc",
                "prediction_30d": 106152.16,
                "lower_bound":    103476.59,
                "upper_bound":    108942.28,
                "confidence":     0.95,
                "risk_label":     "high",
                "risk_score":     67.2,
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
        "for BTC and ETH. Powered by Prophet + RandomForest."
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
        description="Asset ticker (btc or eth)",
        example="btc",
    ),
) -> PredictionResponse:
    """
    Returns a 30-day price forecast and risk classification for the given asset.

    **Backend contract** — this is the exact response Person B's backend expects:

    - `prediction_30d` — predicted price 30 days from now (USD)
    - `lower_bound` / `upper_bound` — 80% prediction interval
    - `confidence` — model confidence 0–1 (derived from interval width)
    - `risk_label` — "low" | "medium" | "high"
    - `risk_score` — continuous 0–100 risk score (P(high) × 100)
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

        # 3. Get forecast prediction dict
        forecast = forecaster.predict()

        # 4. Get risk classification on latest data point
        risk = classifier.predict_latest(features_df)

    except Exception as exc:
        log.error("[%s] Prediction failed: %s", asset.upper(), exc)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error for '{asset}': {str(exc)}",
        )

    elapsed = time.perf_counter() - t0
    log.info(
        "[%s] Served prediction in %.3fs  "
        "pred=%.2f  risk=%s(%.1f)",
        asset.upper(), elapsed,
        forecast["prediction_30d"],
        risk["risk_label"], risk["risk_score"],
    )

    # 5. Merge and return — exact backend contract
    return PredictionResponse(
        asset          = asset,
        prediction_30d = forecast["prediction_30d"],
        lower_bound    = forecast["lower_bound"],
        upper_bound    = forecast["upper_bound"],
        confidence     = forecast["confidence"],
        risk_label     = risk["risk_label"],
        risk_score     = risk["risk_score"],
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
        description="Asset ticker (btc or eth)",
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


@app.post(
    "/retrain/{asset}",
    response_model=RetrainResponse,
    summary="Retrain models and reload cache",
    tags=["System"],
)
async def retrain(
    asset: str = FPath(..., description="Asset to retrain (btc or eth)", example="btc"),
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
