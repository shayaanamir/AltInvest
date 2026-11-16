"""
collectors/rss_collector.py

Fetches articles from all configured RSS feeds, filters by asset keyword,
and returns normalised article dictionaries ready for NLP scoring.

The feeds come from collectors/feed_cache.py, which downloads each feed at most once per cache period
however many assets ask (a cycle over all assets makes about 10 requests, not about 150).
"""

from __future__ import annotations

import calendar
import re
import time
from datetime import datetime, timezone
from typing import Optional

try:
    from sentiment_engine.collectors import feed_cache, news_search
    from sentiment_engine.utils.config import RSS_FEEDS, ASSETS, MAX_ARTICLE_AGE_HOURS
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from collectors import feed_cache, news_search
    from utils.config import RSS_FEEDS, ASSETS, MAX_ARTICLE_AGE_HOURS
    from utils.logger import get_logger

logger = get_logger("rss_collector")


def _parse_published_date(entry) -> Optional[datetime]:
    # feedparser's *_parsed fields are UTC struct_times, so calendar.timegm (not time.mktime, which reads
    # them as local time and shifts every age by the machine's UTC offset outside Docker).
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
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


def _count(pattern: str, text: str, flags: int = 0) -> int:
    return len(re.findall(pattern, text, flags))


def _entry_matches_asset(entry, asset: dict) -> tuple[bool, float]:
    """
    Determines whether an RSS entry is actually about the target asset.

    `asset` is the asset's config block (see ASSETS in utils/config.py):
      - names:   unambiguous full names, matched case-insensitively on word
                 boundaries anywhere in the entry.
      - tickers: a "$TICKER" cashtag always matches. A bare ticker matches
                 case-insensitively, unless the asset is marked
                 ambiguous_ticker (the ticker is also an everyday word:
                 link, near, uni, atom, dot, ...). Those only match when
                 written in UPPERCASE in the TITLE ("LINK jumps 10%", not
                 "click the link").

    Title hits are weighted 3x over summary/tag hits — a name in the headline
    is a much stronger relevance signal than an incidental body mention.

    Returns:
        (is_match, relevance_score)
    """
    title = (getattr(entry, "title", "") or "")
    summary = (getattr(entry, "summary", "") or "")
    tags = " ".join(t.term for t in getattr(entry, "tags", []) if hasattr(t, "term"))

    body = f"{summary} {tags}"
    title_hits = 0
    body_hits = 0

    for name in asset["names"]:
        pattern = r"\b" + re.escape(name) + r"\b"
        title_hits += _count(pattern, title, re.IGNORECASE)
        body_hits += _count(pattern, body, re.IGNORECASE)

    ambiguous = asset.get("ambiguous_ticker", False)
    for ticker in asset["tickers"]:
        cashtag = r"(?<![A-Za-z0-9$])\$" + re.escape(ticker) + r"\b"
        title_hits += _count(cashtag, title, re.IGNORECASE)
        body_hits += _count(cashtag, body, re.IGNORECASE)

        bare = r"(?<![$A-Za-z0-9])" + re.escape(ticker) + r"\b"
        if ambiguous:
            title_hits += _count(r"(?<![$A-Za-z0-9])" + re.escape(ticker.upper()) + r"\b", title)
        else:
            title_hits += _count(bare, title, re.IGNORECASE)
            body_hits += _count(bare, body, re.IGNORECASE)

    relevance = title_hits * 3 + body_hits
    return relevance > 0, float(relevance)


