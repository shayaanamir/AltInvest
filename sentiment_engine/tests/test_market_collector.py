"""Market collector (collectors/market_collector.py): CoinGecko + Binance, one batched call, honest fallbacks."""
import threading
import time

import pytest

from collectors import market_collector as mc
from utils.config import ASSETS

HOUR = 3600 * 1000
NOW_MS = 1_790_000_000_000


class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def coin(cg_id, p1h=1.0, p24h=2.0, p7d=-3.0, cap=1e9):
    return {"id": cg_id, "market_cap": cap, "price_change_percentage_1h_in_currency": p1h,
            "price_change_percentage_24h_in_currency": p24h, "price_change_percentage_7d_in_currency": p7d}


def klines(day1=100.0, day2=120.0, now_ms=None):
    """48 complete hourly klines (24 of `day1`, then 24 of `day2` quote volume per hour) plus the open hour."""
    now_ms = now_ms or int(time.time() * 1000)
    base = now_ms - 49 * HOUR
    rows = []
    for i in range(49):
        open_ms = base + i * HOUR
        vol = day1 if i < 24 else day2
        rows.append([open_ms, "1", "1", "1", "1", "1", open_ms + HOUR - 1, str(vol)])
    rows[-1][6] = now_ms + 1000                 # the last candle has not closed yet
    return rows


class FakeNet:
    """Routes by URL; counts calls per route; per-route answers can be errors or status codes."""
    def __init__(self):
        self.calls, self.routes, self.lock = [], {}, threading.Lock()
        self.set("markets", Resp(200, [coin(a["coingecko_id"]) for a in ASSETS.values()]))
        self.set("global", Resp(200, {"data": {"market_cap_percentage": {"btc": 56.1},
                                                "market_cap_change_percentage_24h_usd": 1.0}}))
        self.set("trending", Resp(200, {"coins": [{"item": {"id": "bitcoin"}}, {"item": {"id": "chainlink"}}]}))
        self.set("klines", Resp(200, klines()))

    def set(self, route, answer):
        self.routes[route] = answer

    def __call__(self, url, params=None, headers=None, timeout=None):
        route = ("markets" if "coins/markets" in url else "global" if url.endswith("/global")
                 else "trending" if "trending" in url else "klines")
        with self.lock:
            self.calls.append((route, dict(params or {})))
            ans = self.routes[route]
            if isinstance(ans, list):                       # a sequence of answers; the last one repeats
                ans = ans.pop(0) if len(ans) > 1 else ans[0]
        if isinstance(ans, Exception):
            raise ans
        return ans

    def count(self, route):
        return sum(1 for r, _ in self.calls if r == route)


@pytest.fixture
def net(monkeypatch):
    mc.reset_cache()
    n = FakeNet()
    monkeypatch.setattr(mc, "_http_get", n)
    monkeypatch.setattr(mc, "_sleep", lambda s: None)
    yield n
    mc.reset_cache()


# ── one batched call for everything ─────────────────────────────────────────

def test_every_asset_shares_the_same_market_calls(net):
    for asset_id in ASSETS:
        assert mc.fetch_market_signals(asset_id)["market_score"] is not None
    assert (net.count("markets"), net.count("global"), net.count("trending")) == (1, 1, 1)
    assert net.count("klines") == len(ASSETS)                       # volume is the only per-asset call
    ids = next(p for r, p in net.calls if r == "markets")["ids"].split(",")
    assert sorted(ids) == sorted(a["coingecko_id"] for a in ASSETS.values())


def test_concurrent_pipelines_still_make_one_call(net):
    threads = [threading.Thread(target=mc.fetch_market_signals, args=(a,)) for a in ASSETS]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert net.count("markets") == 1 and net.count("global") == 1 and net.count("trending") == 1


def test_trending_is_matched_by_coin_id_not_symbol(net):
    assert mc.fetch_market_signals("btc")["is_trending"] is True
    assert mc.fetch_market_signals("link")["is_trending"] is True
    assert mc.fetch_market_signals("eth")["is_trending"] is False


# ── scoring ─────────────────────────────────────────────────────────────────

def test_the_market_score_from_known_inputs():
    s = mc.build_signals("eth", coin("ethereum", 1.0, 2.0, -3.0), {"market_cap_change_24h": 1.0}, set(), 20.0)
    price = (0.2 * 1 + 0.5 * 2 + 0.3 * -3 + 50) / 100                  # 0.503
    volume = (20 + 100) / 200                                           # 0.6
    composite = price * 0.7 + volume * 0.3
    expected = (composite * 0.75 + 0.51 * 0.25)
    assert s["quote"]["price_score"] == pytest.approx(price, abs=1e-4)
    assert s["quote"]["composite_market_score"] == pytest.approx(composite, abs=1e-4)
    assert s["market_score"] == pytest.approx(expected, abs=1e-3)
    assert s["degraded"] is False and s["is_trending"] is False


