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

import time
from datetime import datetime, timezone, timedelta
from typing import Optional

# pyrefly: ignore [missing-import]
from pymongo import MongoClient, DESCENDING
# pyrefly: ignore [missing-import]
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

try:
    from sentiment_engine.utils.config import (
        MONGO_URI,
        MONGO_DB,
        COLLECTION_SENTIMENT,
        COLLECTION_SENTIMENT_HISTORY,
        COLLECTION_RAW_ARTICLES,
        TREND_LOOKBACK_HOURS,
        TREND_TOLERANCE_HOURS,
    )
    from sentiment_engine.utils.logger import get_logger
except ImportError:
    from utils.config import (
        MONGO_URI,
        MONGO_DB,
        COLLECTION_SENTIMENT,
        COLLECTION_SENTIMENT_HISTORY,
        COLLECTION_RAW_ARTICLES,
        TREND_LOOKBACK_HOURS,
        TREND_TOLERANCE_HOURS,
    )
    from utils.logger import get_logger

logger = get_logger("mongo_handler")

# Module-level client — shared across calls
_client: Optional[MongoClient] = None
_db = None

# ── Circuit breaker ────────────────────────────────────────────────────────
# If Mongo fails once, don't retry (and pay another 1s timeout) again for
# this cooldown window. Every failed connection attempt costs a full
# serverSelectionTimeoutMS.
_FAILURE_COOLDOWN_SECONDS = 30
_last_failure_time: float = 0.0


def _mongo_recently_failed() -> bool:
    return (time.monotonic() - _last_failure_time) < _FAILURE_COOLDOWN_SECONDS


def _get_db():
    """Returns the MongoDB database, connecting if necessary."""
    global _client, _db, _last_failure_time

    if _db is not None:
        return _db

    if _mongo_recently_failed():
        # Skip the attempt entirely — don't pay another timeout for a
        # connection we already know is down.
        return None

    try:
        # Reduced from 3000ms — local/dev Mongo either responds almost
        # instantly or isn't running at all; no need to wait 3s to find out.
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)
        _client.admin.command("ping")
        _db = _client[MONGO_DB]
        logger.info(f"Connected to MongoDB at {MONGO_URI} | db={MONGO_DB}")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed: {e}")
        _client = None
        _db = None
        _last_failure_time = time.monotonic()

    return _db


# ── Write operations ───────────────────────────────────────────────────────────

def is_no_articles_result(result: dict) -> bool:
    """True for the neutral placeholder run_pipeline returns when no articles were found."""
    return (result.get("data_quality") or {}).get("reason") == "no_articles"


def save_sentiment(result: dict) -> bool:
    """
    Upserts the latest sentiment result for an asset.
    Also appends to the history collection.

    A neutral "no articles" placeholder is not real data: it never goes into
    history, and it only fills the latest slot when the asset has no record
    yet — it must not overwrite the last good score.

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
        if is_no_articles_result(result):
            # Insert-only: a no-op if a record for this asset already exists.
            db[COLLECTION_SENTIMENT].update_one(
                {"asset_id": asset_id},
                {"$setOnInsert": {**result, "updated_at": timestamp}},
                upsert=True,
            )
            logger.info(f"No articles for {asset_id.upper()} — kept last good score, no history point written")
            return True

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


def get_mood_trend(asset_ids: list[str], days: int) -> list[dict]:
    """
    Average sentiment across assets over time, aggregated inside MongoDB.

    Each asset's readings are averaged within a time bucket (hourly for up to 2 days, daily
    beyond that), then the assets' averages are averaged, so an asset that happened to be
    refreshed more often doesn't count for more. Placeholder rows (confidence 0) are ignored.

    This can't reuse get_sentiment_history: that returns only the newest days*24 rows per
    asset, which at a 15-minute refresh is about the last week — far short of a 30 or 90 day
    window.

    Returns [{"date": ISO bucket start (UTC), "value": -1..1, "assets": n}] oldest first.
    """
    db = _get_db()
    if db is None:
        return []

    # Timestamps are stored as UTC ISO strings, so a prefix of one is the start of its bucket.
    hourly = days <= 2
    prefix_len = 13 if hourly else 10
    suffix = ":00:00Z" if hourly else "T00:00:00Z"

    try:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        pipeline = [
            {"$match": {
                "asset_id":        {"$in": list(asset_ids)},
                "timestamp":       {"$gte": cutoff.isoformat()},
                "confidence":      {"$gt": 0},
                "sentiment_score": {"$ne": None},
            }},
            {"$group": {
                "_id":   {"asset": "$asset_id", "bucket": {"$substrBytes": ["$timestamp", 0, prefix_len]}},
                "score": {"$avg": "$sentiment_score"},
            }},
            {"$group": {
                "_id":    "$_id.bucket",
                "value":  {"$avg": "$score"},
                "assets": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        return [
            {"date": row["_id"] + suffix, "value": round(row["value"], 4), "assets": row["assets"]}
            for row in db[COLLECTION_SENTIMENT_HISTORY].aggregate(pipeline)
        ]

    except Exception as e:
        logger.error(f"Failed to compute mood trend: {e}")
        return []


def get_trend_baseline(asset_id: str) -> list[dict]:
    """
    Returns the stored readings around TREND_LOOKBACK_HOURS ago (± TREND_TOLERANCE_HOURS),
    for trend detection to pick the closest from.

    get_sentiment_history can't serve this: it returns the newest rows first and is capped
    at days*24 of them, which at a 15-minute refresh is only the last few hours.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        target = datetime.now(tz=timezone.utc) - timedelta(hours=TREND_LOOKBACK_HOURS)
        tol    = timedelta(hours=TREND_TOLERANCE_HOURS)

        cursor = db[COLLECTION_SENTIMENT_HISTORY].find(
            {
                "asset_id":  asset_id,
                "timestamp": {"$gte": (target - tol).isoformat(), "$lte": (target + tol).isoformat()},
            },
            {"_id": 0, "timestamp": 1, "sentiment_score": 1, "confidence": 1, "data_quality": 1},
        ).limit(500)

        return list(cursor)

    except Exception as e:
        logger.error(f"Failed to get trend baseline for {asset_id}: {e}")
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
