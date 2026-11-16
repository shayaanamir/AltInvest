"""
collectors/feed_cache.py

One shared, polite fetcher for every RSS / Atom feed the sentiment engines read.

Before this, each asset's pipeline downloaded all 10 feeds itself: 15 assets x 10 feeds = 150 requests per
cycle, which got the engine throttled (CryptoSlate 429) and blocked (Bitcoin Magazine 403, which rejects the
default `python-requests` User-Agent). Now:

  * A feed is downloaded at most once per CACHE_TTL_SECONDS however many assets (or the NFT engine) ask for
    it. Concurrent callers wait for one fetch (single flight) instead of each making their own.
  * Requests are conditional (If-None-Match / If-Modified-Since), so an unchanged feed costs a 304.
  * Requests carry a descriptive User-Agent.
  * A 429 / 503 puts that feed on a cool-down (Retry-After, else BACKOFF_DEFAULT_SECONDS); any other failure
    cools it down briefly. During a cool-down or failure the last good copy is served for up to
    STALE_MAX_SECONDS, so one flaky outlet neither disappears from the news nor gets hammered.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

# pyrefly: ignore [missing-import]
import feedparser
import requests

try:
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger("feed_cache")

USER_AGENT = "Mozilla/5.0 (compatible; AltInvestSentiment/1.0)"
ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"
TIMEOUT_SECONDS = 8
CACHE_TTL_SECONDS = 600            # a feed is re-checked at most this often
STALE_MAX_SECONDS = 3600           # a copy older than this is not served when a re-check fails
BACKOFF_DEFAULT_SECONDS = 900      # cool-down after a 429 / 503 with no Retry-After
BACKOFF_MAX_SECONDS = 3600
FAILURE_BACKOFF_SECONDS = 60       # cool-down after any other failure (timeout, 403, bad XML ...)
FORGET_AFTER_SECONDS = 6 * 3600    # entries nobody has asked for in this long are dropped

_clock = time.monotonic            # replaced in tests
_http_get = requests.get           # replaced in tests

_lock = threading.Lock()
_entries: dict[str, dict] = {}


def _entry(url: str) -> dict:
    return _entries.setdefault(url, {
        "parsed": None, "fetched_at": None, "checked_at": None, "blocked_until": 0.0,
        "etag": None, "last_modified": None, "asked_at": 0.0,
    })


def _retry_after(resp) -> float:
    try:
        return min(max(float(resp.headers.get("Retry-After", "")), 1.0), BACKOFF_MAX_SECONDS)
    except (TypeError, ValueError):
        return float(BACKOFF_DEFAULT_SECONDS)


def _fetch_one(feed: dict, entry: dict, now: float) -> None:
    """Re-checks one feed and updates its entry in place. Never raises."""
    name, url = feed["name"], feed["url"]
    headers = {"User-Agent": USER_AGENT, "Accept": ACCEPT}
    if entry["parsed"] is not None:
        if entry["etag"]:
            headers["If-None-Match"] = entry["etag"]
        if entry["last_modified"]:
            headers["If-Modified-Since"] = entry["last_modified"]
    try:
        resp = _http_get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        logger.warning(f"{name}: timed out (> {TIMEOUT_SECONDS}s); keeping the last copy")
        entry["blocked_until"] = now + FAILURE_BACKOFF_SECONDS
        return
    except Exception as exc:
        logger.warning(f"{name}: request failed ({type(exc).__name__}); keeping the last copy")
        entry["blocked_until"] = now + FAILURE_BACKOFF_SECONDS
        return

    status = resp.status_code
    if status == 304:
        entry["checked_at"] = now
        return
    if status in (429, 503):
        wait = _retry_after(resp)
        entry["blocked_until"] = now + wait
        logger.warning(f"{name}: HTTP {status}; not asking again for {int(wait)}s")
        return
    if status != 200:
        entry["blocked_until"] = now + FAILURE_BACKOFF_SECONDS
        logger.warning(f"{name}: HTTP {status}; keeping the last copy")
        return

    parsed = feedparser.parse(resp.content)
    # An HTML captcha / error page served with HTTP 200 parses to a feed with no entries and no format
    # (version ""), not an error; a genuinely empty feed still has one ("rss20", "atom10", ...). Treating the
    # page as an empty feed would replace the last good copy and drop that outlet's news.
    if not parsed.entries and (parsed.bozo or not parsed.version):
        entry["blocked_until"] = now + FAILURE_BACKOFF_SECONDS
        logger.warning(f"{name}: not a feed ({parsed.get('bozo_exception') or 'unrecognised format'}); keeping the last copy")
        return
    entry.update({
        "parsed": parsed, "fetched_at": now, "checked_at": now, "blocked_until": 0.0,
        "etag": resp.headers.get("ETag"), "last_modified": resp.headers.get("Last-Modified"),
    })


def get_feeds(feeds: list[dict]) -> list[tuple[dict, Any]]:
    """
    The parsed content of each feed (`{"name", "url", ...}` dicts), as [(feed, parsed)], fetching the ones
    that are due. A feed with nothing usable (never fetched, or its last copy is too old) is left out.
    """
    if not feeds:
        return []
    with _lock:                                   # single flight: later callers find the cache fresh
        now = _clock()
        due = []
        for feed in feeds:
            e = _entry(feed["url"])
            e["asked_at"] = now
            fresh = e["checked_at"] is not None and now - e["checked_at"] < CACHE_TTL_SECONDS
            if not fresh and now >= e["blocked_until"]:
                due.append((feed, e))
        if due:
            with ThreadPoolExecutor(max_workers=min(16, len(due))) as pool:
                list(pool.map(lambda pair: _fetch_one(pair[0], pair[1], now), due))
        for url in [u for u, e in _entries.items() if now - e["asked_at"] > FORGET_AFTER_SECONDS]:
            del _entries[url]

        out = []
        for feed in feeds:
            e = _entries[feed["url"]]
            if e["parsed"] is not None and e["fetched_at"] is not None and now - e["fetched_at"] <= STALE_MAX_SECONDS:
                out.append((feed, e["parsed"]))
        return out


def clear() -> None:
    """Forget everything (tests)."""
    with _lock:
        _entries.clear()


def status() -> dict[str, dict]:
    """{url: {age_seconds, blocked_for_seconds}} for diagnostics."""
    now = _clock()
    with _lock:
        return {u: {"age_seconds": None if e["fetched_at"] is None else round(now - e["fetched_at"]),
                    "blocked_for_seconds": max(0, round(e["blocked_until"] - now))}
                for u, e in _entries.items()}
