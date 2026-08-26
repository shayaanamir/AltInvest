"""
collectors/rss_collector.py

Fetches articles from all configured RSS feeds, filters by asset keyword,
and returns normalised article dictionaries ready for NLP scoring.

Feeds are fetched CONCURRENTLY with a bounded timeout per feed, so total
fetch time is roughly max(single feed latency) instead of sum(all feeds).
"""

from __future__ import annotations

import re
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


# ── Near-duplicate clustering ────────────────────────────────────────────────

NEAR_DUPLICATE_THRESHOLD = 0.6  # title-token Jaccard similarity

def _title_tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", title.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _cluster_near_duplicates(articles: list[dict]) -> list[dict]:
    """
    Folds near-duplicate articles (same underlying story, different outlets/
    headlines — wire pickups, syndication, churnalism) into a single
    representative article per cluster, so article_count (and therefore
    confidence, which is derived from it) isn't inflated by republication.

    Representative = highest trust_weight in the cluster, ties broken by
    freshness. Each representative carries `duplicate_count` so callers can
    still see how strongly the story was corroborated.
    """
    tokens = [_title_tokens(a.get("title", "")) for a in articles]
    n = len(articles)
    assigned = [-1] * n
    clusters: list[list[int]] = []

    for i in range(n):
        if assigned[i] != -1:
            continue
        cluster = [i]
        assigned[i] = len(clusters)
        for j in range(i + 1, n):
            if assigned[j] != -1:
                continue
            if _jaccard(tokens[i], tokens[j]) >= NEAR_DUPLICATE_THRESHOLD:
                cluster.append(j)
                assigned[j] = len(clusters)
        clusters.append(cluster)

    deduped = []
    for cluster in clusters:
        members = [articles[idx] for idx in cluster]
        representative = max(
            members,
            key=lambda a: (a.get("trust_weight", 0.0), -a.get("age_hours", 0.0)),
        )
        deduped.append({**representative, "duplicate_count": len(members)})

    if len(deduped) < len(articles):
        logger.info(
            f"Near-duplicate clustering: {len(articles)} articles -> "
            f"{len(deduped)} unique stories"
        )

    return deduped


def _entry_matches_asset(entry, keywords: list[str]) -> tuple[bool, float]:
    """
    Determines whether an RSS entry is actually about the target asset.

    Improvements over plain substring matching:
      - Word-boundary matching, so short ambiguous keywords ("sol") don't
        match inside unrelated words ("solar", "console", "solution").
      - Title matches are weighted 3x over summary/tag matches — a keyword
        in the headline is a much stronger relevance signal than an
        incidental mention in the body.
      - Keywords <=3 chars (the collision-prone ones) require at least one
        TITLE match to count; a body-only mention is discounted rather than
        treated as a full match.

    Returns:
        (is_match, relevance_score)
    """
    title = (getattr(entry, "title", "") or "")
    summary = (getattr(entry, "summary", "") or "")
    tags = " ".join(t.term for t in getattr(entry, "tags", []) if hasattr(t, "term"))

    title_lower = title.lower()
    body_lower = f"{summary} {tags}".lower()

    title_hits = 0
    body_hits = 0
    shortest_kw_len = min((len(kw) for kw in keywords), default=0)

    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        title_hits += len(re.findall(pattern, title_lower))
        body_hits += len(re.findall(pattern, body_lower))

    relevance = title_hits * 3 + body_hits

    if shortest_kw_len <= 3 and title_hits == 0 and body_hits > 0:
        # Ambiguous short keyword with only a body mention — discount hard
        # rather than admit it as a confident match.
        return False, relevance * 0.3

    return relevance > 0, float(relevance)


def _clean_html(raw: str) -> str:
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
                is_match, relevance = _entry_matches_asset(entry, keywords)
                if not is_match:
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
                    "relevance_score": relevance,
                })

    articles.sort(key=lambda a: a["age_hours"])
    articles = _cluster_near_duplicates(articles)
    articles.sort(key=lambda a: a["age_hours"])  # re-sort after clustering

    elapsed = time.perf_counter() - t0
    logger.info(
        f"Fetched {len(articles)} relevant articles for {asset_id.upper()} "
        f"from {len(RSS_FEEDS)} feeds in {elapsed:.2f}s (parallel)"
    )
    return articles


def fetch_articles_for_all_assets() -> dict[str, list[dict]]:
    """Convenience wrapper — fetches articles for every configured asset."""
    return {asset_id: fetch_articles_for_asset(asset_id) for asset_id in ASSETS}