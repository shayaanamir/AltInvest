"""ml/data/fetch.py falls back to data-api.binance.vision only on a network error from api.binance.com.
No network: the session is a stand-in that returns hand-made klines (NOT market data)."""

import json

import pytest
import requests

from ml import config
from ml.data import fetch
from ml.data.loader import fetch_meta_path

DAY_MS = 86_400_000


def _klines(n: int) -> list[list]:
    """n hand-made daily klines starting at 2020-01-01, all closed long ago."""
    start = 1_577_836_800_000
    return [[start + i * DAY_MS, "1", "2", "0.5", "1.5", "10", start + (i + 1) * DAY_MS - 1] for i in range(n)]


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.headers, self.text = status, body, {}, ""

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class _Session:
    """Answers per host: an exception instance is raised, anything else is returned."""

    def __init__(self, by_host: dict):
        self.by_host, self.calls = by_host, []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        out = self.by_host[url]
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


def test_main_host_first_and_mirror_untouched_when_it_answers():
    s = _Session({fetch.KLINES_URL: _Resp(body=_klines(3))})
    used = set()
    assert fetch._get_page(s, "BTCUSDT", 0, used) == _klines(3)
    assert s.calls == [fetch.KLINES_URL] and used == {fetch.KLINES_URL}


@pytest.mark.parametrize("error", [requests.ConnectTimeout("t"), requests.ConnectionError("refused")])
def test_network_error_on_main_host_uses_the_mirror(error):
    s = _Session({fetch.KLINES_URL: error, fetch.KLINES_MIRROR_URL: _Resp(body=_klines(2))})
    used = set()
    assert fetch._get_page(s, "LINKUSDT", 0, used) == _klines(2)
    assert s.calls == [fetch.KLINES_URL, fetch.KLINES_MIRROR_URL] and used == {fetch.KLINES_MIRROR_URL}


@pytest.mark.parametrize("status", sorted(fetch.BLOCKED_STATUSES))
def test_a_block_is_never_worked_around_on_the_mirror(status):
    s = _Session({fetch.KLINES_URL: _Resp(status=status), fetch.KLINES_MIRROR_URL: _Resp(body=_klines(2))})
    with pytest.raises(fetch.FetchBlocked):
        fetch._get_page(s, "BTCUSDT", 0)
    assert fetch.KLINES_MIRROR_URL not in s.calls


def test_both_hosts_down_raises_after_the_retries():
    s = _Session({fetch.KLINES_URL: requests.ConnectionError("a"), fetch.KLINES_MIRROR_URL: requests.ConnectionError("b")})
    with pytest.raises(requests.ConnectionError):
        fetch._get_page(s, "BTCUSDT", 0)
    assert len(s.calls) == 2 * fetch.MAX_ATTEMPTS


def test_fetch_records_the_host_that_answered(monkeypatch, tmp_path):
    s = _Session({fetch.KLINES_URL: requests.ConnectTimeout("t"), fetch.KLINES_MIRROR_URL: _Resp(body=_klines(5))})
    monkeypatch.setattr(fetch.requests, "Session", lambda: s)
    meta = fetch.fetch("sol", tmp_path)
    assert meta["symbol"] == "SOLUSDT" and meta["source"] == fetch.KLINES_MIRROR_URL and meta["bars_written"] == 5
    assert json.loads(fetch_meta_path("sol", tmp_path).read_text(encoding="utf-8")) == meta


def test_main_host_alone_is_recorded_when_the_mirror_is_not_needed(monkeypatch, tmp_path):
    s = _Session({fetch.KLINES_URL: _Resp(body=_klines(4))})
    monkeypatch.setattr(fetch.requests, "Session", lambda: s)
    assert fetch.fetch("btc", tmp_path)["source"] == fetch.KLINES_URL
