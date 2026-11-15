"""
nft_sentiment/aggregator.py

Turns one collection's articles and market signal into a sentiment reading:

    1. keep the newest NFT_MAX_ARTICLES_SCORED articles
    2. score them with the LLM (groq_scorer); any it could not score go to VADER + FinBERT
    3. drop the articles the LLM judged not to be about the collection
    4. weight each article by recency (48h half-life) x source trust
    5. blend news (65%) with the market signal (35%), or use news alone when there is no market signal
    6. confidence from the number of distinct STORIES (the LLM links rewordings of one event, which
       otherwise dominate: one NFT sale story ran ~10 times in a week), trend against the reading ~24h ago

Pure: no database, no feed fetching. The caller passes articles, the market signal and the trend history.
The output mirrors the crypto pipeline's (sentiment_score in -1..1, confidence, trend, top_headlines, ...)
keyed by slug, and states that it has not been validated against human labels.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Callable, Optional

try:
    from sentiment_engine.nft_sentiment import config as cfg
    from sentiment_engine.nft_sentiment import groq_scorer
    from sentiment_engine.aggregator.sentiment_aggregator import _detect_trend, _weighted_mean
    from sentiment_engine.aggregator.volume_weighter import compute_signal_strength, confidence_label
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from nft_sentiment import config as cfg
    from nft_sentiment import groq_scorer
    from aggregator.sentiment_aggregator import _detect_trend, _weighted_mean
    from aggregator.volume_weighter import compute_signal_strength, confidence_label
    from utils.logger import get_logger

logger = get_logger("nft_aggregator")

VALIDATION_NOTE = (
    "Scored by an LLM without validation against human-labelled NFT headlines. "
    "Treat it as a summary of recent news and trading, not a forecast of the floor price."
)


class ScoringUnavailable(Exception):
    """No article could be scored by any scorer; the caller should keep the last good reading."""


def _default_fallback(articles: list[dict]) -> list[dict]:
    """The crypto pipeline's VADER + FinBERT ensemble (FinBERT is loaded lazily, once per process)."""
    try:
        from sentiment_engine.nlp.ensemble_scorer import score_articles
    except ImportError:
        from nlp.ensemble_scorer import score_articles
    return [{**a, "relevant": None} for a in score_articles(articles)]


def recency_weight(age_hours: float) -> float:
    if age_hours <= 0:
        return 1.0
    return math.pow(0.5, age_hours / cfg.NFT_RECENCY_HALF_LIFE_HOURS)


def compute_confidence(n_articles: int) -> float:
    if n_articles <= 0:
        return 0.0
    return round(min(1.0, math.log(n_articles + 1) / math.log(cfg.NFT_CONFIDENCE_FULL_ARTICLES + 1)), 4)


def _scorer_label(n_llm: int, n_fallback: int) -> tuple[str, bool]:
    """(label for the reading's `source`, llm_unavailable)."""
    model = cfg.model_name().split("/")[-1]
    if n_fallback == 0:
        return f"LLM ({model} on Groq)", False
    if n_llm == 0:
        return "VADER + FinBERT (LLM unavailable)", True
    return f"LLM ({model} on Groq), partly VADER + FinBERT", True


def group_stories(articles: list[dict]) -> list[list[int]]:
    """
    Indexes of `articles` grouped by story, in first-seen order. LLM-scored articles carry story_id;
    any without one (fallback-scored) are a story of their own.
    """
    groups: dict[tuple, list[int]] = {}
    for i, a in enumerate(articles):
        sid = ("llm", a["story_id"]) if a.get("story_id") is not None else ("own", i)
        groups.setdefault(sid, []).append(i)
    return list(groups.values())


def _top_headlines(articles: list[dict], weights: list[float], base: list[float],
                   stories: list[list[int]], n: int = 5) -> list[dict]:
    """
    One headline per story (its freshest, most trusted copy), ranked by how much the story moved the
    news score. A story's contribution is its share of the weighted mean, so all contributions add up
    to the news score in -1..1. `copies` says how many outlets ran it.
    """
    total = sum(weights)
    ranked = []
    for members in stories:
        contribution = sum(articles[i]["nlp_score"] * weights[i] for i in members) / total if total else 0.0
        lead = articles[max(members, key=lambda i: base[i])]
        ranked.append((contribution, lead, len(members)))
    ranked.sort(key=lambda item: abs(item[0]), reverse=True)
    return [
        {
            "title": a.get("title", ""),
            "score": round(a["nlp_score"], 4),
            "contribution": round(contribution, 4),
            "label": a.get("llm_label"),
            "reason": a.get("llm_reason"),
            "source": a.get("source", ""),
            "copies": copies,
            "age_hours": a.get("age_hours", 0.0),
            "link": a.get("link", ""),
        }
        for contribution, a, copies in ranked[:n]
    ]


def neutral_output(slug: str, name: str, timestamp: datetime, reason: str = "no_articles", **quality) -> dict:
    """Placeholder when there is nothing to score. Confidence 0 marks it as not a reading."""
    return {
        "slug": slug,
        "name": name,
        "sentiment_score": 0.0,
        "source": None,
        "confidence": 0.0,
        "confidence_label": "low",
        "signal_strength": "weak",
        "trend": "unknown",
        "last_updated": timestamp.isoformat(),
        "article_count": 0,
        "story_count": 0,
        "source_count": 0,
        "source_breakdown": {"news_nlp": None, "market_signals": None},
        "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
        "top_headlines": [],
        "market_signals": {},
        "articles_by_source": {},
        "data_quality": {"reason": reason, **quality},
        "validated": False,
        "validation_note": VALIDATION_NOTE,
    }


