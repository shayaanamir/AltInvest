"""
collectors/cmc_collector.py

Fetches market signals from CoinMarketCap:
  - Latest quote data (price change, volume change, dominance)
  - Global market metrics (fear/greed index, BTC dominance, market cap change)
  - Trending assets (used as a secondary signal for momentum)

These signals are NOT NLP — they are numerical market sentiment indicators
that get blended with news NLP scores in the aggregator.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from utils.config import CMC_API_KEY, CMC_BASE_URL, CMC_TIMEOUT, ASSETS
from utils.logger import get_logger

logger = get_logger("cmc_collector")

HEADERS = {
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
    "Accept": "application/json",
}


def _get(endpoint: str, params: dict = {}) -> Optional[dict]:
    """
    Makes a GET request to the CMC API.
    Returns parsed JSON or None on failure.
    """
    url = f"{CMC_BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=CMC_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"CMC HTTP error on {endpoint}: {e} — Status {resp.status_code}")
    except requests.exceptions.ConnectionError:
        logger.error(f"CMC connection failed on {endpoint}")
    except requests.exceptions.Timeout:
        logger.error(f"CMC request timed out on {endpoint}")
    except Exception as e:
        logger.error(f"CMC unexpected error on {endpoint}: {e}")
    return None


def _normalise_pct(value: float, clip: float = 50.0) -> float:
    """
    Converts a percentage change (e.g. +12.5% or -30%) to a 0–1 sentiment score.
    Clips extreme values at ±clip% to prevent outliers dominating.

    Formula: score = (clipped_value + clip) / (2 * clip)
    So  +50% → 1.0,  0% → 0.5,  -50% → 0.0
    """
    clipped = max(-clip, min(clip, value))
    return round((clipped + clip) / (2 * clip), 4)


def fetch_quote_signals(asset_id: str) -> Optional[dict]:
    """
    Fetches the latest quote for an asset and extracts sentiment-relevant signals.

    Returns a dict with:
        - price_change_1h, price_change_24h, price_change_7d  (raw %)
        - volume_change_24h                                    (raw %)
        - market_cap_dominance                                 (raw %)
        - price_score, volume_score, dominance_score           (0–1 normalised)
        - composite_market_score                               (0–1 blended)
    """
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}")

    symbol = ASSETS[asset_id]["cmc_symbol"]
    data   = _get("/cryptocurrency/quotes/latest", {"symbol": symbol, "convert": "USD"})

    if not data or "data" not in data or symbol not in data["data"]:
        logger.warning(f"No CMC quote data for {symbol}. Returning neutral signals.")
        return _neutral_quote_signals(asset_id)

    asset_data = data["data"][symbol]
    quote      = asset_data["quote"]["USD"]

    p1h  = quote.get("percent_change_1h", 0)  or 0
    p24h = quote.get("percent_change_24h", 0) or 0
    p7d  = quote.get("percent_change_7d", 0)  or 0
    vol  = quote.get("volume_change_24h", 0)  or 0
    dom  = quote.get("market_cap_dominance", 0) or 0

    price_score   = _normalise_pct((p1h * 0.2) + (p24h * 0.5) + (p7d * 0.3))
    volume_score  = _normalise_pct(vol, clip=100.0)
    # Dominance alone is not directionally meaningful, so we treat high dominance
    # as moderately positive (market is consolidating to major assets)
    dom_score     = min(1.0, dom / 60.0)

    composite = round(
        price_score  * 0.60 +
        volume_score * 0.25 +
        dom_score    * 0.15,
        4
    )

    logger.info(
        f"CMC quote signals for {symbol}: "
        f"price_score={price_score}, vol_score={volume_score}, composite={composite}"
    )

    return {
        "asset_id":           asset_id,
        "symbol":             symbol,
        "price_change_1h":    round(p1h, 4),
        "price_change_24h":   round(p24h, 4),
        "price_change_7d":    round(p7d, 4),
        "volume_change_24h":  round(vol, 4),
        "market_cap_dominance": round(dom, 4),
        "price_score":        price_score,
        "volume_score":       volume_score,
        "dominance_score":    round(dom_score, 4),
        "composite_market_score": composite,
        "fetched_at":         datetime.now(tz=timezone.utc).isoformat(),
    }


def fetch_global_metrics() -> Optional[dict]:
    """
    Fetches global crypto market metrics from CMC.
    Includes total market cap change and Bitcoin dominance.

    Returns a dict with:
        - btc_dominance         (raw %)
        - total_market_cap_change_24h (raw %)
        - global_market_score   (0–1)
    """
    data = _get("/global-metrics/quotes/latest")

    if not data or "data" not in data:
        logger.warning("Could not fetch CMC global metrics. Returning neutral.")
        return {
            "btc_dominance": 50.0,
            "total_market_cap_change_24h": 0.0,
            "global_market_score": 0.5,
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    gdata = data["data"]
    quote = gdata.get("quote", {}).get("USD", {})

    btc_dom   = gdata.get("btc_dominance", 50.0) or 50.0
    mcap_chg  = quote.get("total_market_cap_yesterday_percentage_change", 0) or 0

    # High BTC dominance + rising market cap = cautiously bullish
    global_score = round(
        _normalise_pct(mcap_chg) * 0.7 +
        min(1.0, btc_dom / 60.0) * 0.3,
        4
    )

    logger.info(f"CMC global metrics: btc_dom={btc_dom}%, mcap_chg={mcap_chg}%, score={global_score}")

    return {
        "btc_dominance":               round(btc_dom, 4),
        "total_market_cap_change_24h": round(mcap_chg, 4),
        "global_market_score":         global_score,
        "fetched_at":                  datetime.now(tz=timezone.utc).isoformat(),
    }


def fetch_trending_assets() -> list[str]:
    """
    Fetches the current trending assets on CoinMarketCap.
    Returns a list of asset symbols (e.g. ['BTC', 'ETH', 'SOL']).
    Used as a boolean boost: if an asset is trending, add a small positive signal.
    """
    data = _get("/cryptocurrency/trending/latest")

    if not data or "data" not in data:
        logger.warning("Could not fetch CMC trending assets.")
        return []

    trending = []
    for item in data["data"].get("trending", []):
        if "symbol" in item:
            trending.append(item["symbol"].upper())

    logger.info(f"Trending assets: {trending}")
    return trending


def fetch_all_signals(asset_id: str) -> dict:
    """
    Master function — fetches all CMC signals for an asset in one call.

    Returns:
        {
            "quote":   { ...quote signals... },
            "global":  { ...global metrics... },
            "is_trending": True/False,
            "final_cmc_score": float (0–1)
        }
    """
    quote    = fetch_quote_signals(asset_id)
    global_m = fetch_global_metrics()
    trending = fetch_trending_assets()

    symbol       = ASSETS[asset_id]["cmc_symbol"]
    is_trending  = symbol in trending
    trend_bonus  = 0.05 if is_trending else 0.0

    # Blend quote score with global macro score
    cmc_score = round(
        min(1.0,
            quote["composite_market_score"] * 0.75 +
            global_m["global_market_score"] * 0.25 +
            trend_bonus
        ),
        4
    )

    logger.info(f"Final CMC score for {asset_id.upper()}: {cmc_score} (trending={is_trending})")

    return {
        "quote":           quote,
        "global":          global_m,
        "is_trending":     is_trending,
        "final_cmc_score": cmc_score,
    }


def _neutral_quote_signals(asset_id: str) -> dict:
    """Returns perfectly neutral signals when the API is unavailable."""
    return {
        "asset_id":               asset_id,
        "symbol":                 ASSETS[asset_id]["cmc_symbol"],
        "price_change_1h":        0.0,
        "price_change_24h":       0.0,
        "price_change_7d":        0.0,
        "volume_change_24h":      0.0,
        "market_cap_dominance":   0.0,
        "price_score":            0.5,
        "volume_score":           0.5,
        "dominance_score":        0.5,
        "composite_market_score": 0.5,
        "fetched_at":             datetime.now(tz=timezone.utc).isoformat(),
    }