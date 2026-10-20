"""
AAI controller — orchestrates calls to all three modules and assembles the response.

Inputs come only from the database (`predictions`, `risk_scores`) and the sentiment engine;
nothing is made up. A missing prediction or risk score leaves that component null and the AAI
score null (with `missing_inputs` / `note` saying why). Sentiment is the one component with a
stand-in (a neutral 50 at zero confidence), and the response flags when that happened.
"""

from datetime import datetime, timezone
from aai_engine.aai import compute_aai, normalise_sentiment, normalise_expected_return


def _get_real_prediction(asset: str) -> dict | None:
    """Latest row in `predictions`, or None. Database errors propagate (503 via main.py)."""
    from db.queries import get_latest_prediction
    return get_latest_prediction(asset)


def _get_real_risk(asset: str) -> dict | None:
    """Latest row in `risk_scores`, or None. Database errors propagate (503 via main.py)."""
    from db.queries import get_latest_risk
    return get_latest_risk(asset)


def _get_real_sentiment(asset: str) -> dict:
    """
    A fresh sentiment reading from the engine: the stored one if it is recent, otherwise a
    refreshed one (same cache, locking and time budget as GET /sentiment/{asset}).

    Never substitutes made-up data. If there is no usable reading — engine missing, pipeline
    failed, nothing to read — it returns confidence 0.0, which makes compute_aai_response use
    a neutral 50 for the sentiment component, and available=False so the response says so.
    """
    try:
        from routes.sentiment import current_sentiment
        record = current_sentiment(asset.lower())
    except Exception as exc:
        print(f"[aai_controller] Sentiment engine unavailable ({exc})")
        record = None

    if record is None:
        return {"sentiment_score": 0.0, "confidence": 0.0, "available": False}
    return {
        "sentiment_score": record["sentiment_score"],
        "confidence": record["confidence"],
        "available": True,
    }


def _expected_return_pct(pred: dict, asset: str) -> float | None:
    """
    The prediction's expected 30-day move in percent: the stored `prediction_30d`, or worked out
    from `predicted_price` against the latest stored price. None if neither is possible.
    """
    pct = pred.get("prediction_30d")
    if isinstance(pct, (int, float)):
        return float(pct)
    target = pred.get("predicted_price")
    if not isinstance(target, (int, float)):
        return None
    from db.queries import get_latest_price
    price = (get_latest_price(asset) or {}).get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    return (target / price - 1.0) * 100.0


def compute_aai_response(asset: str) -> dict:
    pred = _get_real_prediction(asset)
    sent = _get_real_sentiment(asset)
    risk = _get_real_risk(asset)

    expected = _expected_return_pct(pred, asset) if pred else None
    pred_score = normalise_expected_return(expected) if expected is not None else None

    raw_sent_score = normalise_sentiment(sent.get("sentiment_score", 0.0))
    confidence = float(sent.get("confidence", 0.0))
    sent_score = round(confidence * raw_sent_score + (1 - confidence) * 50.0, 2)

    risk_value = (risk or {}).get("risk_score")
    risk_score = float(risk_value) if isinstance(risk_value, (int, float)) else None

    aai_score = (
        compute_aai(pred_score, sent_score, risk_score)
        if pred_score is not None and risk_score is not None else None
    )
    sentiment_available = bool(sent.get("available", True))
    missing = [name for name, v in (("prediction", pred_score), ("risk score", risk_score)) if v is None]

    return {
        "asset": asset,
        "aai_score": aai_score,
        "pred_score": pred_score,
        "expected_return_30d": round(expected, 2) if expected is not None else None,
        "sentiment_score": round(sent_score, 2),
        "sentiment_confidence": round(confidence, 2),
        "sentiment_available": sentiment_available,
        "sentiment_note": None if sentiment_available else (
            "No recent sentiment reading was available, so a neutral value was used for the sentiment component."
        ),
        "risk_score": round(risk_score, 2) if risk_score is not None else None,
        "missing_inputs": missing,
        "note": None if not missing else (
            f"No {' or '.join(missing)} is stored for {asset} yet, so the AAI score can't be computed."
        ),
        "model_version": (pred or {}).get("model_version"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def is_complete(result: dict) -> bool:
    """True when every input was real (prediction, risk and sentiment): only then may it be cached."""
    return result.get("aai_score") is not None and result.get("sentiment_available") is not False
