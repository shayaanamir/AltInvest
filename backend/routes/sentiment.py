from fastapi import APIRouter, HTTPException
from models.schemas import SentimentResponse
from shared.mock_data import mock_sentiment, SUPPORTED_ASSETS

router = APIRouter(tags=["Sentiment"])


@router.get("/sentiment/{asset}", response_model=SentimentResponse)
def get_sentiment(asset: str):
    """
    Returns the sentiment engine's compound score for the asset.

    Phase 1: returns mock data.
    Phase 4: this will call sentiment_engine/analyze.py directly.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    # --- Phase 4: replace this block with the real call ---
    # from sentiment_engine.analyze import get_sentiment as sentiment_analyze
    # result = sentiment_analyze(asset)
    # return result
    # ------------------------------------------------------

    return mock_sentiment(asset)
