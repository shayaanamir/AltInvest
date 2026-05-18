"""
Centralised mock data for Phase 1.

Every route imports from here so there is exactly one place to update
when real module outputs start replacing these values in Phase 3 and 4.

Usage:
    from shared.mock_data import MOCK_PREDICTION, MOCK_SENTIMENT, MOCK_RISK
"""

from datetime import datetime, timezone

SUPPORTED_ASSETS = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mock_prediction(asset: str) -> dict:
    """Placeholder — replaced by Person C's LSTM output in Phase 3."""
    values = {
        "BTC": {"predicted_price": 65000.0, "prediction_30d": 12.5, "confidence": 0.81},
        "ETH": {"predicted_price": 3200.0,  "prediction_30d": 8.2,  "confidence": 0.76},
    }
    data = values.get(asset, {"predicted_price": None, "prediction_30d": None, "confidence": None})
    return {
        "asset": asset,
        **data,
        "model_version": "mock-v1",
        "timestamp": _now(),
        "note": "Phase 1 mock data — not from ML engine",
    }


def mock_sentiment(asset: str) -> dict:
    """Placeholder — replaced by Person D's VADER output in Phase 4."""
    values = {
        "BTC": {"sentiment_score": 0.72, "post_count": 100},
        "ETH": {"sentiment_score": 0.55, "post_count": 85},
    }
    data = values.get(asset, {"sentiment_score": 0.0, "post_count": 0})
    return {
        "asset": asset,
        **data,
        "source": "mock",
        "timestamp": _now(),
        "note": "Phase 1 mock data — not from sentiment engine",
    }


def mock_risk(asset: str) -> dict:
    """Placeholder — replaced by risk engine output in Phase 3."""
    values = {
        "BTC": {"risk_score": 67.0, "volatility": 0.18, "sharpe_ratio": 1.4},
        "ETH": {"risk_score": 58.0, "volatility": 0.24, "sharpe_ratio": 1.1},
    }
    data = values.get(asset, {"risk_score": 50.0, "volatility": None, "sharpe_ratio": None})
    return {
        "asset": asset,
        **data,
        "timestamp": _now(),
        "note": "Phase 1 mock data — not from risk engine",
    }
