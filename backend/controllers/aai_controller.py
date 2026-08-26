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


def _get_real_sentiment(asset: str) -> dict:
    """
    Fetches live sentiment from the engine (MongoDB cache → fresh pipeline).
    Falls back to mock data if the engine is unavailable.
    Always returns both sentiment_score and confidence so the caller can
    weight the score instead of treating a 3-article and a 40-article
    reading as equally reliable.
    """
    try:
        from storage.mongo_handler import get_latest_sentiment, get_sentiment_history, save_sentiment
        from aggregator.sentiment_aggregator import run_pipeline

        asset_id = asset.lower()
        cached = get_latest_sentiment(asset_id)
        if cached:
            return {
                "sentiment_score": cached.get("sentiment_score", 0.0),
                "confidence": cached.get("confidence", 0.5),
            }

        history = get_sentiment_history(asset_id, days=1)
        result = run_pipeline(asset_id, history=history)
        save_sentiment(result)
        return {
            "sentiment_score": result.get("sentiment_score", 0.0),
            "confidence": result.get("confidence", 0.5),
        }

    except Exception as exc:
        print(f"[aai_controller] Sentiment engine unavailable ({exc}), using mock")
        mock = mock_sentiment(asset)
        return {
            "sentiment_score": mock.get("sentiment_score", 0.0),
            "confidence": mock.get("confidence", 0.5),
        }


def compute_aai_response(asset: str) -> dict:
    pred = mock_prediction(asset)
    sent = _get_real_sentiment(asset)
    risk = mock_risk(asset)

    pred_score = _normalise_prediction(pred.get("predicted_price"), asset)

    # Shrink low-confidence sentiment toward neutral (50) so a handful of
    # articles can't swing AAI as hard as a well-corroborated reading.
    raw_sent_score = normalise_sentiment(sent.get("sentiment_score", 0.0))
    confidence = float(sent.get("confidence", 0.5))
    sent_score = round(confidence * raw_sent_score + (1 - confidence) * 50.0, 2)

    risk_score = float(risk.get("risk_score", 50.0))

    aai_score = compute_aai(pred_score, sent_score, risk_score)

    return {
        "asset": asset,
        "aai_score": aai_score,
        "pred_score": round(pred_score, 2),
        "sentiment_score": round(sent_score, 2),
        "sentiment_confidence": round(confidence, 2),
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
