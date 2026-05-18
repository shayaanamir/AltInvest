"""
routes/sentiment.py

Wires FastAPI sentiment endpoints to the real sentiment engine.
All sentiment-engine imports are LAZY (inside functions) so the backend
starts up cleanly even if the engine's dependencies aren't installed yet.

Endpoints:
    GET  /sentiment                  -> all assets (runs pipeline on cold start)
    GET  /sentiment/{asset}          -> single asset (cached or fresh)
    GET  /sentiment/{asset}/history  -> historical scores for charting
    POST /sentiment/{asset}/refresh  -> force re-run, bypass cache
"""

import path_setup  # noqa: F401  -- must be first

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Sentiment"])

_CACHE_TTL_MINUTES = 60

# ── Scope limiter ─────────────────────────────────────────────────────────────
# Only these asset IDs are processed by the sentiment engine for now.
# Expand this list when you're ready to add more assets.
_ACTIVE_ASSETS = ["btc"]


def _engine():
    """
    Lazy-import the sentiment engine.
    Returns (run_pipeline, get_latest_sentiment, get_sentiment_history,
              get_all_latest, save_sentiment, ASSETS).
    Raises ImportError with a clear message if deps are missing.
    """
    try:
        from aggregator.sentiment_aggregator import run_pipeline
        from storage.mongo_handler import (
            get_latest_sentiment,
            get_sentiment_history,
            get_all_latest,
            save_sentiment,
        )
        from utils.config import ASSETS
        return run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS
    except ImportError as exc:
        raise RuntimeError(
            f"Sentiment engine not importable: {exc}. "
            "Make sure you installed sentiment_engine/requirements.txt "
            "in the same Python environment as the backend."
        ) from exc


def _is_stale(result: dict) -> bool:
    ts_str = result.get("last_updated")
    if not ts_str:
        return True
    try:
        ts = datetime.fromisoformat(ts_str)
        return (datetime.now(tz=timezone.utc) - ts) > timedelta(minutes=_CACHE_TTL_MINUTES)
    except Exception:
        return True


def _neutral(asset_id: str, error: str = "") -> dict:
    return {
        "asset_id":               asset_id,
        "sentiment_score":        0.5,
        "confidence":             0.0,
        "confidence_label":       "low",
        "signal_strength":        "weak",
        "trend":                  "stable",
        "last_updated":           datetime.now(tz=timezone.utc).isoformat(),
        "article_count":          0,
        "source_count":           0,
        "source_breakdown":       {"news_nlp": 0.5, "market_signals": 0.5},
        "sentiment_distribution": {"Positive": 0, "Negative": 0, "neutral": 0},
        "top_headlines":          [],
        "market_signals":         {},
        "articles_by_source":     {},
        **({"error": error} if error else {}),
    }


# ── GET /sentiment ─────────────────────────────────────────────────────────────

@router.get("/sentiment")
def get_all_sentiment():
    """
    Returns latest sentiment for every configured asset.
    On cold start (empty MongoDB), runs the pipeline for each asset.
    """
    run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS = _engine()

    # Fetch cached results — only for the active assets
    all_cached = get_all_latest()
    results = [r for r in all_cached if r.get("asset_id") in _ACTIVE_ASSETS]

    if not results:
        # Cold start: run the pipeline only for active assets
        results = []
        for asset_id in _ACTIVE_ASSETS:
            try:
                history = get_sentiment_history(asset_id, days=1)
                result  = run_pipeline(asset_id, history=history)
                save_sentiment(result)
                results.append(result)
            except Exception as exc:
                results.append(_neutral(asset_id, str(exc)))

    return JSONResponse(content=results)


# ── GET /sentiment/{asset} ─────────────────────────────────────────────────────

@router.get("/sentiment/{asset}")
def get_sentiment(asset: str):
    """
    Returns latest sentiment for a single asset.
    Serves from MongoDB cache if fresh; otherwise re-runs the pipeline.
    """
    run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS = _engine()

    asset_id = asset.lower()
    if asset_id not in _ACTIVE_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not active. Active assets: {_ACTIVE_ASSETS}",
        )

    cached = get_latest_sentiment(asset_id)
    if cached and not _is_stale(cached):
        return JSONResponse(content=cached)

    history = get_sentiment_history(asset_id, days=1)
    result  = run_pipeline(asset_id, history=history)
    save_sentiment(result)
    return JSONResponse(content=result)


# ── GET /sentiment/{asset}/history ────────────────────────────────────────────

@router.get("/sentiment/{asset}/history")
def get_sentiment_history_route(
    asset: str,
    days: int = Query(default=7, ge=1, le=30, description="Days to look back"),
):
    """Returns historical sentiment scores for chart rendering."""
    run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS = _engine()

    asset_id = asset.lower()
    if asset_id not in _ACTIVE_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not active. Active assets: {_ACTIVE_ASSETS}",
        )

    history = get_sentiment_history(asset_id, days=days)
    return JSONResponse(content={
        "asset_id": asset_id,
        "days":     days,
        "count":    len(history),
        "history":  history,
    })


# ── POST /sentiment/{asset}/refresh ───────────────────────────────────────────

@router.post("/sentiment/{asset}/refresh")
def refresh_sentiment(asset: str):
    """Forces a fresh pipeline run for the asset, bypassing the cache."""
    run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS = _engine()

    asset_id = asset.lower()
    if asset_id not in _ACTIVE_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not active. Active assets: {_ACTIVE_ASSETS}",
        )

    history = get_sentiment_history(asset_id, days=1)
    result  = run_pipeline(asset_id, history=history)
    save_sentiment(result)
    return JSONResponse(content={"status": "refreshed", "result": result})
