"""Per-coin news search (collectors/news_search.py and its use in rss_collector). No network."""
import time
from urllib.parse import parse_qs, urlparse

import feedparser
import pytest

from collectors import news_search as ns
from collectors import rss_collector as rc
from utils.config import ASSETS, MAX_ARTICLE_AGE_HOURS, NEWS_SEARCH_QUERIES, RSS_FEEDS


def _rfc(hours_ago):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() - hours_ago * 3600))


def _search_feed(items):
    """A Google-News-shaped feed: ' - Outlet' title suffix, <source>, and a summary that repeats the title."""
    body = "".join(
        f"<item><title>{t} - {outlet}</title><link>https://news.google.com/rss/articles/{abs(hash(t))}</link>"
        f"<description>&lt;a href=&quot;x&quot;&gt;{t}&lt;/a&gt;&nbsp;&nbsp;&lt;font&gt;{outlet}&lt;/font&gt;</description>"
        f"<pubDate>{_rfc(age)}</pubDate><source url=\"https://x\">{outlet}</source></item>"
        for t, outlet, age in items)
    return feedparser.parse(f'<?xml version="1.0"?><rss version="2.0"><channel><title>q</title>{body}</channel></rss>')


def _publisher_feed(items):
    body = "".join(
        f"<item><title>{t}</title><link>https://pub/{abs(hash(t))}</link><description>{s}</description>"
        f"<pubDate>{_rfc(age)}</pubDate></item>" for t, s, age in items)
    return feedparser.parse(f'<?xml version="1.0"?><rss version="2.0"><channel><title>p</title>{body}</channel></rss>')


PUB = {"name": "CoinDesk", "url": "https://p", "trust_weight": 1.0}
SEARCH = {"name": "Google News", "kind": "search", "url": "https://s", "trust_weight": 0.5}


# ── the search feed itself ──────────────────────────────────────────────────

def test_every_asset_has_a_search_query_and_a_feed_url():
    assert set(NEWS_SEARCH_QUERIES) == set(ASSETS)
    for asset_id in ASSETS:
        feed = ns.search_feed(asset_id)
        q = parse_qs(urlparse(feed["url"]).query)["q"][0]
        assert feed["kind"] == "search" and q.endswith(f"when:{round(MAX_ARTICLE_AGE_HOURS / 24)}d")


def test_no_query_means_no_search_feed(monkeypatch):
    monkeypatch.setitem(NEWS_SEARCH_QUERIES, "btc", "")
    assert ns.search_feed("btc") is None


def test_publisher_title_and_summary_cleaning():
    entry = _search_feed([("Chainlink hits a record", "CoinDesk", 2)]).entries[0]
    assert ns.publisher(entry, SEARCH) == "CoinDesk"
    assert ns.clean_title("Chainlink hits a record - CoinDesk", "CoinDesk") == "Chainlink hits a record"
    assert ns.clean_title("A title - Someone Else", "CoinDesk") == "A title - Someone Else"
    assert ns.clean_summary("Chainlink hits a record CoinDesk", "Chainlink hits a record", "CoinDesk") == ""
    assert ns.publisher(SearchlessEntry(), SEARCH) == "Google News"


class SearchlessEntry(dict):
    pass


def test_trust_known_and_unknown_outlets():
    assert ns.trust_for("CoinDesk") == 1.0
    assert ns.trust_for("Some Blog Nobody Knows") == ns.DEFAULT_TRUST < 0.75      # below the fixed feeds


@pytest.mark.parametrize("title,outlet", [
    ("Polygon (prev. MATIC) Price Today | POL to AED Live Price", "Binance"),
    ("Convert 1 POL (Polygon Ecosystem Token) to USD", "Bybit"),
    ("3 Top Price Predictions: Bitcoin, Ethereum, Ripple", "www.tmgm.com"),
    ("Polkadot Spot Price Drops 4.56% in an Hour to $0.711 on Nov. 14", "TOKENPOST"),
    ("NEAR Protocol Gains 5.50% in Four Hours to Reach $3.12", "TOKENPOST"),
    ("Uniswap price drops nearly 30% in a week amid b...", "Pluang"),
    ("Uniswap price drops nearly 30% in a week amid b…", "Pluang"),
    ("NEAR Protocol price meets agent-economy pitch", "ad-hoc-news.de"),
    ("VALOUR POLKADOT Seasonal returns chart", "Yahoo Finance Australia"),
])
def test_junk_is_dropped(title, outlet):
    assert ns.is_junk(title, outlet), title


@pytest.mark.parametrize("title,outlet", [
    ("Chainlink Expands Influence with 10 New Integrations", "Coinfomania"),
    ("Bitcoin falls 5% in 24 hours as ETF outflows grow", "CoinDesk"),
    ("Uniswap jumps 12% after governance vote", "Decrypt"),
    ("Cosmos Hub Votes on Fix for Broken Governance Queries", "The Defiant"),
])
def test_real_news_is_kept(title, outlet):
    assert not ns.is_junk(title, outlet), title


# ── using it in the collector ───────────────────────────────────────────────

