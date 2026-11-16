"""Shared feed cache (collectors/feed_cache.py): one request per feed per period, polite on errors. No network."""
import threading
import time

import pytest
import requests

from collectors import feed_cache as fc

RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
       b'<item><title>Bitcoin climbs</title><link>https://x/1</link>'
       b'<pubDate>Mon, 16 Nov 2026 05:00:00 GMT</pubDate></item></channel></rss>')
RSS2 = RSS.replace(b"Bitcoin climbs", b"Bitcoin slips")


class Resp:
    def __init__(self, status=200, content=RSS, headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}


class FakeHttp:
    """Answers per URL from a list (the last answer repeats); records every call."""
    def __init__(self, answers=None, delay=0.0):
        self.answers, self.calls, self.delay, self.lock = answers or {}, [], delay, threading.Lock()

    def __call__(self, url, headers=None, timeout=None):
        with self.lock:
            self.calls.append((url, dict(headers or {})))
            queue = self.answers.get(url)
            nxt = (queue.pop(0) if len(queue) > 1 else queue[0]) if queue else Resp()
        if self.delay:
            time.sleep(self.delay)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def count(self, url=None):
        return sum(1 for u, _ in self.calls if url is None or u == url)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


FEEDS = [{"name": f"Feed{i}", "url": f"https://feed{i}.example/rss", "trust_weight": 1.0} for i in range(4)]


@pytest.fixture
def env(monkeypatch):
    fc.clear()
    clock, http = Clock(), FakeHttp()
    monkeypatch.setattr(fc, "_clock", clock)
    monkeypatch.setattr(fc, "_http_get", http)
    yield SimpleEnv(clock, http)
    fc.clear()


class SimpleEnv:
    def __init__(self, clock, http):
        self.clock, self.http = clock, http


def titles(result):
    return [e.title for _, parsed in result for e in parsed.entries]


def test_fifteen_assets_cost_one_request_per_feed(env):
    for _ in range(15):                                  # one pipeline run per asset
        assert len(fc.get_feeds(FEEDS)) == 4
    assert env.http.count() == 4


def test_requests_carry_a_real_user_agent_not_python_requests(env):
    fc.get_feeds(FEEDS[:1])
    (_, headers), = env.http.calls
    assert "python-requests" not in headers["User-Agent"] and "AltInvest" in headers["User-Agent"]


def test_a_feed_is_refreshed_after_the_ttl_with_a_conditional_request(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS, {"ETag": '"v1"', "Last-Modified": "Mon, 16 Nov 2026 05:00:00 GMT"}),
                             Resp(304, b"")]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    result = fc.get_feeds(FEEDS[:1])
    assert env.http.count() == 2
    second = env.http.calls[1][1]
    assert second["If-None-Match"] == '"v1"' and second["If-Modified-Since"].startswith("Mon, 16 Nov")
    assert titles(result) == ["Bitcoin climbs"]            # a 304 keeps the copy we have


def test_changed_content_replaces_the_copy(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS), Resp(200, RSS2)]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    assert titles(fc.get_feeds(FEEDS[:1])) == ["Bitcoin slips"]


def test_concurrent_callers_share_one_fetch(env):
    env.http.delay = 0.05
    results = []
    threads = [threading.Thread(target=lambda: results.append(len(fc.get_feeds(FEEDS)))) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [4] * 12 and env.http.count() == 4


def test_429_without_retry_after_cools_down_and_serves_the_last_copy(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS), Resp(429, b"", {})]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    assert titles(fc.get_feeds(FEEDS[:1])) == ["Bitcoin climbs"]      # throttled: the old copy, not nothing
    assert env.http.count() == 2
    for _ in range(5):                                               # cooling down: no more requests
        env.clock.advance(60)
        fc.get_feeds(FEEDS[:1])
    assert env.http.count() == 2
    env.clock.advance(fc.BACKOFF_DEFAULT_SECONDS)                    # cool-down over: asks again
    fc.get_feeds(FEEDS[:1])
    assert env.http.count() == 3


def test_retry_after_is_honoured(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS), Resp(429, b"", {"Retry-After": "120"}), Resp(200, RSS2)]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    fc.get_feeds(FEEDS[:1])                                          # 429, blocked for 120 s
    env.clock.advance(100)
    fc.get_feeds(FEEDS[:1])
    assert env.http.count() == 2
    env.clock.advance(30)
    assert titles(fc.get_feeds(FEEDS[:1])) == ["Bitcoin slips"]


def test_a_forbidden_feed_keeps_serving_its_copy_until_it_is_too_old(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS), Resp(403, b"")]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    assert titles(fc.get_feeds(FEEDS[:1])) == ["Bitcoin climbs"]
    env.clock.advance(fc.STALE_MAX_SECONDS)
    assert fc.get_feeds(FEEDS[:1]) == []                             # too old to present as current


def test_a_feed_that_never_worked_is_left_out_and_not_hammered(env):
    bad, good = FEEDS[0], FEEDS[1]
    env.http.answers[bad["url"]] = [Resp(403, b"")]
    out = fc.get_feeds([bad, good])
    assert [f["name"] for f, _ in out] == ["Feed1"]
    for _ in range(3):
        fc.get_feeds([bad, good])
    assert env.http.count(bad["url"]) == 1                           # the 60 s failure cool-down


@pytest.mark.parametrize("failure", [requests.exceptions.Timeout(), requests.exceptions.ConnectionError("down"), RuntimeError("boom")])
def test_network_errors_never_raise(env, failure):
    env.http.answers[FEEDS[0]["url"]] = [failure]
    assert fc.get_feeds(FEEDS[:1]) == []


def test_an_unreadable_body_is_a_failure_not_an_empty_feed(env):
    env.http.answers[FEEDS[0]["url"]] = [Resp(200, b"<html>captcha</html>")]
    assert fc.get_feeds(FEEDS[:1]) == []


def test_a_captcha_page_does_not_replace_the_last_good_copy(env):
    url = FEEDS[0]["url"]
    env.http.answers[url] = [Resp(200, RSS), Resp(200, b"<html><body>Just a moment...</body></html>")]
    fc.get_feeds(FEEDS[:1])
    env.clock.advance(fc.CACHE_TTL_SECONDS + 1)
    assert titles(fc.get_feeds(FEEDS[:1])) == ["Bitcoin climbs"]


def test_a_genuinely_empty_feed_is_accepted(env):
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'
    env.http.answers[FEEDS[0]["url"]] = [Resp(200, empty)]
    out = fc.get_feeds(FEEDS[:1])
    assert len(out) == 1 and out[0][1].entries == []


def test_entries_nobody_asks_for_are_forgotten(env):
    fc.get_feeds(FEEDS)
    env.clock.advance(fc.FORGET_AFTER_SECONDS + 1)
    fc.get_feeds(FEEDS[:1])
    assert set(fc.status()) == {FEEDS[0]["url"]}


def test_an_empty_request_makes_no_calls(env):
    assert fc.get_feeds([]) == [] and env.http.count() == 0
