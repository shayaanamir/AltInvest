"""
nlp/finbert_scorer.py

FinBERT-based sentiment scoring.
FinBERT is a BERT model fine-tuned on financial text.
It understands phrases like "missed earnings", "bullish reversal", "liquidity crunch"
far better than VADER.

Model: ProsusAI/finbert
Labels: positive, negative, neutral
Output: score in [-1, 1]

NOTE: First run downloads the model (~400MB). Subsequent runs use local cache.
GPU is used automatically if available; falls back to CPU.
"""

from __future__ import annotations

from typing import Optional

from utils.config import FINBERT_MODEL
from utils.logger import get_logger

logger = get_logger("finbert_scorer")

# Lazy-loaded pipeline — only initialised when first needed
_pipeline = None


def _get_pipeline():
    """
    Loads the FinBERT pipeline on first call.
    Lazy-loading avoids startup overhead when running tests or using mock data.
    """
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline
            logger.info(f"Loading FinBERT model: {FINBERT_MODEL}")
            _pipeline = pipeline(
                "sentiment-analysis",
                model=FINBERT_MODEL,
                truncation=True,
                max_length=512,
            )
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}. Scores will default to 0.0")
            _pipeline = None
    return _pipeline


def score_text(text: str) -> float:
    """
    Scores a single piece of text with FinBERT.

    FinBERT returns:
        { "label": "positive"|"negative"|"neutral", "score": 0.0–1.0 }

    We convert this to [-1, 1]:
        positive → +score
        negative → -score
        neutral  → 0.0

    Returns:
        float in [-1.0, 1.0]
    """
    if not text or not text.strip():
        return 0.0

    pipe = _get_pipeline()
    if pipe is None:
        return 0.0

    try:
        result = pipe(text)[0]
        label  = result["label"].lower()
        conf   = result["score"]

        if label == "positive":
            return round(conf, 4)
        elif label == "negative":
            return round(-conf, 4)
        else:
            return 0.0

    except Exception as e:
        logger.error(f"FinBERT scoring error: {e}")
        return 0.0


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Scores a list of prepared article dicts with FinBERT.
    Adds a finbert_score field to each article.
    Uses finbert_text if available (truncated), otherwise cleaned_text.
    """
    pipe = _get_pipeline()
    if pipe is None:
        logger.warning("FinBERT unavailable. Setting all finbert_scores to 0.0")
        return [{**a, "finbert_score": 0.0} for a in articles]

    scored = []
    for article in articles:
        text  = article.get("finbert_text") or article.get("cleaned_text") or article.get("full_text", "")
        score = score_text(text)
        scored.append({**article, "finbert_score": score})

    logger.info(
        f"FinBERT scored {len(scored)} articles. "
        f"Mean score: {sum(a['finbert_score'] for a in scored) / max(len(scored), 1):.4f}"
    )
    return scored
