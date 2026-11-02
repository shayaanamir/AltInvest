from fastapi import APIRouter, HTTPException
from models.schemas import RiskResponse
from shared.mock_data import mock_risk
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
    Returns the risk engine's normalised score for the asset.

    Reads the latest doc from MongoDB `risk_scores`. For the ML-covered assets (BTC, ETH, SOL)
    nothing is substituted: 404 when no usable row is stored, 503 when the database is down
    (main.py). Other assets still fall back to mock data.
    """
    from db.queries import ML_COVERED_ASSETS, get_latest_risk

    asset = require_known_asset(asset)

    if asset in ML_COVERED_ASSETS:
        doc = get_latest_risk(asset)   # database errors become a 503 (main.py)
        if not doc or not isinstance(doc.get("risk_score"), (int, float)):
            raise HTTPException(status_code=404, detail=f"No risk score has been stored for {asset} yet.")
        return _map_risk(doc, asset)

    try:
        doc = get_latest_risk(asset)
        if doc and isinstance(doc.get("risk_score"), (int, float)):
            return _map_risk(doc, asset)
    except Exception as exc:
        print(f"[risk] MongoDB unavailable ({exc}), falling back to mock")

    result = mock_risk(asset)
    if isinstance(result, dict) and not result.get("note"):
        result["note"] = "mock data — no risk score found in DB yet"
    return result
