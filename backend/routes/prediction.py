from fastapi import APIRouter, HTTPException
from models.schemas import PredictionResponse
from utils.asset_gate import require_known_asset

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
    404 if none is stored yet; nothing is substituted.
    """
    asset = require_known_asset(asset)

    from db.queries import get_latest_prediction
    doc = get_latest_prediction(asset)  # database errors become a 503 (main.py)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No prediction has been stored for {asset} yet.")
    return _map_prediction(doc, asset)
