"""
backend/controllers/price_feed.py

Real crypto prices for BTC, ETH and SOL from Binance (ml/docs/DECISIONS.md D90), the same market data the
ML service's daily closes come from (ml/data/fetch.py: /api/v3/klines, BTCUSDT / ETHUSDT / SOLUSDT).

  prices             one row per CLOSED 1-hour kline: asset, timestamp (the hour's open, UTC), price (its close),
                     volume (its quote volume, USDT), source "binance-klines-1h". The 23:00 kline closes at
                     23:59:59.999 with exactly the daily close, so the chart's last price of each UTC day
                     (db.queries.get_daily_price_series) is the ML close of that day; the hourly readers
                     (sparklines, trending, the dashboard's 1D chart) keep their hourly rows.
  asset_market_data  one row per asset per UTC day of the pull: the latest price and the rolling 1h / 24h / 7d
                     change from Binance tickers, source "binance-ticker". market_cap, market_rank,
                     circulating_supply and volume_24h are null: Binance does not publish them (its volume is
                     one exchange's volume, not the market's).

Idempotent: prices are upserted on (asset, timestamp), market rows on (asset_id, date), so re-running a day or
an overlapping backfill rewrites the same rows. Unclosed klines are never written.
Requests: each call retries on connection errors and then tries the next base URL (api.binance.com, then
data-api.binance.vision, Binance's public market-data mirror; same klines). Inside Docker on the dev machine
api.binance.com sometimes fails to connect on the first try.

Daily: part of the ML pull (controllers/ml_pull_controller.pull_all, 00:15 UTC and at startup); it fetches from
the newest stored real hour (at most BACKFILL_DAYS back, at least the last DAILY_LOOKBACK_HOURS).
Backfill (inside the backend container, writes to the database MONGO_URI points at):
    python -m controllers.price_feed --backfill-days 400            # covers the 1Y chart + the 30-day lag
    python -m controllers.price_feed --backfill-days 400 --dry-run  # fetch and count only, no writes
"""
import path_setup  # noqa: F401  (puts the repo root on sys.path for `db`)

import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

BASE_URLS = tuple(u.rstrip("/") for u in os.getenv(
    "BINANCE_BASE_URLS", "https://api.binance.com,https://data-api.binance.vision").split(",") if u.strip())
SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}     # = ml/config.py ASSET_SYMBOLS (tested)
SOURCE_PRICES = "binance-klines-1h"
SOURCE_MARKET = "binance-ticker"
BACKFILL_DAYS = 400              # 366-day chart window + 30-day past-range lag + margin
DAILY_LOOKBACK_HOURS = 72        # the daily run always rewrites at least the last 3 days
LIMIT = 1000                     # klines per request (Binance maximum)
TIMEOUT_SECONDS = 10.0
TRIES_PER_URL = 3
BACKOFF_SECONDS = (1, 2, 4)
HOUR = timedelta(hours=1)


class FeedError(RuntimeError):
    pass


def _ms(t: datetime) -> int:
    return int(t.timestamp() * 1000)


def _utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def get_json(client: httpx.Client, path: str, params: dict, sleep=time.sleep):
    """GET path on the first base URL that answers 200; connection errors are retried. Raises FeedError."""
    reasons = []
    for base in BASE_URLS:
        for attempt in range(TRIES_PER_URL):
            if attempt:
                sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
            try:
                resp = client.get(f"{base}{path}", params=params, timeout=TIMEOUT_SECONDS)
            except httpx.HTTPError as exc:
                reasons.append(f"{base}: {type(exc).__name__}")
                continue
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    reasons.append(f"{base}: 200 with a body that is not JSON")
                    break
            reasons.append(f"{base}: HTTP {resp.status_code}")
            if resp.status_code < 500 and resp.status_code != 429:
                break                    # a 4xx other than rate limiting will not change on retry
    raise FeedError("; ".join(reasons[-4:]) or "no base URL configured")


def fetch_hourly(client, symbol: str, start: datetime, now: datetime, sleep=time.sleep) -> list:
    """Raw 1h klines with open time >= start, paged by LIMIT, until the latest one Binance has."""
    out, start_ms, now_ms = [], _ms(start), _ms(now)
    while start_ms < now_ms:
        page = get_json(client, "/api/v3/klines",
                        {"symbol": symbol, "interval": "1h", "startTime": start_ms, "limit": LIMIT}, sleep)
        if not isinstance(page, list):
            raise FeedError("klines answer is not a list")
        if not page:
            break
        out.extend(page)
        start_ms = int(page[-1][0]) + 3600_000
        if len(page) < LIMIT:
            break
    return out


def price_rows(asset: str, klines: list, now: datetime) -> list[dict]:
    """One `prices` row per closed kline (close time before now), oldest first, duplicates dropped."""
    rows, now_ms = {}, _ms(now)
    for k in klines:
        open_ms, close, close_ms, quote_volume = int(k[0]), float(k[4]), int(k[6]), float(k[7])
        if close_ms >= now_ms or close <= 0:
            continue                     # still open (or a bad value): never stored
        rows[open_ms] = {"asset": asset, "timestamp": _utc(open_ms), "price": close, "volume": quote_volume,
                         "interval": "1h", "source": SOURCE_PRICES}
    return [rows[k] for k in sorted(rows)]


