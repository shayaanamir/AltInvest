from fastapi import APIRouter, HTTPException
from models.schemas import AAIResponse
from utils.asset_gate import require_known_asset
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

    Inputs are the stored prediction and risk score plus live sentiment. If the prediction or
    risk score is missing, aai_score is null and `missing_inputs` / `note` say why.
    """
    asset = require_known_asset(asset)

    return compute_aai_response(asset)