def run_collection_pipeline(
    slug: str,
    name: str,
    articles: list[dict],
    market_signal: Optional[dict] = None,
    history: Optional[list[dict]] = None,
    now: Optional[datetime] = None,
    scorer: Callable = groq_scorer.score_articles,
    fallback: Callable = _default_fallback,
) -> dict:
    """
    One collection's reading. `market_signal` is market_signals.build_market_signal(...) or None (the
    NFT market pseudo-collection has none). `history` is the stored readings around 24h ago, for trend.

    Raises ScoringUnavailable when there were articles but no scorer could score any of them.
    """
    now = now or datetime.now(tz=timezone.utc)
    if not articles:
        return neutral_output(slug, name, now)

    candidates = sorted(articles, key=lambda a: a.get("age_hours", 0.0))[: cfg.NFT_MAX_ARTICLES_SCORED]

    llm_scored, unscored = scorer(slug, name, candidates)
    fallback_scored: list[dict] = []
    if unscored:
        try:
            fallback_scored = fallback(unscored)
        except Exception as exc:
            logger.error(f"Fallback scorer failed for {slug}: {exc}")
    if not llm_scored and not fallback_scored:
        raise ScoringUnavailable(f"no article could be scored for {slug}")

    scored = llm_scored + fallback_scored
    relevant = [a for a in scored if a.get("relevant") is not False]
    dropped = len(scored) - len(relevant)
    source, llm_unavailable = _scorer_label(len(llm_scored), len(fallback_scored))

    if not relevant:
        return neutral_output(slug, name, now, irrelevant_dropped=dropped, llm_unavailable=llm_unavailable)

    # Rewordings of one event count once: an article's weight is shared with the other copies of its story.
    stories = group_stories(relevant)
    base = [recency_weight(a.get("age_hours", 0.0)) * a.get("trust_weight", 1.0) for a in relevant]
    weights = [0.0] * len(relevant)
    for members in stories:
        for i in members:
            weights[i] = base[i] / len(members)
    scores = [a["nlp_score"] for a in relevant]
    news_raw = _weighted_mean(scores, weights)            # -1..1
    news_01 = round((news_raw + 1) / 2, 4)
    story_scores = [_weighted_mean([scores[i] for i in m], [base[i] for i in m]) for m in stories]

    use_market = bool(market_signal) and not market_signal.get("is_fallback", True)
    if use_market:
        final_01 = cfg.NFT_NEWS_WEIGHT * news_01 + cfg.NFT_MARKET_SIGNAL_WEIGHT * market_signal["score"]
    else:
        final_01 = news_01
    final_score = round(final_01 * 2 - 1, 4)

    n = len(relevant)
    n_stories = len(stories)
    confidence = compute_confidence(n_stories)
    trend = _detect_trend(final_score, history or [], now)

    by_source: dict[str, int] = {}
    for a in relevant:
        by_source[a.get("source", "unknown")] = by_source.get(a.get("source", "unknown"), 0) + 1

    pos = sum(1 for s in story_scores if s > 0.1)
    neg = sum(1 for s in story_scores if s < -0.1)

    output = {
        "slug": slug,
        "name": name,
        "sentiment_score": final_score,
        "source": source,
        "confidence": confidence,
        "confidence_label": confidence_label(confidence),
        "signal_strength": compute_signal_strength(story_scores),
        "trend": trend,
        "last_updated": now.isoformat(),
        "article_count": n,
        "story_count": n_stories,
        "source_count": len(by_source),
        "source_breakdown": {
            "news_nlp": news_01,
            "market_signals": market_signal["score"] if use_market else None,
        },
        "sentiment_distribution": {"positive": pos, "negative": neg, "neutral": n_stories - pos - neg},
        "top_headlines": _top_headlines(relevant, weights, base, stories),
        "market_signals": {
            "price_change_24h": market_signal.get("price_change_24h"),
            "price_change_7d": market_signal.get("price_change_7d"),
            "activity_ratio": market_signal.get("activity_ratio"),
            "as_of": market_signal.get("as_of"),
        } if use_market else {},
        "articles_by_source": by_source,
        "data_quality": {
            "llm_unavailable": llm_unavailable,
            "llm_scored": len(llm_scored),
            "fallback_scored": len(fallback_scored),
            "irrelevant_dropped": dropped,
            "market_fallback": market_signal is not None and not use_market,
        },
        "validated": False,
        "validation_note": VALIDATION_NOTE,
    }
    logger.info(
        f"NFT sentiment {slug}: score={final_score} confidence={confidence} trend={trend} "
        f"articles={n} stories={n_stories} (dropped {dropped} irrelevant) source={source}"
    )
    return output


def is_placeholder(result: dict) -> bool:
    """True for a neutral 'nothing to score' output, which must not overwrite a real reading."""
    return bool((result.get("data_quality") or {}).get("reason"))
