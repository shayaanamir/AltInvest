"""
collectors/cmc_collector.py

Fetches market signals from CoinMarketCap. Optimizations:
  1. fetch_quote_signals + fetch_global_metrics + fetch_trending_assets
     run CONCURRENTLY per asset instead of sequentially.
  2. fetch_global_metrics() and fetch_trending_assets() are asset-independent,
     so they're cached with a short TTL — no reason to refetch them for
     every single asset in the same pipeline cycle.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import requests

try:
    from sentiment_engine.utils.config import CMC_API_KEY, CMC_BASE_URL, CMC_TIMEOUT, ASSETS
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.config import CMC_API_KEY, CMC_BASE_URL, CMC_TIMEOUT, ASSETS
    from utils.logger import get_logger

logger = get_logger("cmc_collector")

HEADERS = {
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
    "Accept": "application/json",
}

# How long to reuse global metrics / trending data across assets & cycles.
# These don't change meaningfully faster than this anyway.
_CACHE_TTL_SECONDS = 90

_global_cache: dict = {"data": None, "fetched_at": 0.0}
_trending_cache: dict = {"data": None, "fetched_at": 0.0, "fetched": False}


def _get(endpoint: str, params: dict = {}) -> Optional[dict]:
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
    clipped = max(-clip, min(clip, value))
    return round((clipped + clip) / (2 * clip), 4)


def fetch_quote_signals(asset_id: str) -> Optional[dict]:
    """Per-asset — NOT cacheable across assets, always fetched fresh."""
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}")

    symbol = ASSETS[asset_id]["cmc_symbol"]
    cmc_id = ASSETS[asset_id]["cmc_id"]

    # Look up by id, not symbol: symbols aren't unique on CMC (many tokens share a ticker)
    # and they change — MATIC became POL — while the id stays put. The response is keyed by id.
    data = _get("/cryptocurrency/quotes/latest", {"id": cmc_id, "convert": "USD"})

    if not data or "data" not in data or str(cmc_id) not in data["data"]:
        logger.warning(f"No CMC quote data for {symbol} (id {cmc_id}). Returning neutral signals.")
        return _neutral_quote_signals(asset_id)

    asset_data = data["data"][str(cmc_id)]
    quote      = asset_data["quote"]["USD"]

    p1h  = quote.get("percent_change_1h", 0)  or 0
    p24h = quote.get("percent_change_24h", 0) or 0
    p7d  = quote.get("percent_change_7d", 0)  or 0
    vol  = quote.get("volume_change_24h", 0)  or 0
    dom  = quote.get("market_cap_dominance", 0) or 0

    price_score   = _normalise_pct((p1h * 0.2) + (p24h * 0.5) + (p7d * 0.3))
    volume_score  = _normalise_pct(vol, clip=100.0)

    # Market-cap dominance is reported but deliberately not scored: it measures size, not
    # sentiment. Scoring it as dom/60 gave BTC ~0.9 and almost every other asset ~0.0,
    # dragging their composite down regardless of what the market was doing.
    composite = round(
        price_score  * 0.70 +
        volume_score * 0.30,
        4
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
        "composite_market_score": composite,
        "is_fallback":        False,
        "fetched_at":         datetime.now(tz=timezone.utc).isoformat(),
    }


def fetch_global_metrics(force_refresh: bool = False) -> Optional[dict]:
    """
    Asset-independent — cached with a short TTL so N assets in one cycle
    don't each trigger their own /global-metrics call.
    """
    now = time.monotonic()
    if not force_refresh and _global_cache["data"] is not None:
        if now - _global_cache["fetched_at"] < _CACHE_TTL_SECONDS:
            return _global_cache["data"]

    data = _get("/global-metrics/quotes/latest")

    if not data or "data" not in data:
        logger.warning("Could not fetch CMC global metrics. Returning neutral.")
        result = {
            "btc_dominance": 50.0,
            "total_market_cap_change_24h": 0.0,
            "global_market_score": 0.5,
            "is_fallback": True,
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    else:
        gdata = data["data"]
        quote = gdata.get("quote", {}).get("USD", {})

        btc_dom = gdata.get("btc_dominance")

        # True 24h change: current total market cap vs the value 24h ago. CMC's
        # total_market_cap_yesterday_percentage_change is a different thing (yesterday's
        # close vs the day before), so it isn't used. None if either value is missing.
        mcap_now  = quote.get("total_market_cap")
        mcap_prev = quote.get("total_market_cap_yesterday")
        mcap_chg  = ((mcap_now / mcap_prev) - 1) * 100 if mcap_now and mcap_prev else None

        # BTC dominance isn't scored (see fetch_quote_signals): it's a constant ~0.9 here,
        # which would just add a fixed bullish offset. Without a market-cap change the
        # score stays neutral.
        global_score = round(_normalise_pct(mcap_chg), 4) if mcap_chg is not None else 0.5

        result = {
            "btc_dominance":               round(btc_dom, 4) if btc_dom is not None else None,
            "total_market_cap_change_24h": round(mcap_chg, 4) if mcap_chg is not None else None,
            "global_market_score":         global_score,
            "is_fallback":                 False,
            "fetched_at":                  datetime.now(tz=timezone.utc).isoformat(),
        }

    _global_cache["data"] = result
    _global_cache["fetched_at"] = now
    return result


def fetch_trending_assets(force_refresh: bool = False) -> Optional[list[int]]:
    """
    Asset-independent — cached the same way as global metrics.
    Returns the CMC ids of the trending assets, or None when CMC couldn't be
    reached, so callers can tell "not trending" apart from "unknown".
    """
    now = time.monotonic()
    # "data" may legitimately be None (CMC unreachable), so track fetches separately.
    if not force_refresh and _trending_cache["fetched"]:
        if now - _trending_cache["fetched_at"] < _CACHE_TTL_SECONDS:
            return _trending_cache["data"]

    data = _get("/cryptocurrency/trending/latest")

    if not data or "data" not in data:
        logger.warning("Could not fetch CMC trending assets.")
        result = None
    else:
        raw_list = []
        d_data = data["data"]
        if isinstance(d_data, list):
            raw_list = d_data
        elif isinstance(d_data, dict):
            if "trending" in d_data and isinstance(d_data["trending"], list):
                raw_list = d_data["trending"]
            else:
                raw_list = list(d_data.values())

        # CMC ids, not symbols: a trending token that merely shares a ticker with one of our
        # assets must not count as that asset trending.
        result = [
            int(item["id"])
            for item in raw_list
            if isinstance(item, dict) and item.get("id") is not None
        ]

    _trending_cache["data"] = result
    _trending_cache["fetched_at"] = now
    _trending_cache["fetched"] = True
    return result


def fetch_all_signals(asset_id: str) -> dict:
    """
    Master function — fetches quote (per-asset), global metrics, and
    trending assets CONCURRENTLY instead of sequentially. Global/trending
    will usually hit the cache after the first asset in a multi-asset run.
    """
    with ThreadPoolExecutor(max_workers=3) as executor:
        quote_future    = executor.submit(fetch_quote_signals, asset_id)
        global_future   = executor.submit(fetch_global_metrics)
        trending_future = executor.submit(fetch_trending_assets)

        quote    = quote_future.result()
        global_m = global_future.result()
        trending = trending_future.result()

    is_trending = (ASSETS[asset_id]["cmc_id"] in trending) if trending is not None else None
    trend_bonus = 0.05 if is_trending else 0.0

    cmc_score = round(
        min(1.0,
            quote["composite_market_score"] * 0.75 +
            global_m["global_market_score"] * 0.25 +
            trend_bonus
        ),
        4
    )

    quote_fallback  = bool(quote.get("is_fallback"))
    global_fallback = bool(global_m.get("is_fallback"))
    degraded = quote_fallback or global_fallback
    if degraded:
        logger.warning(f"CMC data degraded for {asset_id.upper()} — using fallback component(s)")

    logger.info(f"Final CMC score for {asset_id.upper()}: {cmc_score} (trending={is_trending}, degraded={degraded})")

    return {
        "quote":           quote,
        "global":          global_m,
        "is_trending":     is_trending,
        "final_cmc_score": cmc_score,
        "degraded":        degraded,
        "quote_fallback":  quote_fallback,
        "global_fallback": global_fallback,
        "trending_fallback": trending is None,
        "key_missing":     not CMC_API_KEY,
    }


def _neutral_quote_signals(asset_id: str) -> dict:
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
        "composite_market_score": 0.5,
        "is_fallback":            True,
        "fetched_at":             datetime.now(tz=timezone.utc).isoformat(),
    }