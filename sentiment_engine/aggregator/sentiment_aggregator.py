"""
aggregator/sentiment_aggregator.py

The master aggregator. Orchestrates the full pipeline:
    1. Fetch RSS articles
    2. Score with NLP ensemble
    3. Apply recency weights
    4. Fetch CMC market signals
    5. Compute volume/confidence metrics
    6. Blend news NLP + CMC into final sentiment score
    7. Detect trend direction (by comparing to stored history)
    8. Return final structured output

This is the one function Person B's backend calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from collectors.rss_collector  import fetch_articles_for_asset
from collectors.cmc_collector  import fetch_all_signals
from nlp.ensemble_scorer       import score_articles as ensemble_score
from aggregator.recency_weighter import apply_recency_weights
from aggregator.volume_weighter  import compute_volume_metrics
from utils.config import (
    NEWS_NLP_WEIGHT,
    MARKET_SIGNAL_WEIGHT,
    TREND_DELTA_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger("sentiment_aggregator")


def _normalise_nlp_to_0_1(score: float) -> float:
    """
    Converts NLP score from [-1, 1] to [0, 1].
    0.0 = maximally bearish, 0.5 = neutral, 1.0 = maximally bullish.
    """
    return round((score + 1) / 2, 4)


def _weighted_mean(scores: list[float], weights: list[float]) -> float:
    """Computes a weighted mean of scores. Falls back to simple mean if weights sum to 0."""
    total_weight = sum(weights)
    if total_weight == 0:
        return sum(scores) / len(scores) if scores else 0.5
    return round(sum(s * w for s, w in zip(scores, weights)) / total_weight, 4)


def _detect_trend(current_score: float, history: list[dict]) -> str:
    """
    Compares current score against the most recent historical score.
    Returns 'improving', 'deteriorating', or 'stable'.
    """
    if not history:
        return "stable"

    # Most recent historical entry
    previous = sorted(history, key=lambda h: h.get("timestamp", ""), reverse=True)
    if not previous:
        return "stable"

    prev_score = previous[0].get("sentiment_score", 0.0)
    delta      = current_score - prev_score

    if delta > TREND_DELTA_THRESHOLD:
        return "improving"
    elif delta < -TREND_DELTA_THRESHOLD:
        return "deteriorating"
    else:
        return "stable"


def _extract_top_headlines(articles: list[dict], n: int = 5) -> list[dict]:
    """
    Returns the top N most impactful headlines (highest absolute nlp_score),
    sorted by absolute score descending.
    """
    sorted_articles = sorted(
        articles,
        key=lambda a: abs(a.get("nlp_score", 0.0)),
        reverse=True
    )

    return [
        {
            "title":  a.get("title", ""),
            "score":  round(a.get("nlp_score", 0.0), 4),
            "source": a.get("source", ""),
            "age_hours": a.get("age_hours", 0.0),
            "link":   a.get("link", ""),
        }
        for a in sorted_articles[:n]
    ]


def _source_breakdown(articles: list[dict]) -> dict[str, int]:
    """Returns article count per source."""
    breakdown = {}
    for a in articles:
        src = a.get("source", "unknown")
        breakdown[src] = breakdown.get(src, 0) + 1
    return breakdown


def run_pipeline(
    asset_id: str,
    history: Optional[list[dict]] = None,
    return_raw_articles: bool = False,
) -> dict | tuple[dict, list[dict]]:
    """
    Full sentiment pipeline for a single asset.

    Args:
        asset_id: e.g. "btc", "eth"
        history:  Previous sentiment scores for trend detection.
                  Pass in from MongoDB via storage/mongo_handler.py.
                  If None, trend will be "stable".
        return_raw_articles: if True, returns (output, raw_articles) instead
            of just output — lets callers reuse the articles already fetched
            here instead of re-fetching for storage purposes.

    Returns:
        Fully structured sentiment output dict (matches API contract),
        or (output, raw_articles) tuple if return_raw_articles is True.
    """
    logger.info(f"═══ Running sentiment pipeline for {asset_id.upper()} ═══")
    timestamp = datetime.now(tz=timezone.utc)

    # ── Step 1: Fetch articles ────────────────────────────────────────────────
    raw_articles = fetch_articles_for_asset(asset_id)

    if not raw_articles:
        logger.warning(f"No articles found for {asset_id}. Returning neutral output.")
        neutral = _neutral_output(asset_id, timestamp)
        return (neutral, raw_articles) if return_raw_articles else neutral

    # ── Step 2: NLP scoring ───────────────────────────────────────────────────
    scored_articles = ensemble_score(raw_articles)

    # ── Step 3: Recency weighting ─────────────────────────────────────────────
    weighted_articles = apply_recency_weights(scored_articles)

    # ── Step 4: CMC market signals ────────────────────────────────────────────
    cmc_data = fetch_all_signals(asset_id)
    cmc_score = cmc_data["final_cmc_score"]

    # ── Step 5: Volume / confidence metrics ───────────────────────────────────
    volume_metrics = compute_volume_metrics(scored_articles)

    # ── Step 6: Compute weighted NLP score ───────────────────────────────────
    # Use recency_adjusted_score as the weight for each article's contribution
    recency_scores  = [a["recency_adjusted_score"] for a in weighted_articles]
    recency_weights = [a["recency_weight"] * a.get("trust_weight", 1.0) for a in weighted_articles]

    raw_nlp_score = _weighted_mean(recency_scores, recency_weights)
    nlp_score_01  = _normalise_nlp_to_0_1(raw_nlp_score)

    # ── Step 7: Blend NLP + CMC ───────────────────────────────────────────────
    final_score_01 = (NEWS_NLP_WEIGHT * nlp_score_01) + (MARKET_SIGNAL_WEIGHT * cmc_score)
    final_score = round((final_score_01 * 2.0) - 1.0, 4)

    # ── Step 8: Trend detection ───────────────────────────────────────────────
    trend = _detect_trend(final_score, history or [])

    # ── Assemble output ───────────────────────────────────────────────────────
    output = {
        # Core contract fields (what Person B needs)
        "asset_id":        asset_id,
        "sentiment_score": final_score,          # 0.0 – 1.0
        "confidence":      volume_metrics["confidence"],
        "confidence_label": volume_metrics["confidence_label"],
        "signal_strength": volume_metrics["signal_strength"],
        "trend":           trend,
        "last_updated":    timestamp.isoformat(),

        # Breakdown
        "article_count":  volume_metrics["article_count"],
        "source_count":   volume_metrics["source_count"],
        "source_breakdown": {
            "news_nlp":        round(nlp_score_01, 4),
            "market_signals":  round(cmc_score, 4),
        },

        # Volume detail
        "sentiment_distribution": {
            "positive": volume_metrics["positive_count"],
            "negative": volume_metrics["negative_count"],
            "neutral":  volume_metrics["neutral_count"],
        },

        # Top headlines
        "top_headlines": _extract_top_headlines(weighted_articles),

        # CMC detail
        "market_signals": {
            "price_change_24h":  cmc_data["quote"]["price_change_24h"],
            "volume_change_24h": cmc_data["quote"]["volume_change_24h"],
            "is_trending":       cmc_data["is_trending"],
            "btc_dominance":     cmc_data["global"]["btc_dominance"],
        },

        # Per-source article counts
        "articles_by_source": _source_breakdown(scored_articles),
    }

    logger.info(
        f"Pipeline complete for {asset_id.upper()} | "
        f"score={final_score} | confidence={volume_metrics['confidence']} | "
        f"trend={trend} | articles={volume_metrics['article_count']}"
    )

    return (output, raw_articles) if return_raw_articles else output


def _neutral_output(asset_id: str, timestamp: datetime) -> dict:
    """
    Returns a neutral output when no data is available.
    Confidence is 0.0 to signal to Person B that this is unreliable.
    """
    return {
        "asset_id":           asset_id,
        "sentiment_score":    0.0,
        "confidence":         0.0,
        "confidence_label":   "low",
        "signal_strength":    "weak",
        "trend":              "stable",
        "last_updated":       timestamp.isoformat(),
        "article_count":      0,
        "source_count":       0,
        "source_breakdown":   {"news_nlp": 0.5, "market_signals": 0.5},
        "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
        "top_headlines":      [],
        "market_signals":     {},
        "articles_by_source": {},
    }
