"""
nft_sentiment/market_signals.py

The NFT counterpart of the crypto pipeline's CoinMarketCap signal: a 0..1 score for how the collection is
trading, built from data the platform already stores (nft_market_data and nft_liquidity). Pure functions;
the backend reads the rows and passes them in, so this module needs no database or network.

Components (each mapped to 0..1, 0.5 = flat):
    change_7d   7-day floor change, clipped to +-30%
    change_24h  24-hour floor change, clipped to +-15%
    activity    sales pace this week vs the 30-day pace: ratio 0.5x -> 0, 1x -> 0.5, 2x -> 1

This is a heuristic summary of recent trading, not a validated predictor of anything.
"""

from __future__ import annotations

import math
from typing import Optional

try:
    from sentiment_engine.nft_sentiment import config as cfg
except ImportError:
    from nft_sentiment import config as cfg


def _number(value) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _norm_pct(value: float, clip: float) -> float:
    clipped = max(-clip, min(clip, value))
    return (clipped + clip) / (2 * clip)


def activity_ratio(liquidity: Optional[dict]) -> Optional[float]:
    """Daily sales pace of the last 7 days divided by that of the last 30 days; None if unknown."""
    if not liquidity:
        return None
    s7, s30 = _number(liquidity.get("sales_7d")), _number(liquidity.get("sales_30d"))
    if s7 is None or s30 is None or s30 <= 0:
        return None
    return (s7 / 7) / (s30 / 30)


def _norm_activity(ratio: float) -> float:
    ratio = max(0.5, min(2.0, ratio))
    return 0.5 + 0.5 * math.log2(ratio)


def build_market_signal(market: Optional[dict], liquidity: Optional[dict]) -> dict:
    """
    Returns {"score": 0..1, "is_fallback": bool, "price_change_24h", "price_change_7d", "activity_ratio",
    "as_of"}. With no usable input the score is a neutral 0.5 and is_fallback is True, so callers can
    leave it out of the blend instead of treating a placeholder as a reading.
    """
    market = market or {}
    c24, c7 = _number(market.get("change_24h")), _number(market.get("change_7d"))
    ratio = activity_ratio(liquidity)

    parts: dict[str, float] = {}
    if c7 is not None:
        parts["change_7d"] = _norm_pct(c7, cfg.MARKET_CLIP_7D_PCT)
    if c24 is not None:
        parts["change_24h"] = _norm_pct(c24, cfg.MARKET_CLIP_24H_PCT)
    if ratio is not None:
        parts["activity"] = _norm_activity(ratio)

    if not parts:
        return {"score": 0.5, "is_fallback": True, "price_change_24h": None, "price_change_7d": None,
                "activity_ratio": None, "as_of": market.get("date")}

    weights = cfg.MARKET_COMPONENT_WEIGHTS
    total = sum(weights[k] for k in parts)
    score = sum(parts[k] * weights[k] for k in parts) / total
    return {
        "score": round(score, 4),
        "is_fallback": False,
        "price_change_24h": c24,
        "price_change_7d": c7,
        "activity_ratio": None if ratio is None else round(ratio, 3),
        "as_of": market.get("date"),
    }
