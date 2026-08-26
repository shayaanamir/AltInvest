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
    """
    Placeholder — replaced by Person D's sentiment engine in Phase 4.
    Fully matches SentimentResponse schema.
    """

    values = {
        "BTC": {
            "sentiment_score": 0.44,
            "post_count": 100,

            "confidence": 0.87,
            "confidence_label": "high",
            "signal_strength": "strong",
            "trend": "bullish",

            "source_count": 3,

            "source_breakdown": {
                "reddit": 45.0,
                "twitter": 40.0,
                "news": 15.0,
            },

            "sentiment_distribution": {
                "positive": 70,
                "negative": 10,
                "neutral": 20,
            },

            "top_headlines": [
                {
                    "title": "Bitcoin ETF demand continues rising",
                    "score": 0.91,
                    "source": "CoinDesk",
                    "age_hours": 2.5,
                    "link": "https://example.com/btc-etf"
                },
                {
                    "title": "BTC sentiment turns strongly positive",
                    "score": 0.84,
                    "source": "CoinTelegraph",
                    "age_hours": 5.0,
                    "link": "https://example.com/btc-sentiment"
                }
            ],

            "market_signals": {
                "price_change_24h": 4.2,
                "volume_change_24h": 12.8,
                "is_trending": True,
                "btc_dominance": 53.4
            },

            "articles_by_source": {
                "reddit": 45,
                "twitter": 40,
                "news": 15
            }
        },

        "ETH": {
            "sentiment_score": 0.10,
            "post_count": 85,

            "confidence": 0.74,
            "confidence_label": "medium",
            "signal_strength": "moderate",
            "trend": "neutral",

            "source_count": 3,

            "source_breakdown": {
                "reddit": 35.0,
                "twitter": 35.0,
                "news": 15.0,
            },

            "sentiment_distribution": {
                "positive": 55,
                "negative": 15,
                "neutral": 30,
            },

            "top_headlines": [
                {
                    "title": "Ethereum gas fees stabilize",
                    "score": 0.68,
                    "source": "Decrypt",
                    "age_hours": 4.0,
                    "link": "https://example.com/eth-gas"
                }
            ],

            "market_signals": {
                "price_change_24h": 1.8,
                "volume_change_24h": 6.1,
                "is_trending": False,
                "btc_dominance": 53.4
            },

            "articles_by_source": {
                "reddit": 35,
                "twitter": 35,
                "news": 15
            }
        }
    }

    data = values.get(asset, {
        "sentiment_score": 0.0,
        "post_count": 0,

        "confidence": 0.0,
        "confidence_label": "unknown",
        "signal_strength": "weak",
        "trend": "neutral",

        "source_count": 0,

        "source_breakdown": {},

        "sentiment_distribution": {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        },

        "top_headlines": [],

        "market_signals": {
            "price_change_24h": 0.0,
            "volume_change_24h": 0.0,
            "is_trending": False,
            "btc_dominance": 0.0
        },

        "articles_by_source": {}
    })

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
