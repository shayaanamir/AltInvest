"""
backend/controllers/market_data_controller.py

Live crypto market data. Replaces what the seed scripts used to write (typed-in prices and market caps,
and a random-walk price history):

  asset_market_data  one live row per asset: price, market cap, rank, 24h volume, 1h / 24h / 7d change,
                     circulating supply. CoinGecko /coins/markets (keyless), ONE call for every asset,
                     every 2 minutes. The same call also refreshes assets.all_time_high / ath_date.
  prices             hourly closes and USD volume. Binance 1h klines of the asset's USDT pair (USDT taken as
                     USD), backfilled PRICE_HISTORY_DAYS on the first run and topped up every 15 minutes.
                     DAI's Binance pair is delisted (its last kline is from 2020), so DAI comes from
                     CoinGecko's hourly chart, which the free API serves for the last 90 days.
                     Hosts (ml/docs/DECISIONS.md D95): api.binance.com first, then data-api.binance.vision (Binance's official public
                     market-data mirror, same /api/v3/klines and data) ONLY on a network error (timeout, refused
                     connection), which happens intermittently from Docker on the dev machine. An HTTP answer is
                     never retried on the mirror (a 403/451 block is not worked around); same rule as
                     ml/data/fetch.py. Each row's `host` says which one answered.

Every live row carries `source`. Rows without one are the old seed's made-up data and are deleted once
the live source has answered, so fake and real numbers are never shown side by side. An asset with no real
market (BASE, a made-up "Base Ecosystem Index") is left with no market data and no price history.
"""
import path_setup  # noqa: F401

import logging
import time
from datetime import datetime, timezone

import httpx

log = logging.getLogger("market_data")

# asset_id -> (CoinGecko coin id, Binance USDT pair or None). The id, not the symbol: symbols are not
# unique on CoinGecko, and MATIC is now POL (same token since the Sept 2024 migration, asset_id kept).
SOURCES = {
    "BTC": ("bitcoin", "BTCUSDT"),
    "ETH": ("ethereum", "ETHUSDT"),
    "SOL": ("solana", "SOLUSDT"),
    "BNB": ("binancecoin", "BNBUSDT"),
    "XRP": ("ripple", "XRPUSDT"),
    "ADA": ("cardano", "ADAUSDT"),
    "AVAX": ("avalanche-2", "AVAXUSDT"),
    "DOGE": ("dogecoin", "DOGEUSDT"),
    "DOT": ("polkadot", "DOTUSDT"),
    "LINK": ("chainlink", "LINKUSDT"),
    "MATIC": ("polygon-ecosystem-token", "POLUSDT"),
    "UNI": ("uniswap", "UNIUSDT"),
    "LTC": ("litecoin", "LTCUSDT"),
    "ATOM": ("cosmos", "ATOMUSDT"),
    "NEAR": ("near", "NEARUSDT"),
    "ARB": ("arbitrum", "ARBUSDT"),
    "DAI": ("dai", None),
}

SNAPSHOT_SOURCE = "coingecko"
BINANCE_SOURCE = "binance"
COINGECKO_HISTORY_SOURCE = "coingecko"
LIVE_PRICE_SOURCES = (BINANCE_SOURCE, COINGECKO_HISTORY_SOURCE)

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_CHART_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_MIRROR_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"     # D95: network-error fallback only
BINANCE_KLINES_URLS = (BINANCE_KLINES_URL, BINANCE_MIRROR_KLINES_URL)

PRICE_HISTORY_DAYS = 400            # the trending / volatility / snapshot code needs > 30 days
COINGECKO_HOURLY_MAX_DAYS = 90      # the free API returns hourly points only up to 90 days
BINANCE_PAGE = 1000
TIMEOUT_SECONDS = 20
MAX_ATTEMPTS = 3

SNAPSHOT_INTERVAL_SECONDS = 2 * 60
PRICES_INTERVAL_SECONDS = 15 * 60
HOUR_MS = 3600 * 1000

