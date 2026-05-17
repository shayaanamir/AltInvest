"""
collectors/rss_collector.py

Fetches articles from all configured RSS feeds, filters by asset keyword,
and returns normalised article dictionaries ready for NLP scoring.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

# pyrefly: ignore [missing-import]
import feedparser

from utils.config import RSS_FEEDS, ASSETS, MAX_ARTICLE_AGE_HOURS
from utils.logger import get_logger

logger = get_logger("rss_collector")


def _parse_published_date(entry) -> Optional[datetime]:
    """
    Attempts to extract a timezone-aware datetime from a feedparser entry.
    Falls back to current UTC time if parsing fails.
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            ts = time.mktime(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            ts = time.mktime(entry.updated_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    logger.warning("Could not parse date for entry, using current UTC time")
    return datetime.now(tz=timezone.utc)


def _article_age_hours(published: datetime) -> float:
    """Returns how many hours old an article is from now."""
    now = datetime.now(tz=timezone.utc)
    delta = now - published
    return delta.total_seconds() / 3600


def _entry_matches_asset(entry, keywords: list[str]) -> bool:
    """
    Returns True if any of the asset keywords appear in the
    title or summary of the feed entry (case-insensitive).
    """
    text = ""
    if hasattr(entry, "title"):
        text += entry.title.lower() + " "
    if hasattr(entry, "summary"):
        text += entry.summary.lower() + " "
    if hasattr(entry, "tags"):
        text += " ".join(t.term.lower() for t in entry.tags if hasattr(t, "term")) + " "

    return any(kw.lower() in text for kw in keywords)


def _clean_html(raw: str) -> str:
    """
    Strips basic HTML tags from summary text.
    feedparser partially handles this but some feeds include raw HTML.
    """
    import re
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def fetch_articles_for_asset(asset_id: str) -> list[dict]:
    """
    Fetches articles from all RSS feeds that are relevant to the given asset.

    Args:
        asset_id: e.g. "btc", "eth". Must exist in ASSETS config.

    Returns:
        List of article dicts, sorted newest-first, filtered by age.
    """
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}. Must be one of {list(ASSETS.keys())}")

    keywords   = ASSETS[asset_id]["keywords"]
    articles   = []
    seen_titles = set()

    for feed_config in RSS_FEEDS:
        feed_name    = feed_config["name"]
        feed_url     = feed_config["url"]
        trust_weight = feed_config["trust_weight"]

        logger.info(f"Fetching feed: {feed_name}")

        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.error(f"Failed to fetch {feed_name}: {e}")
            continue

        if feed.bozo and feed.bozo_exception:
            logger.warning(f"{feed_name} returned a malformed feed: {feed.bozo_exception}")

        for entry in feed.entries:
            if not _entry_matches_asset(entry, keywords):
                continue

            published = _parse_published_date(entry)
            age_hours = _article_age_hours(published)

            if age_hours > MAX_ARTICLE_AGE_HOURS:
                continue

            title   = getattr(entry, "title", "").strip()
            summary = _clean_html(getattr(entry, "summary", ""))
            link    = getattr(entry, "link", "")

            # Deduplicate by title
            title_key = title.lower().strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            articles.append({
                "title":        title,
                "summary":      summary,
                "full_text":    f"{title}. {summary}",
                "link":         link,
                "source":       feed_name,
                "trust_weight": trust_weight,
                "published":    published.isoformat(),
                "age_hours":    round(age_hours, 2),
                "asset_id":     asset_id,
            })

    # Sort newest first
    articles.sort(key=lambda a: a["age_hours"])

    logger.info(f"Fetched {len(articles)} relevant articles for {asset_id.upper()}")
    return articles


def fetch_articles_for_all_assets() -> dict[str, list[dict]]:
    """
    Convenience wrapper — fetches articles for every configured asset.

    Returns:
        Dict of { asset_id: [articles] }
    """
    return {asset_id: fetch_articles_for_asset(asset_id) for asset_id in ASSETS}
