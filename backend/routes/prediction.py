from fastapi import APIRouter, HTTPException
from models.schemas import PredictionResponse
from shared.mock_data import mock_prediction, SUPPORTED_ASSETS

router = APIRouter(tags=["Prediction"])


@router.get("/prediction/{asset}", response_model=PredictionResponse)
def get_prediction(asset: str):
    """
    Returns the ML engine's next-day price prediction.

    Phase 1: returns mock data.
    Phase 3: this will call ml_engine/predict.py directly.
    Phase 5: this will read from MongoDB predictions collection.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    # --- Phase 3: replace this block with the real call ---
    # from ml_engine.predict import get_prediction as ml_predict
    # result = ml_predict(asset)
    # return result
    # ------------------------------------------------------

    return mock_prediction(asset)