def _clean_html(raw: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class _Probe:
    """The fields _entry_matches_asset reads, for text that has been cleaned before matching."""
    def __init__(self, title: str, summary: str, tags):
        self.title, self.summary, self.tags = title, summary, tags


def _without_excluded(text: str, asset: dict) -> str:
    """`text` with the asset's exclude_names (a different coin's name that contains this one's) blanked out."""
    for phrase in asset.get("exclude_names", []):
        text = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", text, flags=re.IGNORECASE)
    return text


def _match(title: str, summary: str, tags, asset: dict) -> tuple[bool, float]:
    return _entry_matches_asset(
        _Probe(_without_excluded(title, asset), _without_excluded(summary, asset), tags), asset)


def articles_from_feeds(parsed_feeds: list, asset_id: str, asset: dict) -> list[dict]:
    """
    Pure matching step (no network): [(feed config, parsed feed)] -> this asset's articles, newest first,
    near-duplicates folded together.

    Publisher feeds come first, so when the same headline arrives from a publisher and from a news search the
    publisher's copy (which has a summary) is the one kept. A news-search feed (kind "search", see
    collectors/news_search.py) differs: the outlet is in each entry, the title carries a " - Outlet" suffix,
    price-tracker pages are dropped, and only the newest SEARCH_MAX_PER_ASSET results are used.
    """
    articles        = []
    search_articles = []
    seen_titles     = set()

    ordered = sorted(parsed_feeds, key=lambda pair: pair[0].get("kind") == "search")   # publishers first

    for feed_config, feed in ordered:
        is_search    = feed_config.get("kind") == "search"
        feed_name    = feed_config["name"]
        trust_weight = feed_config["trust_weight"]

        for entry in feed.entries:
            published = _parse_published_date(entry)
            age_hours = _article_age_hours(published)
            if age_hours > MAX_ARTICLE_AGE_HOURS:
                continue

            title   = getattr(entry, "title", "").strip()
            summary = _clean_html(getattr(entry, "summary", ""))
            link    = getattr(entry, "link", "")
            source  = feed_name

            if is_search:
                source  = news_search.publisher(entry, feed_config)
                title   = news_search.clean_title(title, source)
                summary = news_search.clean_summary(summary, title, source)
                if news_search.is_junk(title, source):
                    continue
                trust_weight = news_search.trust_for(source)
            is_match, relevance = _match(title, summary, getattr(entry, "tags", []), asset)
            if not is_match:
                continue

            title_key = title.lower().strip()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            article = {
                "title":        title,
                "summary":      summary,
                "full_text":    f"{title}. {summary}" if summary else title,
                "link":         link,
                "source":       source,
                "via":          feed_name if is_search else None,
                "trust_weight": trust_weight,
                "published":    published.isoformat(),
                "age_hours":    round(age_hours, 2),
                "asset_id":     asset_id,
                "relevance_score": relevance,
            }
            (search_articles if is_search else articles).append(article)

    search_articles.sort(key=lambda a: a["age_hours"])
    articles += search_articles[: news_search.SEARCH_MAX_PER_ASSET]

    articles.sort(key=lambda a: a["age_hours"])
    articles = _cluster_near_duplicates(articles)
    articles.sort(key=lambda a: a["age_hours"])  # re-sort after clustering
    return articles


def fetch_articles_for_asset(asset_id: str) -> list[dict]:
    """
    Articles about the given asset from the publisher feeds plus a Google News search for the coin
    (collectors/news_search.py). Nothing is downloaded here unless the cache is due (collectors/feed_cache.py).
    If the search is unavailable (throttled, blocked) the publisher feeds alone are used.
    """
    if asset_id not in ASSETS:
        raise ValueError(f"Unknown asset: {asset_id}. Must be one of {list(ASSETS.keys())}")

    t0 = time.perf_counter()
    search = news_search.search_feed(asset_id)
    feeds = RSS_FEEDS + ([search] if search else [])
    parsed_feeds = feed_cache.get_feeds(feeds)
    articles = articles_from_feeds(parsed_feeds, asset_id, ASSETS[asset_id])

    via_search = sum(1 for a in articles if a.get("via"))
    elapsed = time.perf_counter() - t0
    logger.info(
        f"{len(articles)} relevant articles for {asset_id.upper()} ({via_search} via news search) "
        f"from {len(parsed_feeds)}/{len(feeds)} feeds in {elapsed:.2f}s"
    )
    return articles


def fetch_articles_for_all_assets() -> dict[str, list[dict]]:
    """Convenience wrapper — fetches articles for every configured asset."""
    return {asset_id: fetch_articles_for_asset(asset_id) for asset_id in ASSETS}