_sleep = time.sleep   # replaced in tests


def _get_from_hosts(client: httpx.Client, urls, params: dict) -> tuple[httpx.Response, str]:
    """GET the first host in `urls` that answers at all; (response, url). A network error (httpx.TransportError:
    connect error, timeout) moves on to the next host; any HTTP answer, even an error status, is returned as is.
    Raises the last network error if no host answers."""
    if not urls:
        raise ValueError("no URL given")
    for i, url in enumerate(urls):
        try:
            return client.get(url, params=params, timeout=TIMEOUT_SECONDS), url
        except httpx.TransportError as exc:
            if i == len(urls) - 1:
                raise
            log.info("[market-data] network error on %s (%s); trying %s", url, type(exc).__name__, urls[i + 1])
    raise AssertionError("unreachable")


def _get_json(client: httpx.Client, url, params: dict, used: set | None = None):
    """GET with retries on 429 / 5xx / network errors. Raises after MAX_ATTEMPTS. `url` may be a tuple of hosts
    (main first, then fallbacks for network errors only, see _get_from_hosts); `used` collects the host that
    answered."""
    urls = (url,) if isinstance(url, str) else tuple(url)
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp, answered = _get_from_hosts(client, urls, params)
            if resp.status_code == 200:
                if used is not None:
                    used.add(answered)
                return resp.json()
            last = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
            wait = resp.headers.get("retry-after")
        except httpx.HTTPError as exc:
            last, wait = f"{type(exc).__name__}: {exc}", None
        if attempt < MAX_ATTEMPTS:
            try:
                _sleep(min(float(wait), 60.0) if wait else 2 ** attempt)
            except ValueError:
                _sleep(2 ** attempt)
    raise RuntimeError(f"{urls[0]} failed: {last}")


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ── Market snapshot (asset_market_data) ───────────────────────────────────────

def market_row(coin: dict, asset_id: str, now: datetime) -> dict:
    """One CoinGecko /coins/markets item -> an asset_market_data row (field names the app already reads)."""
    updated = coin.get("last_updated")
    try:
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else now
    except ValueError:
        ts = now
    return {
        "asset_id": asset_id,
        "price": _num(coin.get("current_price")),
        "change_1h": _num(coin.get("price_change_percentage_1h_in_currency")),
        "change_24h": _num(coin.get("price_change_percentage_24h_in_currency")),
        "change_7d": _num(coin.get("price_change_percentage_7d_in_currency")),
        "market_cap": _num(coin.get("market_cap")),
        "volume_24h": _num(coin.get("total_volume")),
        "circulating_supply": _num(coin.get("circulating_supply")),
        "market_rank": coin.get("market_cap_rank") if isinstance(coin.get("market_cap_rank"), int) else None,
        "timestamp": ts,
        "date": ts.strftime("%Y-%m-%dT00:00:00Z"),
        "source": SNAPSHOT_SOURCE,
        "fetched_at": now,
    }


def fetch_markets(client: httpx.Client) -> list:
    ids = ",".join(cg for cg, _ in SOURCES.values())
    body = _get_json(client, COINGECKO_MARKETS_URL, {
        "vs_currency": "usd", "ids": ids, "price_change_percentage": "1h,24h,7d", "per_page": 250,
    })
    if not isinstance(body, list):
        raise RuntimeError(f"unexpected CoinGecko response: {str(body)[:200]}")
    return body


