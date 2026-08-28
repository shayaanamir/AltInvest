"""
AAI controller — orchestrates calls to all three modules and assembles the response.
"""

from datetime import datetime, timezone
from shared.mock_data import mock_prediction, mock_sentiment, mock_risk
from aai_engine.aai import compute_aai, normalise_sentiment


def _get_real_prediction(asset: str) -> dict:
    """
    Fetches the latest prediction from MongoDB `predictions`.
    Falls back to mock data if nothing's in the DB yet or Mongo is down.
    """
    try:
        from db.queries import get_latest_prediction
        doc = get_latest_prediction(asset)
        if doc:
            return doc
    except Exception as exc:
        print(f"[aai_controller] Prediction DB unavailable ({exc}), using mock")
    return mock_prediction(asset)


def _get_real_risk(asset: str) -> dict:
    """
    Fetches the latest risk score from MongoDB `risk_scores`.
    Falls back to mock data if nothing's in the DB yet or Mongo is down.
    """
    try:
        from db.queries import get_latest_risk
        doc = get_latest_risk(asset)
        if doc:
            return doc
    except Exception as exc:
        print(f"[aai_controller] Risk DB unavailable ({exc}), using mock")
    return mock_risk(asset)


def _get_real_sentiment(asset: str) -> dict:
    """
    Fetches live sentiment from the engine (MongoDB cache → fresh pipeline).
    Falls back to mock data if the engine is unavailable.
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
    pred = _get_real_prediction(asset)
    sent = _get_real_sentiment(asset)
    risk = _get_real_risk(asset)

    pred_score = _normalise_prediction(pred.get("predicted_price"), asset)

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
    if predicted_price is None:
        return 50.0  # neutral fallback

    bounds = {
        "BTC": 200_000.0,
        "ETH": 20_000.0,
    }
    upper = bounds.get(asset, 100_000.0)
    score = (predicted_price / upper) * 100.0
    return round(min(max(score, 0.0), 100.0), 2)