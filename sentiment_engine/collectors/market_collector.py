"""
collectors/market_collector.py

Market signals for the crypto sentiment blend, from two keyless public sources. Replaces the
CoinMarketCap collector, whose key ran out of credits (429) and whose plan has no trending endpoint (403).

  CoinGecko  /coins/markets  ONE call for every asset: price and its 1h / 24h / 7d change, market cap, volume
             /global         BTC dominance and the 24h change of the total market cap
             /search/trending  the coins people are searching for now
  Binance    1h klines       24h volume change per asset (CoinGecko gives the volume but not its change):
                             the last 24 complete hours of quote volume against the 24 before

Each response is cached for MARKET_CACHE_TTL_SECONDS and shared by every asset and pipeline run, with
single flight (concurrent assets wait for one fetch). If a refresh fails, the last good response is reused
for up to STALE_MAX_SECONDS, so a rate-limit blip does not blank the market half of the sentiment.

Nothing is faked: a component that could not be fetched is None, the market score is computed from the
components that are there, and with none of the price data the market score is None, which the aggregator
treats as "news only" instead of blending in a neutral 0.5.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import requests

try:
    from sentiment_engine.utils.config import (
        ASSETS, BINANCE_KLINES_URLS, COINGECKO_BASE_URL, MARKET_CACHE_TTL_SECONDS, MARKET_HTTP_TIMEOUT,
    )
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.config import (
        ASSETS, BINANCE_KLINES_URLS, COINGECKO_BASE_URL, MARKET_CACHE_TTL_SECONDS, MARKET_HTTP_TIMEOUT,
    )
    from utils.logger import get_logger

logger = get_logger("market_collector")

SOURCE = "coingecko+binance"
USER_AGENT = "Mozilla/5.0 (compatible; AltInvestSentiment/1.0)"
FAILURE_TTL_SECONDS = 60          # after a failed refresh, don't ask again for this long
STALE_MAX_SECONDS = 3600          # ...and reuse the last good response for up to this long
RATE_LIMIT_RETRY_MAX_SECONDS = 10
HOUR_MS = 3600 * 1000

PRICE_WEIGHTS = {"1h": 0.2, "24h": 0.5, "7d": 0.3}
PRICE_WEIGHT_IN_QUOTE = 0.70      # composite = price 70% + volume 30% (price alone when volume is missing)
QUOTE_WEIGHT = 0.75               # market score = asset's own quote 75% + the whole market 25%
GLOBAL_WEIGHT = 0.25
TRENDING_BONUS = 0.05

_clock = time.monotonic           # replaced in tests
_http_get: Callable = requests.get   # replaced in tests
_sleep = time.sleep               # replaced in tests

_cache: dict[str, dict] = {}
_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
_locks_guard = threading.Lock()


def reset_cache() -> None:
    with _locks_guard:
        _cache.clear()


# ── Fetching (cached, single flight) ──────────────────────────────────────────

NETWORK_ERRORS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


def _get_from_hosts(urls: tuple, params: dict):
    """GET the first host in `urls` that answers at all (D95). A network error (no connection, timeout) moves on
    to the next host; any HTTP answer, even an error status, is returned as is. Raises the last network error if
    no host answers."""
    for i, url in enumerate(urls):
        try:
            return _http_get(url, params=params, headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                             timeout=MARKET_HTTP_TIMEOUT)
        except NETWORK_ERRORS as exc:
            if i == len(urls) - 1:
                raise
            logger.info(f"network error on {url} ({type(exc).__name__}); trying {urls[i + 1]}")
    raise ValueError("no URL given")


def _get_json(url, params: dict) -> Any:
    """GET + JSON, with one retry after a short wait on a 429. Raises on anything else. `url` may be a tuple of
    hosts: the first, then the others only after a network error (D95, Binance klines)."""
    urls = (url,) if isinstance(url, str) else tuple(url)
    for attempt in (1, 2):
        resp = _get_from_hosts(urls, params)
        if resp.status_code == 429 and attempt == 1:
            try:
                wait = min(float(resp.headers.get("Retry-After", "")), RATE_LIMIT_RETRY_MAX_SECONDS)
            except (TypeError, ValueError):
                wait = 5.0
            _sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("unreachable")


def _cached(name: str, fetch: Callable[[], Any], ttl: float = MARKET_CACHE_TTL_SECONDS) -> Any:
    """`fetch()`'s result, reused for `ttl` seconds; None only if there is nothing usable (never fetched)."""
    with _locks_guard:
        lock = _locks[name]
    with lock:
        now = _clock()
        e = _cache.get(name)
        if e and now - e["at"] < (ttl if e["ok"] else FAILURE_TTL_SECONDS):
            return e["value"]
        try:
            value = fetch()
            _cache[name] = {"value": value, "at": now, "ok": True, "good_at": now}
            return value
        except Exception as exc:
            logger.warning(f"{name}: refresh failed ({type(exc).__name__}: {exc})")
            stale = e["value"] if e and e.get("good_at") is not None and now - e["good_at"] <= STALE_MAX_SECONDS else None
            _cache[name] = {"value": stale, "at": now, "ok": False, "good_at": e.get("good_at") if e else None}
            return stale


