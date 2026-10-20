"""ML service on :8001 (Phase 6a): /predict/{asset}, /risk/{asset}, /health, /debug/{asset}.

    python -m uvicorn ml.api.service:app --port 8001        (from the repo root)

Serves baselines only; nothing is approved (D27, D33, D35). /predict and /risk bodies are validated against
docs/CONTRACT.md before they are returned (AGENTS rule 14). A violation raises ContractViolation, which the
server turns into a 500 and TestClient re-raises in tests. Extras only on /debug (D6). Assets are
case-insensitive; an asset not in config.ASSETS -> 404 ("not covered"); data that fails the serving gate
(missing CSV or report, failed report, or a report that does not match the CSV; D40) -> 503.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from ml import config
from ml.api.contract import check
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


@app.get("/debug/{asset}")
def debug(asset: str):
    return _serve(rs.debug, asset)
