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

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from sentiment_engine.collectors.rss_collector import fetch_articles_for_asset
    from sentiment_engine.collectors.cmc_collector import fetch_all_signals
    from sentiment_engine.nlp.ensemble_scorer import score_articles as ensemble_score
    from sentiment_engine.aggregator.recency_weighter import apply_recency_weights
    from sentiment_engine.aggregator.volume_weighter import compute_volume_metrics
    from sentiment_engine.utils.config import (
        NEWS_NLP_WEIGHT,
        MARKET_SIGNAL_WEIGHT,
        TREND_DELTA_THRESHOLD,
        TREND_LOOKBACK_HOURS,
        TREND_TOLERANCE_HOURS,
    )
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from collectors.rss_collector import fetch_articles_for_asset
    from collectors.cmc_collector import fetch_all_signals
    from nlp.ensemble_scorer import score_articles as ensemble_score
    from aggregator.recency_weighter import apply_recency_weights
    from aggregator.volume_weighter import compute_volume_metrics
    from utils.config import (
        NEWS_NLP_WEIGHT,
        MARKET_SIGNAL_WEIGHT,
        TREND_DELTA_THRESHOLD,
        TREND_LOOKBACK_HOURS,
        TREND_TOLERANCE_HOURS,
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


def _parse_ts(value) -> Optional[datetime]:
    """Parses a stored timestamp (ISO string or datetime) to an aware UTC datetime."""
    if isinstance(value, datetime):
        ts = value
    else:
        try:
            ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _detect_trend(current_score: float, history: list[dict], now: Optional[datetime] = None) -> str:
    """
    Compares the current score with the stored reading closest to TREND_LOOKBACK_HOURS
    ago (24h), counting only readings within TREND_TOLERANCE_HOURS of that point.

    Returns 'improving', 'deteriorating' or 'stable' — or 'unknown' when there is no
    reading that old, so a lack of history isn't reported as a flat market.
    """
    now = now or datetime.now(tz=timezone.utc)
    target = now - timedelta(hours=TREND_LOOKBACK_HOURS)
    tolerance = timedelta(hours=TREND_TOLERANCE_HOURS)

    baseline, best_gap = None, None
    for h in history:
        ts = _parse_ts(h.get("timestamp") or h.get("last_updated"))
        if ts is None or h.get("sentiment_score") is None:
            continue
        # Skip the neutral placeholders written when no articles were found.
        if not (h.get("confidence") or 0) > 0 or (h.get("data_quality") or {}).get("reason") == "no_articles":
            continue
        gap = abs(ts - target)
        if gap <= tolerance and (best_gap is None or gap < best_gap):
            baseline, best_gap = h, gap

    if baseline is None:
        return "unknown"

    delta = current_score - baseline["sentiment_score"]

    if delta > TREND_DELTA_THRESHOLD:
        return "improving"
    elif delta < -TREND_DELTA_THRESHOLD:
        return "deteriorating"
    else:
        return "stable"


def _load_trend_history(asset_id: str) -> list[dict]:
    """Fetches the ~24h-ago readings for trend detection; [] if storage is unavailable."""
    try:
        try:
            from sentiment_engine.storage.mongo_handler import get_trend_baseline
        except ImportError:
            from storage.mongo_handler import get_trend_baseline
        return get_trend_baseline(asset_id)
    except Exception as exc:
        logger.warning(f"Could not load trend baseline for {asset_id}: {exc}")
        return []


def _extract_top_headlines(articles: list[dict], n: int = 5) -> list[dict]:
    """
    Returns the N headlines that moved the news score the most, largest effect first.

    `contribution` is the article's share of the weighted mean in run_pipeline —
    nlp_score * (recency_weight * trust_weight) / sum of those weights — so the
    contributions of ALL articles add up to the news score itself. A strongly-worded
    but old or low-trust article therefore ranks below a milder fresh, trusted one.
    Each headline also carries the blended score and the VADER and FinBERT scores it
    was blended from.
    """
    weights = [a.get("recency_weight", 1.0) * a.get("trust_weight", 1.0) for a in articles]
    total = sum(weights)
    ranked = sorted(
        ((a.get("nlp_score", 0.0) * w / total if total else 0.0, a) for a, w in zip(articles, weights)),
        key=lambda pair: abs(pair[0]),
        reverse=True,
    )

    return [
        {
            "title":  a.get("title", ""),
            "score":  round(a.get("nlp_score", 0.0), 4),
            "contribution": round(contribution, 4),
            "vader_score":   _round_or_none(a.get("vader_score")),
            "finbert_score": _round_or_none(a.get("finbert_score")),
            "source": a.get("source", ""),
            "age_hours": a.get("age_hours", 0.0),
            "link":   a.get("link", ""),
        }
        for contribution, a in ranked[:n]
    ]


def _scoring_source(articles: list[dict]) -> tuple[str, bool]:
    """
    Describes which models actually scored the articles, so the label never claims
    FinBERT when it didn't run. Returns (source label, finbert_unavailable).
    """
    with_finbert = sum(1 for a in articles if a.get("nlp_models") == "vader+finbert")
    if with_finbert == len(articles):
        return "Ensemble (VADER + FinBERT)", False
    if with_finbert == 0:
        return "VADER only (FinBERT unavailable)", True
    return "Ensemble (VADER + FinBERT, partial)", True


def _round_or_none(value: Optional[float]) -> Optional[float]:
    return round(value, 4) if value is not None else None


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
        history:  Stored readings for trend detection. Normally omitted: when None, the
                  readings around 24h ago are loaded from MongoDB. Pass a list to
                  override (e.g. in tests). With no reading near 24h old the trend is
                  "unknown".
        return_raw_articles: if True, returns (output, raw_articles) instead
            of just output — lets callers reuse the articles already fetched
            here instead of re-fetching for storage purposes.

    Returns:
        Fully structured sentiment output dict (matches API contract),
        or (output, raw_articles) tuple if return_raw_articles is True.
    """
    logger.info(f"═══ Running sentiment pipeline for {asset_id.upper()} ═══")
    timestamp = datetime.now(tz=timezone.utc)

    # ── Steps 1 & 4: fetch RSS articles and CMC signals concurrently ──────────
    # Independent I/O calls — no reason to pay their latency sequentially.
    with ThreadPoolExecutor(max_workers=2) as executor:
        articles_future = executor.submit(fetch_articles_for_asset, asset_id)
        cmc_future      = executor.submit(fetch_all_signals, asset_id)

        raw_articles = articles_future.result()
        cmc_data     = cmc_future.result()

    if not raw_articles:
        logger.warning(f"No articles found for {asset_id}. Returning neutral output.")
        neutral = _neutral_output(asset_id, timestamp)
        return (neutral, raw_articles) if return_raw_articles else neutral

    # ── Step 2: NLP scoring ───────────────────────────────────────────────────
    scored_articles = ensemble_score(raw_articles)

    # ── Step 3: Recency weighting ─────────────────────────────────────────────
    weighted_articles = apply_recency_weights(scored_articles)

    cmc_score = cmc_data["final_cmc_score"]

    # ── Step 5: Volume / confidence metrics ───────────────────────────────────
    volume_metrics = compute_volume_metrics(scored_articles)

    # ── Step 6: Compute weighted NLP score ───────────────────────────────────
    # Weighted mean of raw nlp_score, with recency * trust as the weights.
    # recency_adjusted_score must NOT be used here — it already has recency and
    # trust multiplied in, so weighting it again would double-apply them and
    # shrink the result toward neutral.
    nlp_scores  = [a.get("nlp_score", 0.0) for a in weighted_articles]
    nlp_weights = [a["recency_weight"] * a.get("trust_weight", 1.0) for a in weighted_articles]

    raw_nlp_score = _weighted_mean(nlp_scores, nlp_weights)
    nlp_score_01  = _normalise_nlp_to_0_1(raw_nlp_score)

    # ── Step 7: Blend NLP + CMC ───────────────────────────────────────────────
    final_score_01 = (NEWS_NLP_WEIGHT * nlp_score_01) + (MARKET_SIGNAL_WEIGHT * cmc_score)
    final_score = round((final_score_01 * 2.0) - 1.0, 4)

    # ── Step 8: Trend detection ───────────────────────────────────────────────
    if history is None:
        history = _load_trend_history(asset_id)
    trend = _detect_trend(final_score, history)

    # ── Assemble output ───────────────────────────────────────────────────────
    source, finbert_unavailable = _scoring_source(scored_articles)
    quote_fallback  = bool(cmc_data.get("quote", {}).get("is_fallback", False))
    global_fallback = bool(cmc_data.get("global", {}).get("is_fallback", False))

    output = {
        # Core contract fields (what Person B needs)
        "asset_id":        asset_id,
        "sentiment_score": final_score,          # 0.0 – 1.0
        "source":          source,
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

        # CMC detail — fallback values are placeholders, not readings, so they go out as None
        "market_signals": {
            "price_change_24h":  None if quote_fallback else cmc_data["quote"]["price_change_24h"],
            "volume_change_24h": None if quote_fallback else cmc_data["quote"]["volume_change_24h"],
            "is_trending":       cmc_data["is_trending"],
            "btc_dominance":     None if global_fallback else cmc_data["global"]["btc_dominance"],
        },

        # Per-source article counts
        "articles_by_source": _source_breakdown(scored_articles),
        "data_quality": {
            "degraded":          cmc_data.get("degraded", False),
            "cmc_fallback":      quote_fallback or global_fallback,
            "quote_fallback":    quote_fallback,
            "global_fallback":   global_fallback,
            "trending_fallback": cmc_data.get("trending_fallback", False),
            "cmc_key_missing":   cmc_data.get("key_missing", False),
            "finbert_unavailable": finbert_unavailable,
        },
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
        "trend":              "unknown",
        "last_updated":       timestamp.isoformat(),
        "article_count":      0,
        "source_count":       0,
        "source_breakdown":   {"news_nlp": 0.5, "market_signals": 0.5},
        "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
        "top_headlines":      [],
        "market_signals":     {},
        "articles_by_source": {},
        "data_quality":       {"degraded": True, "cmc_fallback": True, "reason": "no_articles"},
    }