def fetch_markets() -> Optional[dict[str, dict]]:
    """{coingecko id: coin} for every configured asset, from ONE /coins/markets call."""
    def fetch():
        ids = ",".join(a["coingecko_id"] for a in ASSETS.values())
        body = _get_json(f"{COINGECKO_BASE_URL}/coins/markets", {
            "vs_currency": "usd", "ids": ids, "price_change_percentage": "1h,24h,7d", "per_page": 250})
        if not isinstance(body, list):
            raise ValueError(f"unexpected response: {str(body)[:120]}")
        return {c["id"]: c for c in body if isinstance(c, dict) and c.get("id")}
    return _cached("markets", fetch)


def fetch_global() -> Optional[dict]:
    """{btc_dominance, market_cap_change_24h} for the whole market, in percent."""
    def fetch():
        data = (_get_json(f"{COINGECKO_BASE_URL}/global", {}) or {}).get("data") or {}
        return {"btc_dominance": _num((data.get("market_cap_percentage") or {}).get("btc")),
                "market_cap_change_24h": _num(data.get("market_cap_change_percentage_24h_usd"))}
    return _cached("global", fetch)


def fetch_trending() -> Optional[set[str]]:
    """CoinGecko ids of the coins trending now; None when unknown (so "not trending" and "unknown" differ)."""
    def fetch():
        coins = (_get_json(f"{COINGECKO_BASE_URL}/search/trending", {}) or {}).get("coins")
        if not isinstance(coins, list):
            raise ValueError("no coins list")
        return {c["item"]["id"] for c in coins if isinstance(c, dict) and (c.get("item") or {}).get("id")}
    return _cached("trending", fetch)


def volume_change_from_klines(klines: list, now_ms: Optional[int] = None) -> Optional[float]:
    """
    24h volume change in percent from 1h klines: quote volume of the last 24 COMPLETE hours against the 24
    before. None if there are fewer than 48 complete hours or the earlier day has no volume.
    Kline: [open_time, open, high, low, close, volume, close_time, quote_volume, ...]
    """
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    vols = []
    for k in klines or []:
        try:
            if int(k[6]) < now_ms:                     # the still-open hour is skipped
                vols.append(float(k[7]))
        except (TypeError, ValueError, IndexError):
            continue
    if len(vols) < 48:
        return None
    last, prev = sum(vols[-24:]), sum(vols[-48:-24])
    if prev <= 0:
        return None
    return (last / prev - 1) * 100


def fetch_volume_change(binance_symbol: str) -> Optional[float]:
    def fetch():
        klines = _get_json(BINANCE_KLINES_URLS, {"symbol": binance_symbol, "interval": "1h", "limit": 50})   # D95
        change = volume_change_from_klines(klines)
        if change is None:
            raise ValueError("fewer than 48 complete hours of volume")
        return change
    return _cached(f"volume:{binance_symbol}", fetch, ttl=600)