def test_search_results_become_articles_with_their_outlet_and_trust():
    parsed = [(SEARCH, _search_feed([
        ("Chainlink adds ten integrations", "CoinDesk", 3),
        ("Chainlink and Polkadot ETFs post outflows", "Cryptonews.net", 5),
        ("Gold hits a record", "CoinDesk", 1),                       # does not name the coin
    ]))]
    arts = rc.articles_from_feeds(parsed, "link", ASSETS["link"])
    assert [(a["title"], a["source"], a["trust_weight"], a["via"]) for a in arts] == [
        ("Chainlink adds ten integrations", "CoinDesk", 1.0, "Google News"),
        ("Chainlink and Polkadot ETFs post outflows", "Cryptonews.net", 0.6, "Google News")]
    assert arts[0]["summary"] == "" and arts[0]["full_text"] == "Chainlink adds ten integrations"
    assert arts[0]["link"].startswith("https://news.google.com/")


def test_junk_and_old_results_are_dropped():
    parsed = [(SEARCH, _search_feed([
        ("Chainlink news", "CoinDesk", 2),
        ("Chainlink Price Today", "Binance", 1),
        ("Chainlink price drops 3.1% in an hour", "Coindoo", 1),
        ("Chainlink from last week", "CoinDesk", MAX_ARTICLE_AGE_HOURS + 1),
    ]))]
    assert [a["title"] for a in rc.articles_from_feeds(parsed, "link", ASSETS["link"])] == ["Chainlink news"]


def test_only_the_newest_results_are_used(monkeypatch):
    monkeypatch.setattr(ns, "SEARCH_MAX_PER_ASSET", 2)
    parsed = [(SEARCH, _search_feed([
        ("Chainlink partners with a major bank", "CoinDesk", 9),
        ("Chainlink staking rewards double next quarter", "CoinDesk", 1),
        ("Whales accumulate LINK during the dip", "CoinDesk", 5),
        ("Chainlink oracle outage delays several lending protocols", "CoinDesk", 3)]))]
    assert [a["title"] for a in rc.articles_from_feeds(parsed, "link", ASSETS["link"])] == [
        "Chainlink staking rewards double next quarter", "Chainlink oracle outage delays several lending protocols"]


def test_the_publishers_copy_wins_over_the_same_headline_from_search():
    parsed = [(SEARCH, _search_feed([("Chainlink adds ten integrations", "CoinDesk", 3)])),
              (PUB, _publisher_feed([("Chainlink adds ten integrations", "The summary only the publisher has.", 3)]))]
    (art,) = rc.articles_from_feeds(parsed, "link", ASSETS["link"])      # order given: search first
    assert art["via"] is None and art["summary"] == "The summary only the publisher has."


def test_a_different_coin_with_the_same_first_word_is_not_this_coin():
    parsed = [(SEARCH, _search_feed([
        ("Ethereum Classic weekly forecast: rebound odds rise", "Traders Union", 2),
        ("Ethereum and Ethereum Classic rally on ETF news", "Decrypt", 3),
        ("Vitalik Buterin backs a gas overhaul", "Crypto News", 4),
    ])), (PUB, _publisher_feed([("Ethereum Classic miners add hashrate", "ETC news.", 1)]))]
    titles = [a["title"] for a in rc.articles_from_feeds(parsed, "eth", ASSETS["eth"])]
    assert "Ethereum Classic weekly forecast: rebound odds rise" not in titles
    assert "Ethereum Classic miners add hashrate" not in titles           # publisher feeds too
    assert titles == ["Ethereum and Ethereum Classic rally on ETF news", "Vitalik Buterin backs a gas overhaul"]


def test_bitcoin_cash_is_not_bitcoin():
    parsed = [(PUB, _publisher_feed([("Bitcoin Cash surges 20%", "BCH.", 1), ("Bitcoin tops $70,000", "BTC.", 2)]))]
    assert [a["title"] for a in rc.articles_from_feeds(parsed, "btc", ASSETS["btc"])] == ["Bitcoin tops $70,000"]


def test_fetch_asks_the_cache_for_the_publisher_feeds_plus_this_coins_search(monkeypatch):
    asked = []
    monkeypatch.setattr(rc.feed_cache, "get_feeds",
                        lambda feeds: asked.append(feeds) or [(PUB, _publisher_feed([("Chainlink news", "s.", 1)]))])
    arts = rc.fetch_articles_for_asset("link")
    assert asked[0][:len(RSS_FEEDS)] == RSS_FEEDS and asked[0][-1]["kind"] == "search"
    assert len(asked[0]) == len(RSS_FEEDS) + 1 and "Chainlink" in asked[0][-1]["url"]
    assert [a["title"] for a in arts] == ["Chainlink news"]                 # search unavailable: publishers alone


def test_a_coin_with_no_query_uses_the_publisher_feeds_only(monkeypatch):
    monkeypatch.setitem(NEWS_SEARCH_QUERIES, "link", "")
    asked = []
    monkeypatch.setattr(rc.feed_cache, "get_feeds", lambda feeds: asked.append(feeds) or [])
    assert rc.fetch_articles_for_asset("link") == [] and asked == [RSS_FEEDS]
