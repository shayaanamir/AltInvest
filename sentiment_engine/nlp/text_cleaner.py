"""
nlp/text_cleaner.py

Cleans raw article text before it goes into VADER or FinBERT.
Handles HTML remnants, special characters, boilerplate phrases,
excessive whitespace, and truncation for model token limits.
"""

from __future__ import annotations

import re
import unicodedata

try:
    from sentiment_engine.utils.config import FINBERT_MAX_TOKENS
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.config import FINBERT_MAX_TOKENS
    from utils.logger import get_logger

logger = get_logger("text_cleaner")

# Boilerplate phrases that appear in many crypto news articles
# and add no sentiment signal — strip them before scoring.
BOILERPLATE_PATTERNS = [
    r"read more.*",
    r"click here.*",
    r"subscribe.*newsletter.*",
    r"follow us on.*",
    r"sponsored content.*",
    r"advertisement.*",
    r"this article.*does not constitute.*",
    r"not financial advice.*",
    r"disclaimer.*",
    r"the views expressed.*",
    r"past performance.*",
    r"\bshare this article\b.*",
    r"©.*all rights reserved.*",
]

_BOILERPLATE_RE = re.compile(
    "|".join(BOILERPLATE_PATTERNS),
    flags=re.IGNORECASE | re.DOTALL,
)


def clean_text(raw: str) -> str:
    """
    Full cleaning pipeline for a single piece of text.

    Steps:
    1. Normalise unicode
    2. Strip HTML tags
    3. Remove URLs
    4. Remove boilerplate
    5. Remove special characters (keep punctuation)
    6. Collapse whitespace
    7. Strip leading/trailing whitespace

    Returns cleaned string.
    """
    if not raw or not isinstance(raw, str):
        return ""

    text = raw

    # 1. Unicode normalisation
    text = unicodedata.normalize("NFKD", text)

    # 2. Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # 3. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # 4. Remove boilerplate
    text = _BOILERPLATE_RE.sub(" ", text)

    # 5. Remove special characters — keep letters, digits, spaces, basic punctuation
    text = re.sub(r"[^\w\s.,!?$%\-']", " ", text)

    # 6. Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # 7. Strip
    text = text.strip()

    return text


def truncate_for_finbert(text: str, max_chars: int = 1800) -> str:
    """
    FinBERT has a 512-token limit. Rather than tokenising here,
    we approximate: ~3.5 chars per token → 512 tokens ≈ 1800 chars.
    Truncates at the last sentence boundary before the limit.
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]

    # Try to break at the last sentence boundary
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )

    if last_period > max_chars * 0.7:
        return truncated[:last_period + 1].strip()

    return truncated.strip()


def prepare_article(article: dict) -> dict:
    """
    Cleans and prepares an article dict for NLP scoring.
    Adds cleaned_text and finbert_text fields.
    Does NOT modify the original dict.
    """
    raw_title   = article.get("title", "")
    raw_summary = article.get("summary", "")

    # Combine title and summary — title carries strong signal, weight it by repeating
    combined = f"{raw_title}. {raw_title}. {raw_summary}"

    cleaned = clean_text(combined)
    finbert_ready = truncate_for_finbert(cleaned)

    return {
        **article,
        "cleaned_text":  cleaned,
        "finbert_text":  finbert_ready,
        "text_length":   len(cleaned),
    }


def prepare_articles(articles: list[dict]) -> list[dict]:
    """
    Applies prepare_article to a list, filtering out articles
    with too little text to be meaningful (< 20 chars after cleaning).
    """
    prepared = []
    for article in articles:
        p = prepare_article(article)
        if p["text_length"] >= 20:
            prepared.append(p)
        else:
            logger.debug(f"Skipping article with insufficient text: {article.get('title', '')[:50]}")

    logger.info(f"Prepared {len(prepared)}/{len(articles)} articles for NLP")
    return prepared