# ── Scoring ───────────────────────────────────────────────────────────────────

def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def normalise_pct(value: float, clip: float = 50.0) -> float:
    """A percent change clipped to +-clip and mapped to 0..1 (0.5 = unchanged)."""
    clipped = max(-clip, min(clip, value))
    return round((clipped + clip) / (2 * clip), 4)


def price_score(p1h: Optional[float], p24h: Optional[float], p7d: Optional[float]) -> Optional[float]:
    """Weighted price momentum 0..1 over the changes that exist (renormalised); None if none exist."""
    parts = [(v, PRICE_WEIGHTS[k]) for k, v in (("1h", p1h), ("24h", p24h), ("7d", p7d)) if v is not None]
    if not parts:
        return None
    total = sum(w for _, w in parts)
    return normalise_pct(sum(v * w for v, w in parts) / total)


def build_signals(asset_id: str, coin: Optional[dict], glob: Optional[dict], trending: Optional[set],
                  volume_change: Optional[float]) -> dict:
    """Pure: assembles one asset's signals from already-fetched data (any of which may be None)."""
    asset = ASSETS[asset_id]
    coin = coin or {}
    p1h = _num(coin.get("price_change_percentage_1h_in_currency"))
    p24h = _num(coin.get("price_change_percentage_24h_in_currency"))
    p7d = _num(coin.get("price_change_percentage_7d_in_currency"))
    p_score = price_score(p1h, p24h, p7d)
    v_score = normalise_pct(volume_change, clip=100.0) if volume_change is not None else None

    composite = None
    if p_score is not None:
        composite = round(p_score * PRICE_WEIGHT_IN_QUOTE + v_score * (1 - PRICE_WEIGHT_IN_QUOTE), 4) \
            if v_score is not None else p_score

    glob = glob or {}
    mcap_chg = _num(glob.get("market_cap_change_24h"))
    global_score = normalise_pct(mcap_chg) if mcap_chg is not None else None

    is_trending = (asset["coingecko_id"] in trending) if trending is not None else None

    market_score = None
    if composite is not None:
        parts = [(composite, QUOTE_WEIGHT)] + ([(global_score, GLOBAL_WEIGHT)] if global_score is not None else [])
        market_score = sum(v * w for v, w in parts) / sum(w for _, w in parts)
        if is_trending:
            market_score += TRENDING_BONUS
        market_score = round(min(1.0, market_score), 4)

    return {
        "source": SOURCE,
        "quote": {
            "price_change_1h": p1h, "price_change_24h": p24h, "price_change_7d": p7d,
            "volume_change_24h": volume_change, "market_cap": _num(coin.get("market_cap")),
            "price_score": p_score, "volume_score": v_score, "composite_market_score": composite,
            "is_fallback": composite is None,
        },
        "global": {
            "btc_dominance": _num(glob.get("btc_dominance")),
            "total_market_cap_change_24h": mcap_chg, "global_market_score": global_score,
            "is_fallback": global_score is None,
        },
        "is_trending": is_trending,
        "market_score": market_score,
        "quote_fallback": composite is None,
        "global_fallback": global_score is None,
        "volume_fallback": v_score is None,
        "trending_fallback": trending is None,
        "degraded": composite is None or global_score is None or v_score is None,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def fetch_market_signals(asset_id: str) -> dict:
    """Everything the aggregator needs about the market for one asset. Never raises on a data problem."""
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}")
    asset = ASSETS[asset_id]
    markets = fetch_markets()
    coin = (markets or {}).get(asset["coingecko_id"])
    signals = build_signals(asset_id, coin, fetch_global(), fetch_trending(), fetch_volume_change(asset["binance_symbol"]))
    if signals["market_score"] is None:
        logger.warning(f"No usable market data for {asset_id.upper()}; its sentiment will be news only")
    else:
        logger.info(f"Market score for {asset_id.upper()}: {signals['market_score']} "
                    f"(trending={signals['is_trending']}, degraded={signals['degraded']})")
    return signals