def refresh_market_snapshot(client: httpx.Client | None = None, db=None, now: datetime | None = None) -> dict:
    """
    Writes one live asset_market_data row per asset and the CoinGecko all-time high into `assets`, then
    deletes every asset_market_data row that is not live (the old seed's made-up numbers). Nothing is
    deleted if CoinGecko answered with no usable coin.
    """
    from db.mongo_connection import get_db
    db = db if db is not None else get_db()
    now = now or datetime.now(timezone.utc)
    by_cg_id = {cg: asset for asset, (cg, _) in SOURCES.items()}

    with (client or httpx.Client()) as http:
        coins = fetch_markets(http)

    written = []
    for coin in coins:
        asset = by_cg_id.get(coin.get("id"))
        row = market_row(coin, asset, now) if asset else None
        if not row or row["price"] is None:
            continue
        db.asset_market_data.update_one({"asset_id": asset, "source": SNAPSHOT_SOURCE}, {"$set": row}, upsert=True)
        ath = _num(coin.get("ath"))
        if ath is not None:
            db.assets.update_one({"asset_id": asset}, {"$set": {
                "all_time_high": ath, "ath_date": (coin.get("ath_date") or "")[:10] or None, "ath_source": SNAPSHOT_SOURCE}})
        written.append(asset)

    removed = 0
    if written:
        removed = db.asset_market_data.delete_many({"source": {"$ne": SNAPSHOT_SOURCE}}).deleted_count
    missing = sorted(set(SOURCES) - set(written))
    return {"updated": len(written), "missing": missing, "removed_fake_rows": removed}


# ── Hourly price history (prices) ─────────────────────────────────────────────

def kline_docs(asset: str, klines: list, now_ms: int) -> list:
    """
    Binance 1h klines -> prices rows. Each row is the hour's close, stamped at the close (open + 1h),
    with the hour's quote-asset (USDT) volume. The still-open hour is skipped.
    Kline: [open_time, open, high, low, close, volume, close_time, quote_volume, ...]
    """
    docs = []
    for k in klines:
        try:
            open_ms, close, close_ms, quote_vol = int(k[0]), float(k[4]), int(k[6]), float(k[7])
        except (TypeError, ValueError, IndexError):
            continue
        if close_ms >= now_ms or close <= 0:
            continue
        docs.append({
            "asset": asset,
            "price": close,
            "volume": quote_vol,
            "timestamp": datetime.fromtimestamp((open_ms + HOUR_MS) / 1000, tz=timezone.utc),
            "source": BINANCE_SOURCE,
        })
    return docs