def _pct(ticker: dict, key: str = "priceChangePercent") -> float | None:
    try:
        return round(float(ticker[key]), 2)
    except (KeyError, TypeError, ValueError):
        return None


def market_row(asset: str, t24: dict, t1h: dict | None, t7d: dict | None, now: datetime) -> dict:
    price = float(t24["lastPrice"])
    if price <= 0:
        raise FeedError("ticker lastPrice is not positive")
    return {
        "asset_id": asset, "date": now.strftime("%Y-%m-%dT00:00:00Z"), "timestamp": now,
        "price": price, "change_1h": _pct(t1h) if t1h else None, "change_24h": _pct(t24),
        "change_7d": _pct(t7d) if t7d else None,
        # Not published by Binance; null rather than a made-up or single-exchange number (D90).
        "market_cap": None, "market_rank": None, "circulating_supply": None, "volume_24h": None,
        "source": SOURCE_MARKET,
    }


def fetch_market(client, asset: str, now: datetime, sleep=time.sleep) -> dict:
    sym = SYMBOLS[asset]
    t24 = get_json(client, "/api/v3/ticker/24hr", {"symbol": sym}, sleep)
    rolling = {}
    for w in ("1h", "7d"):
        try:
            rolling[w] = get_json(client, "/api/v3/ticker", {"symbol": sym, "windowSize": w}, sleep)
        except FeedError:
            rolling[w] = None            # the header needs only price and 24h change
    return market_row(asset, t24, rolling["1h"], rolling["7d"], now)


def start_time(latest_real: datetime | None, now: datetime, backfill_days: int | None) -> datetime:
    """Where to start fetching: the backfill window, or (daily) the newest stored real hour, bounded."""
    floor = now - timedelta(days=backfill_days or BACKFILL_DAYS)
    if backfill_days:
        return floor
    recent = now - timedelta(hours=DAILY_LOOKBACK_HOURS)
    if latest_real is None:
        return recent
    if latest_real.tzinfo is None:
        latest_real = latest_real.replace(tzinfo=timezone.utc)   # Mongo returns naive UTC datetimes
    return max(floor, min(recent, latest_real))


def pull_asset(client, asset: str, now: datetime, backfill_days: int | None = None, dry_run: bool = False,
               sleep=time.sleep) -> str:
    from db import queries
    try:
        market = fetch_market(client, asset, now, sleep)        # HTTP first: an unreachable feed never reads the DB
        latest = None if (backfill_days or dry_run) else queries.latest_real_price_time(asset, SOURCE_PRICES)
        start = start_time(latest, now, backfill_days)
        rows = price_rows(asset, fetch_hourly(client, SYMBOLS[asset], start, now, sleep), now)
    except (FeedError, KeyError, TypeError, ValueError, IndexError) as exc:
        return f"failed: {exc}; nothing written"
    if not rows:
        return "failed: no closed klines returned; nothing written"
    span = f"{rows[0]['timestamp']:%Y-%m-%d %H:%M} to {rows[-1]['timestamp']:%Y-%m-%d %H:%M} UTC"
    if dry_run:
        return f"dry run: {len(rows)} hourly rows ({span}); price {market['price']}, 24h {market['change_24h']}%"
    queries.upsert_real_prices(rows)
    queries.upsert_real_market_data(market)
    return f"stored: {len(rows)} hourly rows ({span}); price {market['price']}, 24h {market['change_24h']}%"


def pull(client: httpx.Client | None = None, now: datetime | None = None, backfill_days: int | None = None,
         dry_run: bool = False, sleep=time.sleep) -> dict:
    """{ASSET: outcome} for every asset in SYMBOLS. Never raises for HTTP errors."""
    now = now or datetime.now(timezone.utc)
    own = client is None
    client = client or httpx.Client()
    try:
        return {a: pull_asset(client, a, now, backfill_days, dry_run, sleep) for a in SYMBOLS}
    finally:
        if own:
            client.close()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Real Binance prices into prices / asset_market_data (D90)")
    p.add_argument("--backfill-days", type=int, default=None, help=f"fetch this many days back (e.g. {BACKFILL_DAYS})")
    p.add_argument("--dry-run", action="store_true", help="fetch and count only; write nothing")
    args = p.parse_args(argv)
    if args.backfill_days is not None and not 1 <= args.backfill_days <= 1000:
        p.error("--backfill-days must be between 1 and 1000")
    from db.seed_guard import uri_hosts
    scheme, hosts = uri_hosts(os.getenv("MONGO_URI"))
    print(f"[price-feed] target {scheme}://{','.join(hosts)} / {os.getenv('MONGO_DB_NAME')}"
          f"{' (dry run: no writes)' if args.dry_run else ''}", flush=True)
    result = pull(backfill_days=args.backfill_days, dry_run=args.dry_run)
    for asset, outcome in result.items():
        print(f"[price-feed] {asset}: {outcome}", flush=True)
    return 1 if any(v.startswith("failed") for v in result.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
