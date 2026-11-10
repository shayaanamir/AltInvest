"""ML service on :8001 (Phase 6a): /predict/{asset}, /risk/{asset}, /health, /debug/{asset}; Phase 6d adds
/debug/scorecard and /debug/live-scorecard.

    python -m uvicorn ml.api.service:app --port 8001        (from the repo root)

Serves baselines only; nothing is approved (D27, D33, D35). /predict and /risk bodies are validated against
docs/CONTRACT.md before they are returned (AGENTS rule 14). A violation raises ContractViolation, which the
server turns into a 500 and TestClient re-raises in tests. Extras only on /debug (D6). Assets are
case-insensitive; an asset not in config.ASSETS -> 404 ("not covered"); data that fails the serving gate
(missing CSV or report, failed report, or a report that does not match the CSV; D40) -> 503.
"""

import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from ml import config
from ml.api.contract import check
from ml.evaluation import live_score, scorecard
from ml.serving import nft_responses as nft
from ml.serving import responses as rs

app = FastAPI(title="AltInvest ML", version="v2")


def _serve(build, asset: str) -> dict:
    a = asset.lower()
    if a not in config.ASSETS:
        raise HTTPException(404, f"asset '{asset}' is not covered; covered: {[x.upper() for x in config.ASSETS]}")
    try:
        return build(a, datetime.now(timezone.utc))
    except rs.NotServable as e:
        raise HTTPException(503, str(e)) from None


@app.get("/predict/{asset}")
def predict(asset: str):
    return check("PredictionResponse", _serve(rs.predict, asset))


@app.get("/risk/{asset}")
def risk(asset: str):
    return check("RiskResponse", _serve(rs.risk, asset))


@app.get("/health")
def health():
    return {"status": "ok", "model_version": rs.model_versions(), "data_last_bar": rs.data_last_bars()}


@app.get("/debug/scorecard")
def debug_scorecard():
    """The offline scorecard, ml/reports/scorecard.json (Phase 6d). Declared before /debug/{asset}."""
    if not scorecard.OUT_JSON.exists():
        raise HTTPException(404, "scorecard.json not written yet; run python -m ml.evaluation.scorecard")
    return json.loads(scorecard.OUT_JSON.read_text(encoding="utf-8"))


@app.get("/debug/live-scorecard")
def debug_live_scorecard():
    """Forward scores of the logged served values (Phase 6d), computed now from the serving data."""
    return live_score.build()


def _serve_nft(build, *args):
    """NFT endpoints (Phase 10, D61): unknown slug -> 404, missing or unusable NFT data -> 503."""
    try:
        return build(*args)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0])) from None
    except rs.NotServable as e:
        raise HTTPException(503, str(e)) from None


@app.get("/nft/collections")
def nft_collections():
    return check("NftCollectionsResponse", _serve_nft(lambda: nft.collections(datetime.now(timezone.utc))))


@app.get("/nft/{slug}/floor")
def nft_floor(slug: str, days: int = 365):
    return check("NftFloorResponse", _serve_nft(nft.floor, slug, datetime.now(timezone.utc), days))


@app.get("/nft/{slug}/risk")
def nft_risk(slug: str):
    return check("NftRiskResponse", _serve_nft(nft.risk, slug, datetime.now(timezone.utc)))


@app.get("/nft/{slug}/sales")
def nft_sales(slug: str, days: int = 30):
    return check("NftSalesResponse", _serve_nft(nft.sales, slug, datetime.now(timezone.utc), days))


@app.get("/debug/{asset}")
def debug(asset: str):
    return _serve(rs.debug, asset)
