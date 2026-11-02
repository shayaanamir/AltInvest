from fastapi import APIRouter, HTTPException
from models.schemas import PredictionResponse
from utils.asset_gate import require_known_asset
from utils.ml_rows import iso, with_stale_note

router = APIRouter(tags=["Prediction"])


def _map_prediction(doc: dict, asset: str) -> dict:
    ts = doc.get("timestamp")
    return {
        "asset": asset,
        "predicted_price": doc.get("predicted_price"),
        "prediction_30d": doc.get("prediction_30d"),
        "confidence": doc.get("confidence"),
        "model_version": doc.get("model_version"),
        "timestamp": iso(ts),
        "lower_bound": doc.get("lower_bound"),
        "upper_bound": doc.get("upper_bound"),
        "risk_score": doc.get("risk_score"),
        "trend": doc.get("trend"),
        "agreement": doc.get("agreement"),
        "signal": doc.get("signal"),
        "boosted_confidence": doc.get("boosted_confidence"),
        "ensemble_price": doc.get("ensemble_price"),
        "note": with_stale_note(doc.get("note"), ts),
    }


@router.get("/prediction/{asset}", response_model=PredictionResponse)
def get_prediction(asset: str):
    """
    Returns the ML engine's prediction for the asset.

    Reads the latest doc from MongoDB `predictions` (written by the ML pull,
    controllers/ml_pull_controller.py, for BTC/ETH/SOL; by db/seed_predictions_risk.py
    for the other assets). 404 if none is stored yet; nothing is substituted.
    """
    asset = require_known_asset(asset)

    from db.queries import get_latest_prediction
    doc = get_latest_prediction(asset)  # database errors become a 503 (main.py)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No prediction has been stored for {asset} yet.")
    return _map_prediction(doc, asset)
