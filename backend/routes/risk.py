from fastapi import APIRouter, HTTPException
from models.schemas import RiskResponse
from utils.asset_gate import require_known_asset
from utils.ml_rows import iso, with_stale_note

router = APIRouter(tags=["Risk"])


def _map_risk(doc: dict, asset: str) -> dict:
    ts = doc.get("timestamp")
    return {
        "asset": asset,
        "risk_score": doc.get("risk_score"),
        "volatility": doc.get("volatility"),
        "sharpe_ratio": doc.get("sharpe_ratio"),
        "timestamp": iso(ts),
        "note": with_stale_note(doc.get("note"), ts),
    }


@router.get("/risk/{asset}", response_model=RiskResponse)
def get_risk(asset: str):
    """
    Returns the ML service's risk score for the asset (ml/docs/DECISIONS.md D36, D82, D87).

    Reads the latest doc from MongoDB `risk_scores`, written only by the ML pull
    (controllers/ml_pull_controller.py) for db.queries.ML_COVERED_ASSETS. Nothing is substituted:
    404 for an asset the ML service does not cover (DAI) or when no usable row is stored yet,
    503 when the database is down (main.py).
    """
    from db.queries import ML_COVERED_ASSETS, get_latest_risk

    asset = require_known_asset(asset)
    if asset not in ML_COVERED_ASSETS:
        raise HTTPException(status_code=404, detail=f"{asset} is not covered by the risk model.")

    doc = get_latest_risk(asset)   # database errors become a 503 (main.py)
    if not doc or not isinstance(doc.get("risk_score"), (int, float)):
        raise HTTPException(status_code=404, detail=f"No risk score has been stored for {asset} yet.")
    return _map_risk(doc, asset)