def test_trending_adds_a_small_bonus_capped_at_one():
    base = mc.build_signals("btc", coin("bitcoin"), {"market_cap_change_24h": 0.0}, set(), 0.0)["market_score"]
    boosted = mc.build_signals("btc", coin("bitcoin"), {"market_cap_change_24h": 0.0}, {"bitcoin"}, 0.0)["market_score"]
    assert boosted == pytest.approx(base + 0.05, abs=1e-4)
    huge = coin("bitcoin", 99, 99, 99)
    assert mc.build_signals("btc", huge, {"market_cap_change_24h": 99}, {"bitcoin"}, 999)["market_score"] == 1.0


def test_missing_volume_uses_the_price_alone_and_says_so():
    s = mc.build_signals("eth", coin("ethereum"), {"market_cap_change_24h": 0.0}, None, None)
    assert s["quote"]["composite_market_score"] == s["quote"]["price_score"]
    assert s["volume_fallback"] is True and s["trending_fallback"] is True and s["degraded"] is True
    assert s["quote"]["volume_change_24h"] is None and s["is_trending"] is None


def test_missing_global_uses_the_asset_quote_alone_not_a_neutral_half():
    s = mc.build_signals("eth", coin("ethereum", 5, 5, 5), None, set(), 0.0)
    assert s["global_fallback"] is True
    assert s["market_score"] == s["quote"]["composite_market_score"]   # not averaged with a placeholder 0.5


def test_no_quote_means_no_market_score():
    s = mc.build_signals("eth", None, {"market_cap_change_24h": 3.0}, {"ethereum"}, 50.0)
    assert s["market_score"] is None and s["quote_fallback"] is True and s["degraded"] is True
    # the whole market alone says nothing about this asset, so it is not used on its own
    assert s["quote"]["price_change_24h"] is None


def test_price_score_renormalises_over_the_changes_that_exist():
    only_24h = mc.price_score(None, 10.0, None)
    assert only_24h == pytest.approx((10 + 50) / 100)
    assert mc.price_score(None, None, None) is None


def test_garbage_numbers_are_ignored():
    s = mc.build_signals("eth", {"id": "ethereum", "price_change_percentage_24h_in_currency": float("nan"),
                                "price_change_percentage_7d_in_currency": "up", "market_cap": True}, None, None, None)
    assert s["market_score"] is None and s["quote"]["market_cap"] is None


# ── volume from klines ──────────────────────────────────────────────────────

def test_volume_change_compares_the_last_two_complete_days():
    assert mc.volume_change_from_klines(klines(100.0, 120.0)) == pytest.approx(20.0)
    assert mc.volume_change_from_klines(klines(100.0, 50.0)) == pytest.approx(-50.0)


def test_the_open_candle_is_not_counted():
    rows = klines(100.0, 100.0)
    rows[-1][7] = "999999"                                  # a huge, still-open hour
    assert mc.volume_change_from_klines(rows) == pytest.approx(0.0)


def test_too_little_history_or_no_earlier_volume_is_unknown():
    assert mc.volume_change_from_klines(klines()[10:]) is None
    assert mc.volume_change_from_klines(klines(0.0, 5.0)) is None
    assert mc.volume_change_from_klines([]) is None and mc.volume_change_from_klines(None) is None


# ── failures never raise, and one blip doesn't blank the market half ────────

def test_a_rate_limit_is_retried_once(net):
    net.set("markets", [Resp(429, headers={"Retry-After": "2"}), Resp(200, [coin("bitcoin")])])
    assert "bitcoin" in mc.fetch_markets()
    assert net.count("markets") == 2


def test_a_failed_refresh_reuses_the_last_good_response_for_an_hour(net, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(mc, "_clock", lambda: clock[0])
    assert mc.fetch_markets() is not None
    net.set("markets", Resp(429))
    clock[0] += mc.MARKET_CACHE_TTL_SECONDS + 1
    assert mc.fetch_markets() is not None                  # rate limited: yesterday's blip does not blank it
    n = net.count("markets")
    clock[0] += 10
    mc.fetch_markets()
    assert net.count("markets") == n                       # and it is not hammered (failure cool-down)
    clock[0] += mc.STALE_MAX_SECONDS + mc.MARKET_CACHE_TTL_SECONDS
    assert mc.fetch_markets() is None                      # too old to present as current


def test_everything_down_gives_news_only_signals_and_never_raises(net):
    net.set("markets", RuntimeError("down"))
    net.set("global", RuntimeError("down"))
    net.set("trending", Resp(403))
    net.set("klines", Resp(451))
    s = mc.fetch_market_signals("btc")
    assert s["market_score"] is None and s["degraded"] is True and s["trending_fallback"] is True


def test_unknown_asset_is_an_error():
    with pytest.raises(ValueError):
        mc.fetch_market_signals("nope")


def test_every_asset_has_a_coingecko_id_and_a_binance_pair():
    for asset_id, a in ASSETS.items():
        assert a["coingecko_id"] and a["binance_symbol"].endswith("USDT"), asset_id
    assert len({a["coingecko_id"] for a in ASSETS.values()}) == len(ASSETS)
