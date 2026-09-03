"""
nlp/finbert_scorer.py

FinBERT-based sentiment scoring — batched, GPU-accelerated.

Model: ProsusAI/finbert
Labels: Positive, Negative, neutral
Output: score in [-1, 1]

Batching + GPU changes this from ~1-3s/article (CPU, one-at-a-time) to
a fraction of a second for the whole batch on a 3090.
"""

from __future__ import annotations

from typing import Optional

try:
    from sentiment_engine.utils.config import FINBERT_MODEL
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.config import FINBERT_MODEL
    from utils.logger import get_logger

logger = get_logger("finbert_scorer")

# Lazy-loaded pipeline — only initialised once per process, then reused
_pipeline = None

# Tune based on VRAM headroom. A 3090 (24GB) can comfortably handle much
# larger batches than this for a base-sized BERT model — 64 is conservative
# and leaves room for the rest of your stack (torch, other models, etc).
BATCH_SIZE = 16


def _get_pipeline():
    """
    Loads the FinBERT pipeline on first call, onto GPU if available.
    Cached at module level so this cost is paid ONCE per process,
    not once per pipeline run — critical if you run this as a
    long-lived service instead of a fresh CLI process each cycle.
    """
    global _pipeline
    if _pipeline is None:
        try:
            logger.info(
                "Initializing PyTorch and Transformers. If this is the first run, "
                "it will download the FinBERT model (~440MB) which may take a few minutes..."
            )
            import torch
            from transformers import pipeline

            device = 0 if torch.cuda.is_available() else -1
            if device == 0:
                logger.info(f"CUDA available — loading FinBERT on GPU ({torch.cuda.get_device_name(0)})")
            else:
                logger.warning("CUDA not available — falling back to CPU for FinBERT")

            logger.info(f"Loading FinBERT model: {FINBERT_MODEL}")
            _pipeline = pipeline(
                "sentiment-analysis",
                model=FINBERT_MODEL,
                truncation=True,
                max_length=512,
                device=device,
            )
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}. Scores will default to 0.0")
            _pipeline = None
    return _pipeline


def warmup_pipeline() -> None:
    """
    Explicitly pre-load the FinBERT model and PyTorch into memory.

    Call this once at process startup so the first scoring call bears zero
    model-load latency.  Safe to call multiple times — subsequent calls are
    instant because the pipeline is cached at module level.
    """
    _get_pipeline()


def _label_to_signed_score(label: str, conf: float) -> float:
    """Converts FinBERT's {label, score} into a signed [-1, 1] float."""
    label = label.lower()
    if label == "positive":
        return round(conf, 4)
    elif label == "negative":
        return round(-conf, 4)
    return 0.0


def score_text(text: str) -> float:
    """
    Scores a SINGLE piece of text with FinBERT.

    Kept for backwards compatibility / ad-hoc use, but the pipeline
    (score_articles) should always be preferred for batches — this
    path pays full per-call overhead with no batching benefit.
    """
    if not text or not text.strip():
        return 0.0

    pipe = _get_pipeline()
    if pipe is None:
        return 0.0

    try:
        result = pipe(text)[0]
        return _label_to_signed_score(result["label"], result["score"])
    except Exception as e:
        logger.error(f"FinBERT scoring error: {e}")
        return 0.0


def score_articles(articles: list[dict]) -> list[dict]:
    if not articles:
        return []

    pipe = _get_pipeline()
    if pipe is None:
        logger.warning("FinBERT unavailable. Setting all finbert_scores to 0.0")
        return [{**a, "finbert_score": 0.0} for a in articles]

    texts = [
        a.get("finbert_text") or a.get("cleaned_text") or a.get("full_text", "")
        for a in articles
    ]
    safe_texts = [t if t and t.strip() else "neutral" for t in texts]

    try:
        results = pipe(safe_texts, batch_size=BATCH_SIZE, truncation=True, max_length=512)
    except Exception as e:
        # Covers CUDA OOM specifically — common on 4GB cards under load.
        # Fall back to a smaller batch size once before giving up.
        if "out of memory" in str(e).lower():
            logger.warning(f"CUDA OOM at batch_size={BATCH_SIZE}, retrying at batch_size=4")
            try:
                import torch
                torch.cuda.empty_cache()
                results = pipe(safe_texts, batch_size=4, truncation=True, max_length=512)
            except Exception as e2:
                logger.error(f"FinBERT retry also failed: {e2}. Falling back to 0.0 for all.")
                return [{**a, "finbert_score": 0.0} for a in articles]
        else:
            logger.error(f"FinBERT batch scoring failed: {e}. Falling back to 0.0 for all.")
            return [{**a, "finbert_score": 0.0} for a in articles]

    scored = []
    for article, result in zip(articles, results):
        score = _label_to_signed_score(result["label"], result["score"])
        scored.append({**article, "finbert_score": score})

    logger.info(
        f"FinBERT scored {len(scored)} articles in batches of {BATCH_SIZE}. "
        f"Mean score: {sum(a['finbert_score'] for a in scored) / max(len(scored), 1):.4f}"
    )
    return scored