"""
storage/mongo_handler.py

Handles all MongoDB read/write operations for the sentiment engine.

Collections used:
    sentiment          → latest sentiment score per asset (upsert)
    sentiment_history  → time-series of scores (append-only)
    raw_articles       → raw article dumps for debugging / retraining

This module is the ONLY place that touches MongoDB.
All other modules are pure functions.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

# pyrefly: ignore [missing-import]
from pymongo import MongoClient, DESCENDING
# pyrefly: ignore [missing-import]
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from utils.config import (
    MONGO_URI,
    MONGO_DB,
    COLLECTION_SENTIMENT,
    COLLECTION_SENTIMENT_HISTORY,
    COLLECTION_RAW_ARTICLES,
)
from utils.logger import get_logger

logger = get_logger("mongo_handler")

# Module-level client — shared across calls
_client: Optional[MongoClient] = None
_db = None


def _get_db():
    """Returns the MongoDB database, connecting if necessary."""
    global _client, _db
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            _client.admin.command("ping")  # Test connection
            _db = _client[MONGO_DB]
            logger.info(f"Connected to MongoDB at {MONGO_URI} | db={MONGO_DB}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            _client = None
            _db = None
    return _db


# ── Write operations ───────────────────────────────────────────────────────────

def save_sentiment(result: dict) -> bool:
    """
    Upserts the latest sentiment result for an asset.
    Also appends to the history collection.

    Args:
        result: The output dict from sentiment_aggregator.run_pipeline()

    Returns:
        True if successful, False on error.
    """
    db = _get_db()
    if db is None:
        logger.warning("MongoDB unavailable — skipping save_sentiment")
        return False

    asset_id  = result["asset_id"]
    timestamp = result.get("last_updated", datetime.now(tz=timezone.utc).isoformat())

    try:
        # Upsert latest
        db[COLLECTION_SENTIMENT].update_one(
            {"asset_id": asset_id},
            {"$set": {**result, "updated_at": timestamp}},
            upsert=True,
        )

        # Append to history
        db[COLLECTION_SENTIMENT_HISTORY].insert_one({
            **result,
            "timestamp": timestamp,
        })

        logger.info(f"Saved sentiment for {asset_id.upper()} | score={result['sentiment_score']}")
        return True

    except Exception as e:
        logger.error(f"Failed to save sentiment for {asset_id}: {e}")
        return False


def save_raw_articles(articles: list[dict], asset_id: str) -> bool:
    """
    Saves raw (pre-NLP) articles to MongoDB for debugging / model retraining.
    Skips duplicates based on (title, source, published).
    """
    db = _get_db()
    if db is None or not articles:
        return False

    try:
        inserted = 0
        for article in articles:
            key = {
                "title":    article.get("title", ""),
                "source":   article.get("source", ""),
                "published": article.get("published", ""),
            }
            db[COLLECTION_RAW_ARTICLES].update_one(
                key,
                {"$setOnInsert": {**article, "asset_id": asset_id}},
                upsert=True,
            )
            inserted += 1

        logger.info(f"Saved {inserted} raw articles for {asset_id.upper()}")
        return True

    except Exception as e:
        logger.error(f"Failed to save raw articles for {asset_id}: {e}")
        return False


# ── Read operations ────────────────────────────────────────────────────────────

def get_latest_sentiment(asset_id: str) -> Optional[dict]:
    """
    Returns the most recent sentiment result for an asset.
    Returns None if not found or DB unavailable.
    """
    db = _get_db()
    if db is None:
        return None

    try:
        result = db[COLLECTION_SENTIMENT].find_one(
            {"asset_id": asset_id},
            {"_id": 0}
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get latest sentiment for {asset_id}: {e}")
        return None


def get_sentiment_history(asset_id: str, days: int = 7) -> list[dict]:
    """
    Returns the last N days of sentiment history for an asset.
    Used by the trend detection and the /history API endpoint.

    Args:
        asset_id: e.g. "btc"
        days:     Number of days to look back (default 7)

    Returns:
        List of sentiment records, sorted oldest-first.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        cursor = db[COLLECTION_SENTIMENT_HISTORY].find(
            {
                "asset_id":  asset_id,
                "timestamp": {"$gte": cutoff.isoformat()},
            },
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(days * 24)  # hourly resolution max

        return list(cursor)

    except Exception as e:
        logger.error(f"Failed to get sentiment history for {asset_id}: {e}")
        return []


def get_all_latest() -> list[dict]:
    """
    Returns the latest sentiment result for all assets.
    Used by the /sentiment endpoint (no asset filter).
    """
    db = _get_db()
    if db is None:
        return []

    try:
        return list(db[COLLECTION_SENTIMENT].find({}, {"_id": 0}))
    except Exception as e:
        logger.error(f"Failed to get all latest sentiment: {e}")
        return []
