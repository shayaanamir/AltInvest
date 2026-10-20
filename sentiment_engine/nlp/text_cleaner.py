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
#
# Every pattern is confined to ONE sentence/line: [^.!?\n] never crosses a sentence end or
# a newline, and there is no DOTALL. An unbounded ".*" would delete everything after the
# first "read more" or "disclaimer", i.e. most of the article (or the title itself).

_TAIL = r"[^.!?\n]*[.!?]?"                 # rest of the current sentence, plus its end mark
_SENTENCE = r"[^.!?\n]*" + r"{}" + _TAIL   # the whole sentence around a phrase

# Calls to action: remove the phrase and what trails it in the same sentence
# ("Read more: Bitcoin hits 100k"), keeping whatever came before it.
_TRAILING_PHRASES = [
    r"\bread more\b",
    r"\bclick here\b",
    r"\bfollow us on\b",
    r"\bsponsored content\b",
    r"\bshare this article\b",
    r"\bsubscribe\b[^.!?\n]*?\bnewsletter\b",
    r"©",
]

# Disclaimers: the whole sentence is boilerplate, so remove all of it.
_WHOLE_SENTENCE_PHRASES = [
    r"\bdoes not constitute\b",
    r"\bnot financial advice\b",
    r"\bdisclaimer\b",
    r"\bthe views expressed\b",
    r"\bpast performance\b",
    r"\ball rights reserved\b",
]

BOILERPLATE_PATTERNS = (
    [p + _TAIL for p in _TRAILING_PHRASES]
    + [_SENTENCE.format(p) for p in _WHOLE_SENTENCE_PHRASES]
    + [r"\badvertisement\b"]               # a bare label; nothing after it belongs to it
)

_BOILERPLATE_RE = re.compile("|".join(BOILERPLATE_PATTERNS), flags=re.IGNORECASE)


def clean_text(raw: str, strip_boilerplate: bool = True) -> str:
    """
    Full cleaning pipeline for a single piece of text.

    Steps:
    1. Normalise unicode
    2. Strip HTML tags
    3. Remove URLs
    4. Remove boilerplate (skipped when strip_boilerplate is False — headlines are
       content, not feed furniture, so they shouldn't lose a sentence to it)
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
    if strip_boilerplate:
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

    # Combine title and summary — title carries strong signal, weight it by repeating.
    # Boilerplate is stripped from the summary only; the headline is kept as written.
    title   = clean_text(raw_title, strip_boilerplate=False)
    summary = clean_text(raw_summary)
    cleaned = clean_text(f"{title}. {title}. {summary}", strip_boilerplate=False)
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
