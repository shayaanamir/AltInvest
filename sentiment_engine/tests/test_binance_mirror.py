"""D95: the 24h volume klines fall back to data-api.binance.vision ONLY on a network error from api.binance.com.
No network: _http_get is a stand-in answering per host with hand-made klines (NOT market data)."""
import time

import pytest
import requests

from collectors import market_collector as mc
from utils import config

MAIN, MIRROR = config.BINANCE_KLINES_URL, config.BINANCE_MIRROR_KLINES_URL
HOUR = 3600 * 1000


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.headers = status, body, {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _klines(day1=100.0, day2=150.0):
    now_ms = int(time.time() * 1000)
    base = now_ms - 49 * HOUR
    rows = [[base + i * HOUR, "1", "1", "1", "1", "1", base + (i + 1) * HOUR - 1, str(day1 if i < 24 else day2)]
            for i in range(49)]
    rows[-1][6] = now_ms + 1000
    return rows


@pytest.fixture
def hosts(monkeypatch):
    """hosts[url] = an exception instance to raise or a Resp; calls lists the URLs asked, in order."""
    mc.reset_cache()
    answers, calls = {}, []

    def get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        out = answers[url]
        if isinstance(out, Exception):
            raise out
        return out
    monkeypatch.setattr(mc, "_http_get", get)
    monkeypatch.setattr(mc, "_sleep", lambda s: None)
    yield answers, calls
    mc.reset_cache()


def test_config_lists_the_main_host_first():
    assert config.BINANCE_KLINES_URLS == (MAIN, MIRROR)
    assert MAIN.startswith("https://api.binance.com/") and MIRROR.startswith("https://data-api.binance.vision/")


def test_main_host_answers_and_the_mirror_is_not_called(hosts):
    answers, calls = hosts
    answers[MAIN] = Resp(200, _klines())
    assert mc.fetch_volume_change("BTCUSDT") == pytest.approx(50.0)
    assert calls == [MAIN]


@pytest.mark.parametrize("error", [requests.ConnectionError("refused"), requests.ConnectTimeout("t"),
                                   requests.ReadTimeout("t")])
def test_network_error_on_main_host_uses_the_mirror(hosts, error):
    answers, calls = hosts
    answers[MAIN], answers[MIRROR] = error, Resp(200, _klines())
    assert mc.fetch_volume_change("LINKUSDT") == pytest.approx(50.0)
    assert calls == [MAIN, MIRROR]


@pytest.mark.parametrize("status", [403, 451, 400])
def test_an_http_answer_is_never_retried_on_the_mirror(hosts, status):
    answers, calls = hosts
    answers[MAIN], answers[MIRROR] = Resp(status), Resp(200, _klines())
    assert mc.fetch_volume_change("BTCUSDT") is None           # the collector's honest "unknown"
    assert MIRROR not in calls


def test_both_hosts_down_gives_no_value(hosts):
    answers, calls = hosts
    answers[MAIN], answers[MIRROR] = requests.ConnectionError("a"), requests.ConnectionError("b")
    assert mc.fetch_volume_change("BTCUSDT") is None
    assert calls == [MAIN, MIRROR]


def test_coingecko_calls_have_no_fallback(hosts):
    answers, calls = hosts
    url = f"{config.COINGECKO_BASE_URL}/global"
    answers[url] = requests.ConnectionError("down")
    with pytest.raises(requests.ConnectionError):
        mc._get_json(url, {})
    assert calls == [url]
