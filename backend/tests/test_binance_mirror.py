"""D95: Binance klines fall back to data-api.binance.vision ONLY on a network error from api.binance.com
(controllers/market_data_controller.py; same rule as ml/data/fetch.py). No network: httpx.MockTransport
answers per host with hand-made klines (NOT market data)."""
from datetime import datetime, timezone

import httpx
import pytest

from controllers import market_data_controller as md

NOW = datetime(2026, 11, 16, 5, 30, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
H = md.HOUR_MS
MAIN, MIRROR = "api.binance.com", "data-api.binance.vision"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(md, "_sleep", lambda s: None)


def _kline(open_ms: int, close: float) -> list:
    return [open_ms, "1", "1", "1", str(close), "1", open_ms + H - 1, "10"]


def _klines(start: int, n: int = 3) -> list:
    return [_kline(start + i * H, 1.0 + i) for i in range(n)]


def _client(by_host: dict, calls: list):
    """by_host: host -> an exception class to raise, or an httpx.Response factory taking the request."""
    def handler(req):
        calls.append(req.url.host)
        out = by_host[req.url.host]
        if isinstance(out, type) and issubclass(out, Exception):
            raise out("simulated", request=req)
        return out(req)
    return httpx.Client(transport=httpx.MockTransport(handler))


def _ok(req):
    return httpx.Response(200, json=_klines(int(req.url.params["startTime"])))


START = NOW_MS - 10 * H


def test_main_host_answers_and_the_mirror_is_not_called():
    calls = []
    with _client({MAIN: _ok}, calls) as c:
        docs = md.fetch_binance_hourly(c, "BTC", "BTCUSDT", START, NOW_MS)
    assert calls == [MAIN] and len(docs) == 3
    assert {d["host"] for d in docs} == {md.BINANCE_KLINES_URL} and {d["source"] for d in docs} == {"binance"}


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout])
def test_network_error_on_main_host_uses_the_mirror(error):
    calls = []
    with _client({MAIN: error, MIRROR: _ok}, calls) as c:
        docs = md.fetch_binance_hourly(c, "LINK", "LINKUSDT", START, NOW_MS)
    assert calls == [MAIN, MIRROR] and len(docs) == 3
    assert {d["host"] for d in docs} == {md.BINANCE_MIRROR_KLINES_URL}
    assert {d["source"] for d in docs} == {"binance"}              # same data source; only the host differs


@pytest.mark.parametrize("status", [403, 451, 400])
def test_an_http_answer_is_never_retried_on_the_mirror(status):
    calls = []
    with _client({MAIN: lambda req: httpx.Response(status, text="no"), MIRROR: _ok}, calls) as c:
        with pytest.raises(RuntimeError, match=f"HTTP {status}"):
            md.fetch_binance_hourly(c, "BTC", "BTCUSDT", START, NOW_MS)
    assert MIRROR not in calls


def test_rate_limit_is_retried_on_the_host_that_answered():
    calls, answers = [], iter([httpx.Response(429, headers={"retry-after": "1"}), None])

    def main(req):
        r = next(answers)
        return r if r is not None else _ok(req)
    with _client({MAIN: main, MIRROR: _ok}, calls) as c:
        docs = md.fetch_binance_hourly(c, "BTC", "BTCUSDT", START, NOW_MS)
    assert calls == [MAIN, MAIN] and {d["host"] for d in docs} == {md.BINANCE_KLINES_URL}


def test_both_hosts_down_fails_after_the_retries():
    calls = []
    with _client({MAIN: httpx.ConnectError, MIRROR: httpx.ConnectError}, calls) as c:
        with pytest.raises(RuntimeError, match="ConnectError"):
            md.fetch_binance_hourly(c, "BTC", "BTCUSDT", START, NOW_MS)
    assert calls == [MAIN, MIRROR] * md.MAX_ATTEMPTS


def test_coingecko_calls_have_no_fallback():
    """A single URL (CoinGecko) is still tried on its own host only."""
    calls = []
    with _client({"api.coingecko.com": httpx.ConnectError}, calls) as c:
        with pytest.raises(RuntimeError):
            md._get_json(c, md.COINGECKO_MARKETS_URL, {})
    assert calls == ["api.coingecko.com"] * md.MAX_ATTEMPTS
