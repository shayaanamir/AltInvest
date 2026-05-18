from fastapi import APIRouter, HTTPException
from models.schemas import AAIResponse
from shared.mock_data import mock_prediction, mock_sentiment, mock_risk, SUPPORTED_ASSETS
from controllers.aai_controller import compute_aai_response

router = APIRouter(tags=["AAI"])


@router.get("/aai/{asset}", response_model=AAIResponse)
def get_aai(asset: str):
    """
    Returns the full AAI composite score for the asset.

    Orchestration order:
    1. Fetch prediction score
    2. Fetch sentiment score
    3. Fetch risk score
    4. Pass all three to the AAI engine
    5. Return composite response

    Phase 1: all inputs are mock data.
    Phase 3: prediction + risk are real.
    Phase 4: all three are real.
    Phase 5: full error handling + fallbacks active.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    return compute_aai_response(asset)
