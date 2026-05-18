from fastapi import APIRouter, HTTPException
from models.schemas import RiskResponse
from shared.mock_data import mock_risk, SUPPORTED_ASSETS

router = APIRouter(tags=["Risk"])


@router.get("/risk/{asset}", response_model=RiskResponse)
def get_risk(asset: str):
    """
    Returns the risk engine's normalised score for the asset.

    Phase 1: returns mock data.
    Phase 3: this will call risk_engine/risk.py directly.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    # --- Phase 3: replace this block with the real call ---
    # from risk_engine.risk import calculate_risk
    # result = calculate_risk(asset)
    # return result
    # ------------------------------------------------------

    return mock_risk(asset)
