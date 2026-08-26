"""
aggregator/volume_weighter.py

Computes confidence and signal strength metrics based on article volume.

More articles = higher confidence.
15 articles saying "bearish" is a stronger signal than 1 article saying the same.

Also detects whether there's a strong directional consensus
(most articles agree) or high disagreement (mixed sentiment).
"""

from __future__ import annotations

import math

from utils.config import (
    CONFIDENCE_LOW_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    CONFIDENCE_HIGH_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger("volume_weighter")


def compute_confidence(article_count: int) -> float:
    """
    Maps article count to a confidence score [0.0, 1.0].
    Uses a logarithmic curve so marginal articles matter less at high volumes.

    Benchmarks:
        0  articles  → 0.00
        5  articles  → ~0.40  (low confidence)
        15 articles  → ~0.65  (medium confidence)
        30 articles  → ~0.85  (high confidence)
        50+ articles → ~1.00
    """
    if article_count <= 0:
        return 0.0
    # Logarithmic scale anchored at CONFIDENCE_HIGH_THRESHOLD = 1.0
    raw = math.log(article_count + 1) / math.log(CONFIDENCE_HIGH_THRESHOLD + 2)
    return round(min(1.0, raw), 4)


def confidence_label(confidence: float) -> str:
    """Maps a confidence float to a human-readable label."""
    if confidence < 0.40:
        return "low"
    elif confidence < 0.70:
        return "medium"
    else:
        return "high"


def compute_signal_strength(scores: list[float]) -> str:
    """
    Analyses the distribution of NLP scores to determine signal strength.

    Returns one of:
        "strong"    — most articles strongly agree on direction
        "moderate"  — moderate directional agreement
        "weak"      — mixed or near-neutral sentiment
        "conflicted" — scores split roughly evenly between Positive and Negative
    """
    if not scores:
        return "weak"

    n         = len(scores)
    mean      = sum(scores) / n
    Positives = sum(1 for s in scores if s > 0.1)
    Negatives = sum(1 for s in scores if s < -0.1)
    neutrals  = n - Positives - Negatives

    pos_ratio = Positives / n
    neg_ratio = Negatives / n

    # Both directions strongly represented
    if pos_ratio > 0.3 and neg_ratio > 0.3:
        return "conflicted"

    abs_mean = abs(mean)

    if abs_mean >= 0.35:
        return "strong"
    elif abs_mean >= 0.15:
        return "moderate"
    else:
        return "weak"


def compute_volume_metrics(articles: list[dict]) -> dict:
    """
    Computes all volume-based metrics for a set of scored articles.

    Returns:
        {
            "article_count": int,
            "confidence": float,
            "confidence_label": str,
            "signal_strength": str,
            "Positive_count": int,
            "Negative_count": int,
            "neutral_count": int,
            "source_count": int,       # how many distinct sources contributed
        }
    """
    n      = len(articles)
    scores = [a.get("nlp_score", 0.0) for a in articles]

    pos = sum(1 for s in scores if s > 0.1)
    neg = sum(1 for s in scores if s < -0.1)
    neu = n - pos - neg

    sources = set(a.get("source", "unknown") for a in articles)

    confidence = compute_confidence(n)
    strength   = compute_signal_strength(scores)

    logger.info(
        f"Volume metrics: {n} articles, {len(sources)} sources, "
        f"confidence={confidence} ({confidence_label(confidence)}), "
        f"signal={strength}, +{pos}/-{neg}/~{neu}"
    )

    return {
        "article_count":    n,
        "confidence":       confidence,
        "confidence_label": confidence_label(confidence),
        "signal_strength":  strength,
        "positive_count":   pos,
        "negative_count":   neg,
        "neutral_count":    neu,
        "source_count":     len(sources),
    }
