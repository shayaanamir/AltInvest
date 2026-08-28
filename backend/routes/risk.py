from fastapi import APIRouter, HTTPException
from models.schemas import RiskResponse
from shared.mock_data import mock_risk, SUPPORTED_ASSETS

router = APIRouter(tags=["Risk"])


def _map_risk(doc: dict, asset: str) -> dict:
    ts = doc.get("timestamp")
    if hasattr(ts, "strftime"):
        ts = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "asset": asset,
        "risk_score": doc.get("risk_score"),
        "volatility": doc.get("volatility"),
        "sharpe_ratio": doc.get("sharpe_ratio"),
        "timestamp": ts or "",
    }


@router.get("/risk/{asset}", response_model=RiskResponse)
def get_risk(asset: str):
    """
    Returns the risk engine's normalised score for the asset.

    Reads the latest doc from MongoDB `risk_scores`. Falls back to mock
    data if nothing's in the DB yet, or Mongo is down.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    try:
        from db.queries import get_latest_risk
        doc = get_latest_risk(asset)
        if doc:
            return _map_risk(doc, asset)
    except Exception as exc:
        print(f"[risk] MongoDB unavailable ({exc}), falling back to mock")

    result = mock_risk(asset)
    if isinstance(result, dict) and not result.get("note"):
        result["note"] = "mock data — no risk score found in DB yet"
    return result