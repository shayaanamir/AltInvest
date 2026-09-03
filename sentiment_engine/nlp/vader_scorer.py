"""
nlp/vader_scorer.py

VADER-based sentiment scoring.
VADER (Valence Aware Dictionary and sEntiment Reasoner) is a rule-based model
tuned for social media and short texts. It's fast and needs no GPU.

Scores articles on the cleaned_text field and returns a score in [-1, 1].
"""

from __future__ import annotations

# pyrefly: ignore [missing-import]
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger("vader_scorer")

# Initialise once at module level — expensive to re-create
_analyser = SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    """
    Scores a single piece of text with VADER.

    Returns:
        compound score in range [-1.0, 1.0]
        -1.0 = maximally Negative
         0.0 = neutral
        +1.0 = maximally Positive
    """
    if not text or not text.strip():
        return 0.0

    scores = _analyser.polarity_scores(text)
    return round(scores["compound"], 4)


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Scores a list of prepared article dicts.
    Adds a vader_score field to each article.
    Uses cleaned_text if available, otherwise full_text.
    """
    scored = []
    for article in articles:
        text  = article.get("cleaned_text") or article.get("full_text", "")
        score = score_text(text)
        scored.append({**article, "vader_score": score})

    logger.info(
        f"VADER scored {len(scored)} articles. "
        f"Mean score: {sum(a['vader_score'] for a in scored) / max(len(scored), 1):.4f}"
    )
    return scored
