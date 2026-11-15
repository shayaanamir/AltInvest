"""
nft_sentiment/collector.py

Collects NFT news for every target (the collections plus the NFT market) in one cycle, from two kinds of
source, all fetched concurrently:

  search feeds  Google News and Bing News RSS searches, one set per target (config google_query and
                bing_queries). The main source: in a live check of the broad feeds (2026-11-16) none of 311
                headlines from the past week named a tracked collection.
  broad feeds   the NFT sites and the crypto pipeline's feeds, fetched ONCE and matched against every
                target by name (the crypto collector re-downloads every feed per asset).

Every article must still name its target (the crypto pipeline's _entry_matches_asset), so a search hit
that only mentions the collection deep in a page it doesn't show us is left out. The LLM scorer then
decides whether what remains is really about the collection.
"""

from __future__ import annotations

import calendar
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import feedparser
import requests

try:
    from sentiment_engine.nft_sentiment import config as cfg
    from sentiment_engine.collectors.rss_collector import (
        _entry_matches_asset,
        _clean_html,
        _cluster_near_duplicates,
    )
    from sentiment_engine.utils.config import RSS_FEEDS
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from nft_sentiment import config as cfg
    from collectors.rss_collector import (
        _entry_matches_asset,
        _clean_html,
        _cluster_near_duplicates,
    )
    from utils.config import RSS_FEEDS
    from utils.logger import get_logger

logger = get_logger("nft_collector")


# ── Source definitions ────────────────────────────────────────────────────────

def broad_feeds() -> list[dict]:
    """NFT feeds first, then the general crypto feeds, without repeating a URL."""
    seen, feeds = set(), []
    for feed in [*cfg.NFT_RSS_FEEDS, *RSS_FEEDS]:
        if feed["url"] not in seen:
            seen.add(feed["url"])
            feeds.append({**feed, "kind": "broad"})
    return feeds


def search_feeds(target_id: str, target: dict) -> list[dict]:
    """The Google News and Bing News search feeds for one target."""
    feeds = []
    if target.get("google_query"):
        q = f"{target['google_query']} when:{cfg.SEARCH_WINDOW}"
        feeds.append({
            "name": "Google News", "kind": "search", "target": target_id,
            "url": f"{cfg.GOOGLE_NEWS_URL}?{urlencode({'q': q, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})}",
        })
    for query in target.get("bing_queries", []):
        feeds.append({
            "name": "Bing News", "kind": "search", "target": target_id,
            "url": f"{cfg.BING_NEWS_URL}?{urlencode({'q': query, 'format': 'rss'})}",
        })
    return feeds


def targets_for(slugs=None, include_market: bool = True) -> dict[str, dict]:
    """The targets to collect for: the chosen collections (default all) plus the market."""
    chosen = list(cfg.NFT_COLLECTIONS) if slugs is None else [s for s in slugs if s in cfg.NFT_COLLECTIONS]
    targets = {slug: cfg.NFT_COLLECTIONS[slug] for slug in chosen}
    if include_market:
        targets[cfg.NFT_MARKET_ID] = cfg.NFT_MARKET
    return targets


# ── Fetching ──────────────────────────────────────────────────────────────────

