"""RSS collector: shared feeds, UTC dates and asset matching. No network."""
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import feedparser

from collectors import rss_collector as rc
from utils.config import ASSETS, RSS_FEEDS


def _feed(items):
    body = "".join(
        f"<item><title>{t}</title><link>https://x/{abs(hash(t))}</link><description>{t}</description>"
        f"<pubDate>{d}</pubDate></item>" for t, d in items)
    return feedparser.parse(f'<?xml version="1.0"?><rss version="2.0"><channel><title>f</title>{body}</channel></rss>')


def _now_rfc():
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() - 3600))


def test_every_asset_reads_the_same_downloaded_feeds(monkeypatch):
    parsed = [(RSS_FEEDS[0], _feed([("Bitcoin rallies as Ethereum lags", _now_rfc())]))]
    calls = []
    monkeypatch.setattr(rc.feed_cache, "get_feeds", lambda feeds: calls.append(feeds) or parsed)
    btc = rc.fetch_articles_for_asset("btc")
    eth = rc.fetch_articles_for_asset("eth")
    assert len(btc) == 1 and len(eth) == 1
    assert btc[0]["asset_id"] == "btc" and eth[0]["asset_id"] == "eth"
    assert calls == [RSS_FEEDS, RSS_FEEDS]                 # the cache decides what is actually downloaded


def test_an_unrelated_article_is_not_matched(monkeypatch):
    parsed = [(RSS_FEEDS[0], _feed([("Gold hits a record high", _now_rfc())]))]
    monkeypatch.setattr(rc.feed_cache, "get_feeds", lambda feeds: parsed)
    assert rc.fetch_articles_for_asset("btc") == []


def test_unknown_asset_is_an_error():
    try:
        rc.fetch_articles_for_asset("nope")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_published_time_is_read_as_utc_whatever_the_machine_timezone():
    entry = SimpleNamespace(published_parsed=time.struct_time((2026, 11, 16, 5, 0, 0, 0, 320, 0)))
    assert rc._parse_published_date(entry) == datetime(2026, 11, 16, 5, 0, tzinfo=timezone.utc)
    updated_only = SimpleNamespace(published_parsed=None, updated_parsed=time.struct_time((2026, 1, 2, 3, 4, 5, 0, 2, 0)))
    assert rc._parse_published_date(updated_only) == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_old_articles_are_dropped():
    old = "Mon, 01 Jan 2024 00:00:00 GMT"
    parsed = [(RSS_FEEDS[0], _feed([("Bitcoin from long ago", old)]))]
    assert rc.articles_from_feeds(parsed, "btc", ASSETS["btc"]) == []


def test_bitcoin_magazine_uses_the_working_feed_url():
    urls = {f["name"]: f["url"] for f in RSS_FEEDS}
    assert urls["Bitcoin Magazine"] == "https://bitcoinmagazine.com/feed"      # /.rss/full/ is 403 for every client
    assert len({f["url"] for f in RSS_FEEDS}) == len(RSS_FEEDS)
