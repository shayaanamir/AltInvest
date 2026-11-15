"""D90: the real Binance price feed, with a mocked HTTP client and an in-memory database (no network, no Mongo).
Kline numbers are hand-made, not market data."""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

import db.queries as queries
from controllers import price_feed as pf
from db import cleanup_seed_data
from tests.fake_mongo import FakeDB

NOW = datetime(2026, 11, 16, 0, 20, tzinfo=timezone.utc)
H = 3600_000


def kline(open_dt: datetime, close: float, interval_ms: int = H) -> list:
    o = int(open_dt.timestamp() * 1000)
    return [o, "1", "1", "1", f"{close:.2f}", "10", o + interval_ms - 1, f"{close * 10:.2f}", 5, "1", "1", "0"]


def hours(start: datetime, n: int, base: float = 100.0) -> list:
    return [kline(start + timedelta(hours=i), base + i) for i in range(n)]


TICKER_24 = {"lastPrice": "64974.47", "priceChangePercent": "-0.953"}
TICKER_1H = {"lastPrice": "64974.47", "priceChangePercent": "0.12"}
TICKER_7D = {"lastPrice": "64974.47", "priceChangePercent": "-14.349"}


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(queries, "get_db", lambda: db)
    return db


def binance(klines_by_symbol, fail_first_base=0, calls=None):
    """Mock transport: /klines pages from klines_by_symbol by startTime; tickers fixed. The first base URL
    raises ConnectError `fail_first_base` times (the dev machine's flaky first connection)."""
    state = {"fails": fail_first_base}

    def handler(req: httpx.Request):
        if calls is not None:
            calls.append(str(req.url))
        if req.url.host == "api.binance.com" and state["fails"] > 0:
            state["fails"] -= 1
            raise httpx.ConnectError("Network is unreachable", request=req)
        p = dict(req.url.params)
        if req.url.path == "/api/v3/klines":
            start = int(p["startTime"])
            rows = [k for k in klines_by_symbol[p["symbol"]] if k[0] >= start][: int(p["limit"])]
            return httpx.Response(200, json=rows)
        if req.url.path == "/api/v3/ticker/24hr":
            return httpx.Response(200, json=TICKER_24)
        if req.url.path == "/api/v3/ticker":
            return httpx.Response(200, json=TICKER_1H if p["windowSize"] == "1h" else TICKER_7D)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _no_sleep(_):
    pass


def test_symbols_match_the_ml_service_and_the_cleanup():
    assert tuple(pf.SYMBOLS) == cleanup_seed_data.REAL_PRICE_ASSETS
    cfg = Path(__file__).resolve().parents[2] / "ml" / "config.py"
    if not cfg.exists():                           # ml/ is not mounted in the backend container
        pytest.skip("ml/config.py not visible here")
    text = cfg.read_text(encoding="utf-8")
    for asset, symbol in pf.SYMBOLS.items():
        assert re.search(rf'"{asset.lower()}"\s*:\s*"{symbol}"', text), asset


def test_price_rows_keep_closed_klines_only():
    start = NOW.replace(minute=0) - timedelta(hours=3)          # 21:00, 22:00, 23:00 closed; 00:00 still open
    rows = pf.price_rows("BTC", hours(start, 4) + hours(start, 1), NOW)
    assert [r["timestamp"].hour for r in rows] == [21, 22, 23]                   # duplicates dropped, open one too
    assert rows[0] == {"asset": "BTC", "timestamp": start, "price": 100.0, "volume": 1000.0, "interval": "1h",
                       "source": "binance-klines-1h"}


def test_the_chart_reads_the_daily_close_from_the_23h_kline(fake_db):
    """get_daily_price_series takes each UTC day's last row: the 23:00 kline, whose close is the 1d close."""
    day = datetime(2026, 11, 14, tzinfo=timezone.utc)
    kl = hours(day, 48)                                          # 14 and 15 Nov, closes 100..147
    queries.upsert_real_prices(pf.price_rows("BTC", kl, NOW))
    series = queries.get_daily_price_series("BTC", 5)
    assert series == [{"date": "2026-11-14", "price": 123.0}, {"date": "2026-11-15", "price": 147.0}]