def _fetch_feed(feed: dict):
    try:
        resp = requests.get(
            feed["url"],
            headers={"User-Agent": cfg.FEED_USER_AGENT},
            timeout=cfg.FEED_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return feed, feedparser.parse(resp.content)
    except Exception as exc:
        logger.error(f"Failed to fetch {feed['name']} ({feed.get('target', 'broad')}): {exc}")
        return feed, None


def fetch_feeds(feeds: list[dict]) -> list[tuple[dict, Any]]:
    """Downloads and parses feeds concurrently. Feeds that fail are left out."""
    if not feeds:
        return []
    with ThreadPoolExecutor(max_workers=min(16, len(feeds))) as pool:
        results = list(pool.map(_fetch_feed, feeds))
    return [(feed, parsed) for feed, parsed in results if parsed is not None]


# ── Turning entries into articles ─────────────────────────────────────────────

def _publisher(entry, feed: dict) -> str:
    """The outlet behind an entry: the search feed's publisher field, else the feed's own name."""
    if feed.get("kind") != "search":
        return feed["name"]
    source = entry.get("source")
    if isinstance(source, dict) and source.get("title"):
        return str(source["title"]).strip()
    if entry.get("news_source"):
        return str(entry["news_source"]).strip()
    return feed["name"]


def _clean_title(title: str, publisher: str) -> str:
    """Google News appends " - Publisher" to every title; strip it so duplicates line up."""
    suffix = f" - {publisher}"
    return title[: -len(suffix)].strip() if publisher and title.endswith(suffix) else title


def _trust(feed: dict, publisher: str) -> float:
    if feed.get("kind") != "search":
        return feed["trust_weight"]
    return cfg.SOURCE_TRUST.get(publisher, cfg.SEARCH_TRUST_DEFAULT)


def published_at(entry) -> Optional[datetime]:
    """
    The entry's publication time in UTC. feedparser's *_parsed fields are UTC struct_times, so they are
    converted with calendar.timegm. (The crypto collector's _parse_published_date uses time.mktime,
    which reads them as LOCAL time: its ages are off by the machine's UTC offset outside Docker.)
    """
    for attr in ("published_parsed", "updated_parsed"):
        st = entry.get(attr)
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return None


class _Entry:
    """The fields _entry_matches_asset reads, with the cleaned title and summary."""
    def __init__(self, title: str, summary: str, tags):
        self.title, self.summary, self.tags = title, summary, tags


def build_articles(
    parsed_feeds: list[tuple[dict, Any]],
    targets: dict[str, dict],
    now: Optional[datetime] = None,
) -> dict[str, list[dict]]:
    """
    Pure step (no network): parsed feeds -> {target id: [article, ...]}, newest first.

    A search feed's entries are only considered for the target it searched for; a broad feed's entries
    for every target. An entry can belong to several targets (company news on both Ape collections, or a
    collection and the market); each gets its own article, because sentiment is judged per target.
    """
    now = now or datetime.now(tz=timezone.utc)
    out: dict[str, list[dict]] = {target_id: [] for target_id in targets}
    seen: dict[str, set[str]] = {target_id: set() for target_id in targets}

    for feed, parsed in parsed_feeds:
        candidates = [feed["target"]] if feed.get("kind") == "search" else list(targets)
        candidates = [t for t in candidates if t in targets]
        if not candidates:
            continue
        for entry in parsed.entries:
            publisher = _publisher(entry, feed)
            title = _clean_title((entry.get("title") or "").strip(), publisher)
            if not title:
                continue
            published = published_at(entry)
            if published is None:
                continue                            # undated: its age, and so its weight, is unknown
            age_hours = (now - published).total_seconds() / 3600
            if age_hours > cfg.NFT_MAX_ARTICLE_AGE_HOURS:
                continue
            summary = _clean_html(entry.get("summary") or "")
            if summary.startswith(title):          # Google News' summary is just the title again
                summary = summary[len(title):].strip(" -")
                if summary == publisher:
                    summary = ""
            summary = summary[: cfg.SUMMARY_MAX_CHARS]
            probe = _Entry(title, summary, entry.get("tags", []))

            for target_id in candidates:
                asset = targets[target_id]
                is_match, relevance = _entry_matches_asset(probe, asset)
                if not is_match or relevance < asset.get("min_relevance", 0.0):
                    continue
                key = re.sub(r"\W+", " ", title.lower()).strip()
                if key in seen[target_id]:
                    continue
                seen[target_id].add(key)
                out[target_id].append({
                    "title": title,
                    "summary": summary,
                    "full_text": f"{title}. {summary}" if summary else title,
                    "link": entry.get("link", ""),
                    "source": publisher,
                    "via": feed["name"] if feed.get("kind") == "search" else None,
                    "trust_weight": _trust(feed, publisher),
                    "published": published.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "asset_id": target_id,
                    "slug": target_id,
                    "relevance_score": relevance,
                })

    for target_id, articles in out.items():
        if articles:
            articles.sort(key=lambda a: a["age_hours"])
            articles = _cluster_near_duplicates(articles)
            articles.sort(key=lambda a: a["age_hours"])
        out[target_id] = articles
    return out


def collect(slugs=None, include_market: bool = True, parsed_feeds=None) -> dict[str, list[dict]]:
    """Fetches every source once and returns the articles for every target."""
    t0 = time.perf_counter()
    targets = targets_for(slugs, include_market)
    if parsed_feeds is None:
        feeds = broad_feeds() + [f for tid, t in targets.items() for f in search_feeds(tid, t)]
        parsed_feeds = fetch_feeds(feeds)
    articles = build_articles(parsed_feeds, targets)
    logger.info(
        f"Collected NFT articles from {len(parsed_feeds)} feeds in {time.perf_counter() - t0:.2f}s: "
        + ", ".join(f"{k}={len(v)}" for k, v in articles.items())
    )
    return articles
