from fastapi import APIRouter, HTTPException
from models.schemas import AAIResponse
from utils.asset_gate import require_known_asset
from controllers.aai_controller import compute_aai_response, compute_nft_aai_response
from utils.http_errors import db_unavailable

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


@router.get("/aai/nft/{slug}", response_model=AAIResponse)
def get_nft_aai(slug: str):
    """
    The AAI for one tracked NFT collection (ml/docs/DECISIONS.md D98): a neutral 50 for the prediction part,
    the collection's NFT sentiment reading and its ML NFT risk score. Null with `missing_inputs` / `note`
    when there is no usable risk score. Not comparable to a crypto AAI score (the risk part is ranked
    against the tracked collections only).
    """
    from db.queries import get_nft_collection
    try:
        collection = get_nft_collection(slug)
    except Exception as exc:
        raise db_unavailable(exc)
    if not collection:
        raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")
    return compute_nft_aai_response(collection["slug"])
