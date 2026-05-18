"""
AAI controller — orchestrates calls to all three modules and assembles the response.

Keeping this logic in a controller (not in the route) means:
- The route stays thin and readable
- This function can be unit tested independently
- Phase 5 error handling / fallback logic slots in here cleanly
"""

from datetime import datetime, timezone
from shared.mock_data import mock_prediction, mock_sentiment, mock_risk
from aai_engine.aai import compute_aai, normalise_sentiment


def compute_aai_response(asset: str) -> dict:
    """
    Fetches all three component scores and computes the AAI.

    Phase 1: uses mock data for all three modules.
    Phase 3+: each mock_* call is replaced with a real module call.

    Phase 5 error handling pattern (add here, not in the route):
        try:
            pred = real_ml_predict(asset)
        except Exception as e:
            logger.warning(f"ML engine failed: {e}")
            pred = {"predicted_price": last_known_price, "confidence": None}
    """

    # --- Step 1: Get prediction score ---
    # Phase 3 replacement: from ml_engine.predict import get_prediction; pred = get_prediction(asset)
    pred = mock_prediction(asset)

    # --- Step 2: Get sentiment score ---
    # Phase 4 replacement: from sentiment_engine.analyze import get_sentiment; sent = get_sentiment(asset)
    sent = mock_sentiment(asset)

    # --- Step 3: Get risk score ---
    # Phase 3 replacement: from risk_engine.risk import calculate_risk; risk = calculate_risk(asset)
    risk = mock_risk(asset)

    # --- Step 4: Normalise inputs and compute AAI ---
    pred_score  = _normalise_prediction(pred.get("predicted_price"), asset)
    sent_score  = normalise_sentiment(sent.get("sentiment_score", 0.0))
    risk_score  = float(risk.get("risk_score", 50.0))

    aai_score = compute_aai(pred_score, sent_score, risk_score)

    return {
        "asset": asset,
        "aai_score": aai_score,
        "pred_score": round(pred_score, 2),
        "sentiment_score": round(sent_score, 2),
        "risk_score": round(risk_score, 2),
        "model_version": pred.get("model_version", "mock-v1"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _normalise_prediction(predicted_price: float | None, asset: str) -> float:
    """
    Converts a raw USD predicted price into a 0–100 score.

    Uses a rough per-asset upper bound for normalisation.
    This will be replaced with a data-driven min/max from the
    historical price range once the pipeline is live (Phase 3).
    """
    if predicted_price is None:
        return 50.0  # neutral fallback

    bounds = {
        "BTC": 200_000.0,
        "ETH": 20_000.0,
    }
    upper = bounds.get(asset, 100_000.0)
    score = (predicted_price / upper) * 100.0
    return round(min(max(score, 0.0), 100.0), 2)
