"""
collectors/news_search.py

Per-coin news from Google News' RSS search, added to the 10 fixed publisher feeds.

The fixed feeds only list each site's latest 10-40 stories, so a coin that is not in the headlines of those
sites that day (LINK, UNI, DOT, LTC, ATOM, NEAR, POL) had no news at all. A Google News search for the coin's
name returns what hundreds of outlets published about it in the last few days, usually within the last
hours. It is an unofficial RSS endpoint (no key), fetched through collectors/feed_cache.py like every other
feed: once per cache period, with a real User-Agent, a cool-down if throttled, and the last good copy meanwhile.

What a result gives us differs from a publisher feed:
  * the title ends with " - Publisher" (stripped, so duplicates line up with the same story from the
    publisher's own feed), and the real outlet is in the entry's <source> field;
  * there is no summary, only the headline;
  * the link is a news.google.com redirect.

Results still have to name the coin (rss_collector's name/ticker matching), price-tracker pages are dropped
(they restate a price and say nothing about sentiment), and at most SEARCH_MAX_PER_ASSET of the newest are
used, which bounds the extra scoring work per cycle.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlencode

try:
    from sentiment_engine.utils.config import ASSETS, MAX_ARTICLE_AGE_HOURS, NEWS_SEARCH_QUERIES
except ImportError:
    from utils.config import ASSETS, MAX_ARTICLE_AGE_HOURS, NEWS_SEARCH_QUERIES

GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
SEARCH_FEED_NAME = "Google News"
SEARCH_MAX_PER_ASSET = 15          # newest results kept per coin and cycle (bounds FinBERT work)
DEFAULT_TRUST = 0.5                # an outlet not in OUTLET_TRUST: unknown, so below the fixed feeds (0.75-1.0)

# Trust per outlet, on the same 0..1 scale as the fixed feeds (utils/config.py RSS_FEEDS). The established
# news outlets match the fixed feeds; trading-blog and aggregator sites that mostly rewrite price moves
# rank lower; anything not listed gets DEFAULT_TRUST. These numbers are judgement calls: tune them freely.
OUTLET_TRUST = {
    "CoinDesk": 1.0, "The Block": 1.0, "Reuters": 1.0, "Bloomberg": 1.0, "Bloomberg.com": 1.0,
    "CoinTelegraph": 0.95, "Cointelegraph": 0.95, "Decrypt": 0.9, "Blockworks": 0.9, "The Defiant": 0.9,
    "CryptoSlate": 0.9, "Fortune": 0.9, "TechCrunch": 0.9, "The Wall Street Journal": 0.9,
    "Bitcoin Magazine": 0.85, "BeInCrypto": 0.8, "Yahoo Finance": 0.75, "NewsBTC": 0.75, "AMBCrypto": 0.75,
    "Forbes": 0.7, "CryptoPotato": 0.7, "24/7 Wall St.": 0.7, "StreetInsider": 0.65, "U.Today": 0.65,
    "Benzinga": 0.65, "Cryptonews.net": 0.6, "TOKENPOST": 0.6, "www.tokenpost.com": 0.6, "Blockonomi": 0.6,
    "Coin Edition": 0.6, "Coinpedia": 0.6, "Coindoo": 0.55, "Traders Union": 0.5, "CryptoTicker.io": 0.5,
    "Coinfomania": 0.5, "Pluang": 0.5, "TronWeekly": 0.5, "BlockchainReporter": 0.5, "Blockchain News": 0.5,
}

# Dropped outright, because they carry no news about the coin:
#   * exchange / price-tracker pages: they restate the price, which is measured separately;
#   * SEO and press-release farms and chart pages (formulaic text, paid placement).
JUNK_OUTLETS = {"CoinMarketCap", "CoinGecko", "Binance", "Binance Square", "Crypto.com", "Coinbase", "Kraken",
                "Bybit", "KuCoin", "OKX", "Gate.io", "Bitget", "MEXC", "Investing.com", "TradingView",
                "ad-hoc-news.de", "openPR.com", "TechBullion", "BigGo Finance"}
JUNK_TITLE = re.compile(
    r"\b(live price|price today|price chart|price live|converter?|convert\b|price predictions?|price forecasts?"
    r"|to (usd|inr|eur|gbp|jpy)\b|how to buy|market cap (today|data)|latest price|returns chart)\b"
    # auto-generated move blurbs: "Polkadot Price Drops 4.56% in an Hour", "UNI jumps 3.87% in four hours"
    # (up to 12 hours or any minutes; "falls 5% in 24 hours as ETF outflows grow" is real news and stays)
    r"|[\d.,]+%\s+(?:in|within)\s+(?:(?:an?|one|two|three|four|five|six|[1-9]|1[0-2])\s+hours?|\d+\s+minutes?)\b",
    re.I)


def search_feed(asset_id: str) -> Optional[dict]:
    """The feed config for this coin's Google News search, or None if no query is configured."""
    query = NEWS_SEARCH_QUERIES.get(asset_id)
    if not query:
        return None
    days = max(1, round(MAX_ARTICLE_AGE_HOURS / 24))
    params = {"q": f"{query} when:{days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return {
        "name": SEARCH_FEED_NAME, "kind": "search", "asset_id": asset_id,
        "url": f"{GOOGLE_NEWS_URL}?{urlencode(params)}", "trust_weight": DEFAULT_TRUST,
    }


def publisher(entry, feed: dict) -> str:
    """The outlet behind a search result (its <source> field), else the feed's own name."""
    source = entry.get("source")
    if isinstance(source, dict) and source.get("title"):
        return str(source["title"]).strip()
    return feed["name"]


def clean_title(title: str, outlet: str) -> str:
    """Google News appends ' - Outlet' to every title; strip it so the same story from two places lines up."""
    suffix = f" - {outlet}"
    return title[: -len(suffix)].strip() if outlet and title.endswith(suffix) else title


def clean_summary(summary: str, title: str, outlet: str) -> str:
    """A search result's summary is just the title and outlet again; keep it only if it adds something."""
    if summary.startswith(title):
        summary = summary[len(title):].strip(" -")
        if summary == outlet:
            summary = ""
    return summary


def trust_for(outlet: str) -> float:
    return OUTLET_TRUST.get(outlet, DEFAULT_TRUST)


def is_junk(title: str, outlet: str) -> bool:
    """A result to drop: a junk outlet, a price page / move blurb, or a headline cut off with '...'."""
    return (outlet in JUNK_OUTLETS or bool(JUNK_TITLE.search(title))
            or title.rstrip().endswith(("...", "…")))        # truncated: its meaning is lost
