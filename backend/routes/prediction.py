from fastapi import APIRouter, HTTPException
from models.schemas import PredictionResponse
from shared.mock_data import mock_prediction, SUPPORTED_ASSETS

router = APIRouter(tags=["Prediction"])


def _map_prediction(doc: dict, asset: str) -> dict:
    ts = doc.get("timestamp")
    if hasattr(ts, "strftime"):
        ts = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "asset": asset,
        "predicted_price": doc.get("predicted_price"),
        "prediction_30d": doc.get("prediction_30d"),
        "confidence": doc.get("confidence"),
        "model_version": doc.get("model_version"),
        "timestamp": ts or "",
        "lower_bound": doc.get("lower_bound"),
        "upper_bound": doc.get("upper_bound"),
        "risk_score": doc.get("risk_score"),
        "trend": doc.get("trend"),
        "agreement": doc.get("agreement"),
        "signal": doc.get("signal"),
        "boosted_confidence": doc.get("boosted_confidence"),
        "ensemble_price": doc.get("ensemble_price"),
    }


@router.get("/prediction/{asset}", response_model=PredictionResponse)
def get_prediction(asset: str):
    """
    Returns the ML engine's prediction for the asset.

    Reads the latest doc from MongoDB `predictions` (written by
    ml/api/prediction_service.py or db/seed_predictions_risk.py).
    Falls back to mock data if nothing's in the DB yet, or Mongo is down.
    """
    asset = asset.upper()
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not supported. Supported: {list(SUPPORTED_ASSETS.keys())}"
        )

    try:
        from db.queries import get_latest_prediction
        doc = get_latest_prediction(asset)
        if doc:
            return _map_prediction(doc, asset)
    except Exception as exc:
        print(f"[prediction] MongoDB unavailable ({exc}), falling back to mock")

    result = mock_prediction(asset)
    if isinstance(result, dict) and not result.get("note"):
        result["note"] = "mock data — no prediction found in DB yet"
    return result