"""Live crypto market data (controllers/market_data_controller.py). HTTP and MongoDB are faked."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from controllers import market_data_controller as md

NOW = datetime(2026, 11, 16, 5, 30, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
H = md.HOUR_MS


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(md, "_sleep", lambda s: None)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _coin(cg_id, price=100.0, **extra):
    return {"id": cg_id, "current_price": price, "market_cap": 1e9, "market_cap_rank": 7, "total_volume": 5e7,
            "circulating_supply": 1e7, "price_change_percentage_1h_in_currency": 0.1,
            "price_change_percentage_24h_in_currency": -1.5, "price_change_percentage_7d_in_currency": -13.4,
            "ath": 250.0, "ath_date": "2025-01-19T10:00:00.000Z", "last_updated": "2026-11-16T05:16:49.000Z", **extra}


class FakeCollection:
    def __init__(self):
        self.updates, self.deletes, self.last = [], [], None

    def update_one(self, flt, update, upsert=False):
        self.updates.append((flt, update, upsert))

    def create_index(self, keys, **kw):
        self.indexes = getattr(self, "indexes", []) + [keys]

    def delete_many(self, flt):
        self.deletes.append(flt)
        return SimpleNamespace(deleted_count=3)

    def find_one(self, flt, sort=None):
        return self.last.get(flt["asset"]) if isinstance(self.last, dict) else None


def _db():
    return SimpleNamespace(asset_market_data=FakeCollection(), assets=FakeCollection(), prices=FakeCollection())


# ── snapshot ────────────────────────────────────────────────────────────────

def test_market_row_uses_the_fields_the_app_reads():
    row = md.market_row(_coin("bitcoin", 64640.0), "BTC", NOW)
    assert row["price"] == 64640.0 and row["change_24h"] == -1.5 and row["change_7d"] == -13.4
    assert row["market_cap"] == 1e9 and row["volume_24h"] == 5e7 and row["market_rank"] == 7
    assert row["timestamp"] == datetime(2026, 11, 16, 5, 16, 49, tzinfo=timezone.utc)
    assert row["source"] == "coingecko" and row["date"] == "2026-11-16T00:00:00Z"


def test_snapshot_writes_live_rows_and_ath_then_removes_the_fake_rows():
    seen = {}

    def handler(req):
        seen.update(dict(req.url.params))
        return httpx.Response(200, json=[_coin("bitcoin", 64640.0), _coin("polygon-ecosystem-token", 0.08),
                                         _coin("some-other-coin"), _coin("ethereum", None)])
    db = _db()
    out = md.refresh_market_snapshot(client=_client(handler), db=db, now=NOW)
    assert out["updated"] == 2 and "ETH" in out["missing"] and out["removed_fake_rows"] == 3
    written = {f["asset_id"]: u["$set"] for f, u, upsert in db.asset_market_data.updates}
    assert set(written) == {"BTC", "MATIC"} and written["BTC"]["price"] == 64640.0      # POL is stored as MATIC
    assert db.asset_market_data.deletes == [{"source": {"$ne": "coingecko"}}]
    ath = {f["asset_id"]: u["$set"] for f, u, _ in db.assets.updates}
    assert ath["BTC"] == {"all_time_high": 250.0, "ath_date": "2025-01-19", "ath_source": "coingecko"}
    assert "bitcoin" in seen["ids"] and seen["price_change_percentage"] == "1h,24h,7d"


def test_snapshot_deletes_nothing_when_no_coin_is_usable():
    db = _db()
    out = md.refresh_market_snapshot(client=_client(lambda r: httpx.Response(200, json=[])), db=db, now=NOW)
    assert out["updated"] == 0 and db.asset_market_data.deletes == []


def test_rate_limit_is_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "1"}) if len(calls) == 1 else httpx.Response(200, json=[_coin("bitcoin")])
    out = md.refresh_market_snapshot(client=_client(handler), db=_db(), now=NOW)
    assert len(calls) == 2 and out["updated"] == 1


def test_snapshot_gives_up_after_max_attempts():
    with pytest.raises(RuntimeError):
        md.refresh_market_snapshot(client=_client(lambda r: httpx.Response(503)), db=_db(), now=NOW)


# ── price history ───────────────────────────────────────────────────────────

def _kline(open_ms, close, quote_vol=1000.0):
    return [open_ms, "1", "1", "1", str(close), "10", open_ms + H - 1, str(quote_vol)]


def test_klines_become_hourly_closes_and_skip_the_open_hour():
    hour = NOW_MS - NOW_MS % H                     # the hour still in progress
    docs = md.kline_docs("BTC", [_kline(hour - 2 * H, 100), _kline(hour - H, 101, 55.5), _kline(hour, 102)], NOW_MS)
    assert [d["price"] for d in docs] == [100.0, 101.0]
    assert docs[-1]["timestamp"] == datetime.fromtimestamp(hour / 1000, tz=timezone.utc)   # stamped at the close
    assert docs[-1]["volume"] == 55.5 and docs[-1]["source"] == "binance"


def test_coingecko_chart_is_hourly_with_hourly_volume():
    t = NOW_MS - NOW_MS % H - 3 * H
    chart = {"prices": [[t, 1.001], [t + 60_000, 1.002], [t + H, 0.999], [t + 2 * H, -1]],
             "total_volumes": [[t, 2400.0], [t + 60_000, 4800.0], [t + H, 240.0]]}
    docs = md.chart_docs("DAI", chart)
    assert [d["price"] for d in docs] == [1.002, 0.999]              # last point of each hour, bad price dropped
    assert docs[0]["volume"] == 200.0 and docs[1]["volume"] == 10.0   # rolling 24h total / 24


def test_binance_history_is_paged():
    pages = []
    start = NOW_MS - 1500 * H

    def handler(req):
        s = int(req.url.params["startTime"])
        pages.append(s)
        n = 1000 if len(pages) == 1 else 400
        return httpx.Response(200, json=[_kline(s + i * H, 1.0) for i in range(n)])
    with _client(handler) as c:
        docs = md.fetch_binance_hourly(c, "BTC", "BTCUSDT", start, NOW_MS)
    assert pages == [start, start + 1000 * H] and len(docs) == 1400


def test_refresh_backfills_tops_up_and_removes_the_random_walk(monkeypatch):
    monkeypatch.setattr(md, "SOURCES", {"BTC": ("bitcoin", "BTCUSDT"), "ETH": ("ethereum", "ETHUSDT"),
                                       "DAI": ("dai", None), "SOL": ("solana", "SOLUSDT")})
    saved = []
    monkeypatch.setattr(md, "_save_prices", lambda db, docs: saved.extend(docs) or len(docs))
    hour = NOW_MS - NOW_MS % H
    starts = {}

    def handler(req):
        if "market_chart" in req.url.path:
            return httpx.Response(200, json={"prices": [[hour - H, 1.0]], "total_volumes": [[hour - H, 24.0]]})
        sym, s = req.url.params["symbol"], int(req.url.params["startTime"])
        starts[sym] = s
        if sym == "SOLUSDT":
            return httpx.Response(400, text="Invalid symbol")
        return httpx.Response(200, json=[_kline(hour - 2 * H, 1.0), _kline(hour - H, 2.0)])
    db = _db()
    db.prices.last = {"ETH": {"timestamp": datetime.fromtimestamp((hour - H) / 1000, tz=timezone.utc)}}  # ETH has up to hour-1h
    out = md.refresh_prices(client=_client(handler), db=db, now=NOW)

    assert starts["BTCUSDT"] < NOW_MS - 399 * 24 * H                  # no live rows yet: full backfill
    assert out["BTC"] == 2 and out["ETH"] == 1 and out["DAI"] == 1    # ETH only gets the newer hour
    assert out["SOL"].startswith("failed") and out["removed_fake_rows"] == 3
    assert db.prices.deletes == [{"source": {"$nin": ["binance", "coingecko"]}}]
    assert {d["asset"] for d in saved} == {"BTC", "ETH", "DAI"}


def test_the_prices_index_exists_before_any_row_is_written(monkeypatch):
    """Without it every upsert scans the collection: a fresh database's 155,000-row backfill took 1h40m."""
    monkeypatch.setattr(md, "SOURCES", {"BTC": ("bitcoin", "BTCUSDT")})
    order = []
    db = _db()
    db.prices.create_index = lambda keys, **kw: order.append(("index", keys))
    monkeypatch.setattr(md, "_save_prices", lambda d, docs: order.append(("save", len(docs))) or len(docs))
    hour = NOW_MS - NOW_MS % H
    md.refresh_prices(client=_client(lambda r: httpx.Response(200, json=[_kline(hour - H, 1.0)])), db=db, now=NOW)
    assert order[0] == ("index", [("asset", 1), ("timestamp", -1)]) and ("save", 1) in order


