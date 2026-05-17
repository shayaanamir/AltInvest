"""
api/sentiment_routes.py

FastAPI router for sentiment endpoints.
Person B mounts this into the main FastAPI app with:

    from sentiment_engine.api.sentiment_routes import router as sentiment_router
    app.include_router(sentiment_router, prefix="/sentiment")

Endpoints:
    GET /sentiment/{asset_id}
        Returns the latest sentiment result for an asset.
        If the result is stale (> 1 hour old), re-runs the pipeline.

    GET /sentiment/{asset_id}/history
        Returns historical sentiment scores for charting.
        Query param: ?days=7 (default)

    GET /sentiment
        Returns latest sentiment for all assets.

    POST /sentiment/{asset_id}/refresh
        Forces a pipeline re-run for an asset.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from aggregator.sentiment_aggregator import run_pipeline
from storage.mongo_handler import (
    get_latest_sentiment,
    get_sentiment_history,
    get_all_latest,
    save_sentiment,
)
from utils.config import ASSETS
from utils.logger import get_logger

logger = get_logger("sentiment_routes")

router = APIRouter(tags=["sentiment"])

# How old a cached result can be before we re-run the pipeline (in minutes)
CACHE_TTL_MINUTES = 60


def _is_stale(result: dict) -> bool:
    """Returns True if the cached result is older than CACHE_TTL_MINUTES."""
    last_updated = result.get("last_updated")
    if not last_updated:
        return True
    try:
        ts  = datetime.fromisoformat(last_updated)
        age = datetime.now(tz=timezone.utc) - ts
        return age > timedelta(minutes=CACHE_TTL_MINUTES)
    except Exception:
        return True


@router.get("/{asset_id}")
async def get_sentiment(asset_id: str):
    """
    Returns the latest sentiment for a given asset.
    Serves from cache if fresh, otherwise re-runs the pipeline.
    """
    asset_id = asset_id.lower()

    if asset_id not in ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown asset '{asset_id}'. Supported: {list(ASSETS.keys())}"
        )

    cached = get_latest_sentiment(asset_id)

    if cached and not _is_stale(cached):
        logger.info(f"Serving cached sentiment for {asset_id.upper()}")
        return JSONResponse(content=cached)

    logger.info(f"Cache miss or stale for {asset_id.upper()} — running pipeline")

    history = get_sentiment_history(asset_id, days=1)
    result  = run_pipeline(asset_id, history=history)
    save_sentiment(result)

    return JSONResponse(content=result)


@router.get("/{asset_id}/history")
async def get_history(
    asset_id: str,
    days: int = Query(default=7, ge=1, le=30, description="Number of days to look back"),
):
    """
    Returns historical sentiment scores for a given asset.
    Used by the frontend to render sentiment trend charts.
    """
    asset_id = asset_id.lower()

    if asset_id not in ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown asset '{asset_id}'. Supported: {list(ASSETS.keys())}"
        )

    history = get_sentiment_history(asset_id, days=days)

    return JSONResponse(content={
        "asset_id": asset_id,
        "days":     days,
        "count":    len(history),
        "history":  history,
    })


@router.get("")
async def get_all_sentiment():
    """
    Returns latest sentiment results for all configured assets.
    """
    results = get_all_latest()
    return JSONResponse(content={
        "assets": results,
        "count":  len(results),
    })


@router.post("/{asset_id}/refresh")
async def refresh_sentiment(asset_id: str):
    """
    Forces a pipeline re-run for the given asset, ignoring cache.
    Useful for Person B to call after new data is ingested.
    """
    asset_id = asset_id.lower()

    if asset_id not in ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown asset '{asset_id}'. Supported: {list(ASSETS.keys())}"
        )

    logger.info(f"Force refresh for {asset_id.upper()}")

    history = get_sentiment_history(asset_id, days=1)
    result  = run_pipeline(asset_id, history=history)
    save_sentiment(result)

    return JSONResponse(content={"status": "refreshed", "result": result})
