"""
nlp/ensemble_scorer.py

Combines VADER and FinBERT scores into a single per-article NLP score.
Also applies source trust weighting so that high-trust sources (e.g. CoinDesk, The Block)
influence the final score more than low-trust ones.

Blend formula per article:
    nlp_score = (vader_weight * vader_score) + (finbert_weight * finbert_score)

Final ensemble score across all articles is a trust-weighted average.
"""

from __future__ import annotations

try:
    from sentiment_engine.utils.config import VADER_WEIGHT, FINBERT_WEIGHT
    from sentiment_engine.utils.logger import get_logger
    from sentiment_engine.nlp.vader_scorer import score_articles as vader_score_articles
    from sentiment_engine.nlp.finbert_scorer import score_articles as finbert_score_articles
    from sentiment_engine.nlp.text_cleaner import prepare_articles
except ImportError:
    from utils.config import VADER_WEIGHT, FINBERT_WEIGHT
    from utils.logger import get_logger
    from nlp.vader_scorer import score_articles as vader_score_articles
    from nlp.finbert_scorer import score_articles as finbert_score_articles
    from nlp.text_cleaner import prepare_articles

logger = get_logger("ensemble_scorer")


def _blend_scores(vader: float, finbert: float) -> float:
    """
    Blends VADER and FinBERT scores.
    Both are in [-1, 1]. Result is in [-1, 1].
    """
    return round(
        (VADER_WEIGHT * vader) + (FINBERT_WEIGHT * finbert),
        4
    )


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Full NLP scoring pipeline for a list of raw article dicts.

    Steps:
        1. Clean and prepare text
        2. Score with VADER
        3. Score with FinBERT
        4. Blend scores
        5. Apply trust weighting per article

    Returns list of articles with added fields:
        cleaned_text, finbert_text, vader_score, finbert_score,
        nlp_score (blended), trust_weighted_score
    """
    if not articles:
        logger.warning("No articles to score.")
        return []

    # Step 1 — clean
    prepared = prepare_articles(articles)

    # Step 2 — VADER
    vader_scored = vader_score_articles(prepared)

    # Step 3 — FinBERT
    ensemble_scored = finbert_score_articles(vader_scored)

    # Step 4 + 5 — blend and apply trust weight
    result = []
    for article in ensemble_scored:
        vader_s   = article.get("vader_score", 0.0)
        finbert_s = article.get("finbert_score", 0.0)
        trust     = article.get("trust_weight", 1.0)

        blended = _blend_scores(vader_s, finbert_s)
        trust_weighted = round(blended * trust, 4)

        result.append({
            **article,
            "nlp_score":            blended,
            "trust_weighted_score": trust_weighted,
        })

    # Log distribution
    scores = [a["nlp_score"] for a in result]
    if scores:
        logger.info(
            f"Ensemble scored {len(result)} articles | "
            f"min={min(scores):.3f} max={max(scores):.3f} "
            f"mean={sum(scores)/len(scores):.3f}"
        )

    return result