def test_backfill_then_daily_is_idempotent_and_replaces_seed_rows(fake_db):
    start = datetime(2026, 11, 10, tzinfo=timezone.utc)
    kl = {s: hours(start, 6 * 24 + 1) for s in pf.SYMBOLS.values()}         # 10 Nov 00:00 .. 16 Nov 00:00 (open)
    seed_hour = datetime(2026, 11, 12, 5)                                   # naive, as Mongo returns it
    fake_db.prices.docs.append({"asset": "BTC", "timestamp": seed_hour.replace(tzinfo=timezone.utc),
                                "price": 42000.0, "volume": 1.0})
    out = pf.pull(binance(kl), NOW, backfill_days=10, sleep=_no_sleep)
    assert all(v.startswith("stored: 144 hourly rows") for v in out.values()), out
    btc = [d for d in fake_db.prices.docs if d["asset"] == "BTC"]
    assert len(btc) == 144 and all(d["source"] == "binance-klines-1h" for d in btc)   # the seed hour was replaced
    again = pf.pull(binance(kl), NOW, sleep=_no_sleep)                  # daily mode, overlapping 72 h
    assert all(v.startswith("stored:") for v in again.values())
    assert len(fake_db.prices.docs) == 3 * 144                          # nothing duplicated
    m = fake_db.asset_market_data.docs
    assert len(m) == 3                                                  # one row per asset and UTC day
    btc_m = next(d for d in m if d["asset_id"] == "BTC")
    assert (btc_m["price"], btc_m["change_24h"], btc_m["change_1h"], btc_m["change_7d"]) == (64974.47, -0.95, 0.12, -14.35)
    assert btc_m["source"] == "binance-ticker" and btc_m["date"] == "2026-11-16T00:00:00Z"
    assert all(btc_m[k] is None for k in ("market_cap", "market_rank", "circulating_supply", "volume_24h"))


def test_daily_start_fills_a_gap_but_never_beyond_the_backfill_window():
    assert pf.start_time(None, NOW, None) == NOW - timedelta(hours=72)
    week_old = (NOW - timedelta(days=7)).replace(tzinfo=None)           # Mongo gives naive UTC
    assert pf.start_time(week_old, NOW, None) == NOW - timedelta(days=7)
    assert pf.start_time(NOW - timedelta(hours=2), NOW, None) == NOW - timedelta(hours=72)
    assert pf.start_time(NOW - timedelta(days=900), NOW, None) == NOW - timedelta(days=pf.BACKFILL_DAYS)
    assert pf.start_time(None, NOW, 30) == NOW - timedelta(days=30)


def test_connection_errors_retry_then_fall_back_to_the_mirror(fake_db):
    kl = {s: hours(NOW - timedelta(hours=5), 5) for s in pf.SYMBOLS.values()}
    calls = []
    out = pf.pull(binance(kl, fail_first_base=pf.TRIES_PER_URL, calls=calls), NOW, sleep=_no_sleep)
    assert all(v.startswith("stored:") for v in out.values()), out
    assert any("data-api.binance.vision" in c for c in calls)


def test_unreachable_feed_writes_nothing_and_reads_no_database(monkeypatch):
    def boom():
        raise AssertionError("the database must not be touched")
    monkeypatch.setattr(queries, "get_db", boom)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    out = pf.pull(client, NOW, sleep=_no_sleep)
    assert all(v.startswith("failed:") and "nothing written" in v for v in out.values())


def test_a_4xx_is_not_retried():
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(1) or httpx.Response(400)))
    with pytest.raises(pf.FeedError):
        pf.get_json(client, "/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}, _no_sleep)
    assert len(calls) == len(pf.BASE_URLS)                              # once per base URL


def test_dry_run_writes_nothing(fake_db):
    kl = {s: hours(NOW - timedelta(hours=5), 5) for s in pf.SYMBOLS.values()}
    out = pf.pull(binance(kl), NOW, backfill_days=1, dry_run=True, sleep=_no_sleep)
    assert all(v.startswith("dry run: 5 hourly rows") for v in out.values()), out
    assert fake_db.prices.docs == [] and fake_db.asset_market_data.docs == []


def test_cli_rejects_a_silly_backfill():
    with pytest.raises(SystemExit):
        pf.main(["--backfill-days", "5000"])
