"""
collectors/rss_collector.py

Fetches articles from all configured RSS feeds, filters by asset keyword,
and returns normalised article dictionaries ready for NLP scoring.

Feeds are fetched CONCURRENTLY with a bounded timeout per feed, so total
fetch time is roughly max(single feed latency) instead of sum(all feeds).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

# pyrefly: ignore [missing-import]
import feedparser
import requests

from utils.config import RSS_FEEDS, ASSETS, MAX_ARTICLE_AGE_HOURS
from utils.logger import get_logger

logger = get_logger("rss_collector")

FEED_TIMEOUT_SECONDS = 6   # bounds the slowest feed instead of letting it hang


def _parse_published_date(entry) -> Optional[datetime]:
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
    now = datetime.now(tz=timezone.utc)
    delta = now - published
    return delta.total_seconds() / 3600


def _entry_matches_asset(entry, keywords: list[str]) -> bool:
    text = ""
    if hasattr(entry, "title"):
        text += entry.title.lower() + " "
    if hasattr(entry, "summary"):
        text += entry.summary.lower() + " "
    if hasattr(entry, "tags"):
        text += " ".join(t.term.lower() for t in entry.tags if hasattr(t, "term")) + " "

    return any(kw.lower() in text for kw in keywords)


def _clean_html(raw: str) -> str:
    import re
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _fetch_single_feed(feed_config: dict) -> tuple[dict, "feedparser.FeedParserDict | None"]:
    """
    Fetches ONE feed with a hard timeout via requests, then hands the raw
    bytes to feedparser (which itself has no timeout support — this is
    why we fetch with requests first instead of feedparser.parse(url)).
    """
    feed_name = feed_config["name"]
    feed_url  = feed_config["url"]

    try:
        resp = requests.get(feed_url, timeout=FEED_TIMEOUT_SECONDS)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        return feed_config, parsed
    except requests.exceptions.Timeout:
        logger.error(f"Feed timed out (> {FEED_TIMEOUT_SECONDS}s): {feed_name}")
    except Exception as e:
        logger.error(f"Failed to fetch {feed_name}: {e}")
    return feed_config, None


def fetch_articles_for_asset(asset_id: str) -> list[dict]:
    """
    Fetches articles from all RSS feeds that are relevant to the given asset.
    Feeds are fetched concurrently — total time ≈ slowest feed, not sum of all.
    """
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}. Must be one of {list(ASSETS.keys())}")

    keywords    = ASSETS[asset_id]["keywords"]
    articles    = []
    seen_titles = set()

    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(RSS_FEEDS)) as executor:
        futures = [executor.submit(_fetch_single_feed, fc) for fc in RSS_FEEDS]

        for future in as_completed(futures):
            feed_config, feed = future.result()
            if feed is None:
                continue

            feed_name    = feed_config["name"]
            trust_weight = feed_config["trust_weight"]

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

    articles.sort(key=lambda a: a["age_hours"])

    elapsed = time.perf_counter() - t0
    logger.info(
        f"Fetched {len(articles)} relevant articles for {asset_id.upper()} "
        f"from {len(RSS_FEEDS)} feeds in {elapsed:.2f}s (parallel)"
    )
    return articles


def fetch_articles_for_all_assets() -> dict[str, list[dict]]:
    """Convenience wrapper — fetches articles for every configured asset."""
    return {asset_id: fetch_articles_for_asset(asset_id) for asset_id in ASSETS}