def test_nothing_is_deleted_when_every_fetch_fails(monkeypatch):
    monkeypatch.setattr(md, "SOURCES", {"BTC": ("bitcoin", "BTCUSDT")})
    db = _db()
    out = md.refresh_prices(client=_client(lambda r: httpx.Response(503)), db=db, now=NOW)
    assert out["BTC"].startswith("failed") and "removed_fake_rows" not in out and db.prices.deletes == []


def test_the_sentiment_engine_and_the_price_controller_agree_on_every_coin():
    """Both map asset ids to CoinGecko coins and Binance pairs; they must never drift apart."""
    from sentiment_engine.utils.config import ASSETS
    for asset_id, cfg in ASSETS.items():
        cg_id, pair = md.SOURCES[asset_id.upper()]
        assert (cfg["coingecko_id"], cfg["binance_symbol"]) == (cg_id, pair), asset_id


def test_every_mapped_asset_has_a_coingecko_id_and_base_has_none():
    assert all(cg for cg, _ in md.SOURCES.values())
    assert "BASE" not in md.SOURCES                     # a made-up index: no real market exists
    assert md.SOURCES["MATIC"] == ("polygon-ecosystem-token", "POLUSDT")
    assert md.SOURCES["DAI"][1] is None                 # DAIUSDT is delisted on Binance
