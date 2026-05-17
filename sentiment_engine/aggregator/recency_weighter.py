"""
aggregator/recency_weighter.py

Applies exponential time-decay to article NLP scores.
Recent articles carry more weight than old ones.

Decay formula:
    weight = 0.5 ^ (age_hours / HALF_LIFE_HOURS)

So at half-life (e.g. 12 hours), an article is worth 50% of a fresh one.
At 24 hours, it's worth 25%. At 72 hours, it's worth ~1.5%.
"""

from __future__ import annotations

import math

from utils.config import RECENCY_HALF_LIFE_HOURS
from utils.logger import get_logger

logger = get_logger("recency_weighter")


def recency_weight(age_hours: float) -> float:
    """
    Computes the recency weight for an article given its age in hours.

    Args:
        age_hours: How old the article is in hours (0 = just published)

    Returns:
        float in (0.0, 1.0] — 1.0 for brand new, decays exponentially
    """
    if age_hours <= 0:
        return 1.0
    return round(math.pow(0.5, age_hours / RECENCY_HALF_LIFE_HOURS), 6)


def apply_recency_weights(articles: list[dict]) -> list[dict]:
    """
    Adds recency_weight and recency_adjusted_score to each article.

    recency_adjusted_score = nlp_score * recency_weight * trust_weight

    This is the final per-article contribution score before aggregation.
    """
    weighted = []
    for article in articles:
        age   = article.get("age_hours", 0.0)
        score = article.get("trust_weighted_score", article.get("nlp_score", 0.0))
        rw    = recency_weight(age)

        adjusted = round(score * rw, 4)

        weighted.append({
            **article,
            "recency_weight":          rw,
            "recency_adjusted_score":  adjusted,
        })

    logger.info(
        f"Applied recency weights to {len(weighted)} articles. "
        f"Effective age range: {min(a['age_hours'] for a in weighted):.1f}h "
        f"– {max(a['age_hours'] for a in weighted):.1f}h"
        if weighted else "No articles to weight."
    )

    return weighted