def chart_docs(asset: str, chart: dict) -> list:
    """
    CoinGecko market_chart (hourly) -> prices rows. Its volumes are rolling 24h totals, so a row's volume
    is that total / 24: an hourly figure on the same scale as Binance's.
    """
    vols = {int(t): v for t, v in (chart.get("total_volumes") or []) if isinstance(v, (int, float))}
    docs = []
    for t, p in chart.get("prices") or []:
        if not isinstance(p, (int, float)) or p <= 0:
            continue
        ts = datetime.fromtimestamp(int(t) / 1000, tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
        vol = vols.get(int(t))
        docs.append({"asset": asset, "price": float(p), "volume": vol / 24 if vol is not None else None,
                     "timestamp": ts, "source": COINGECKO_HISTORY_SOURCE})
    # several points can fall in one hour; keep the last
    return list({d["timestamp"]: d for d in docs}.values())


def fetch_binance_hourly(client: httpx.Client, asset: str, symbol: str, start_ms: int, now_ms: int) -> list:
    docs = []
    while start_ms < now_ms:
        used: set[str] = set()
        klines = _get_json(client, BINANCE_KLINES_URLS,
                           {"symbol": symbol, "interval": "1h", "startTime": start_ms, "limit": BINANCE_PAGE}, used)
        if not klines:
            break
        docs += [{**d, "host": next(iter(used))} for d in kline_docs(asset, klines, now_ms)]
        last_open = int(klines[-1][0])
        if len(klines) < BINANCE_PAGE or last_open + HOUR_MS <= start_ms:
            break
        start_ms = last_open + HOUR_MS
    return docs


def _save_prices(db, docs: list) -> int:
    from pymongo import UpdateOne
    if not docs:
        return 0
    ops = [UpdateOne({"asset": d["asset"], "timestamp": d["timestamp"]}, {"$set": d}, upsert=True) for d in docs]
    for i in range(0, len(ops), 5000):
        db.prices.bulk_write(ops[i:i + 5000], ordered=False)
    return len(docs)


def _last_live_ms(db, asset: str):
    row = db.prices.find_one({"asset": asset, "source": {"$in": list(LIVE_PRICE_SOURCES)}}, sort=[("timestamp", -1)])
    if not row:
        return None
    ts = row["timestamp"]
    ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return int(ts.timestamp() * 1000)


def refresh_prices(client: httpx.Client | None = None, db=None, now: datetime | None = None) -> dict:
    """
    Backfills / tops up the hourly history of every asset, then deletes the history rows that are not
    live (the old seed's random walk) once at least one asset was fetched. Returns {asset: rows | error}.
    """
    from db.mongo_connection import get_db
    db = db if db is not None else get_db()
    now = now or datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    out, fetched = {}, 0

    # Every row is an upsert on (asset, timestamp). Without this index each one scans the whole collection, so
    # the first backfill (~155,000 rows) on a fresh database slowed from under a minute to over an hour. It is the
    # same index db/indexes.py creates at startup (creating it again is a no-op); doing it here too means the
    # job never depends on startup having run first.
    db.prices.create_index([("asset", 1), ("timestamp", -1)])

    with (client or httpx.Client()) as http:
        for asset, (cg_id, symbol) in SOURCES.items():
            try:
                last = _last_live_ms(db, asset)
                if symbol:
                    start = last + 1 if last else now_ms - PRICE_HISTORY_DAYS * 24 * HOUR_MS
                    docs = fetch_binance_hourly(http, asset, symbol, start - HOUR_MS, now_ms)
                    if last:
                        docs = [d for d in docs if d["timestamp"].timestamp() * 1000 > last]
                else:
                    if last and now_ms - last < HOUR_MS:
                        out[asset] = 0
                        fetched += 1
                        continue
                    chart = _get_json(http, COINGECKO_CHART_URL.format(id=cg_id),
                                      {"vs_currency": "usd", "days": COINGECKO_HOURLY_MAX_DAYS})
                    docs = chart_docs(asset, chart)
                out[asset] = _save_prices(db, docs)
                fetched += 1
            except Exception as exc:
                out[asset] = f"failed: {exc}"[:200]
                log.warning("[market-data] price history for %s failed: %s", asset, exc)

    if fetched:
        out["removed_fake_rows"] = db.prices.delete_many({"source": {"$nin": list(LIVE_PRICE_SOURCES)}}).deleted_count
    return out


# ── Scheduler ─────────────────────────────────────────────────────────────────

def run_market_data_scheduler(initial_delay_seconds: int = 5) -> None:
    """
    Daemon-thread loop: the market snapshot every 2 minutes, the price history every 15 (the first run
    backfills PRICE_HISTORY_DAYS). Like the other schedulers, each job first claims its run in MongoDB, so
    with several backend processes only one fetches per interval. Never raises.
    """
    from utils.scheduler_gate import claim_run

    time.sleep(initial_delay_seconds)
    while True:
        for name, interval, job in (("market-snapshot", SNAPSHOT_INTERVAL_SECONDS, refresh_market_snapshot),
                                    ("price-history", PRICES_INTERVAL_SECONDS, refresh_prices)):
            try:
                if claim_run(name, interval - 30):
                    result = job()
                    log.info("[market-data] %s: %s", name, result)
                    print(f"[market-data] {name}: {result}")
            except Exception as exc:
                from utils.http_errors import redact
                log.error("[market-data] %s failed: %s: %s", name, type(exc).__name__, redact(exc))
                print(f"[market-data] {name} failed: {type(exc).__name__}: {redact(exc)}")
        time.sleep(SNAPSHOT_INTERVAL_SECONDS)


if __name__ == "__main__":
    print(refresh_market_snapshot())
    print(refresh_prices())
