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
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError
from fastapi.responses import JSONResponse

from models.schemas import SentimentResponse

router = APIRouter(tags=["Sentiment"])

_CACHE_TTL_MINUTES = 20

# ── Scope limiter ─────────────────────────────────────────────────────────────
# Only these asset IDs are processed by the sentiment engine for now.
# Expand this list when you're ready to add more assets.
_ACTIVE_ASSETS = [
    "btc", "eth", "sol", "bnb", "xrp",
    "ada", "avax", "doge", "dot", "link",
    "matic", "uni", "ltc", "atom", "near",
]


def _engine():
    """
    Lazy-import the sentiment engine.
    Returns (run_pipeline, get_latest_sentiment, get_sentiment_history,
              get_all_latest, save_sentiment, ASSETS).
    Raises ImportError with a clear message if deps are missing.
    """
    try:
        try:
            from sentiment_engine.aggregator.sentiment_aggregator import run_pipeline
            from sentiment_engine.storage.mongo_handler import (
                get_latest_sentiment,
                get_sentiment_history,
                get_all_latest,
                save_sentiment,
            )
            from sentiment_engine.utils.config import ASSETS
        except ImportError:
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


def _is_no_articles(result: dict) -> bool:
    """True for the neutral placeholder run_pipeline returns when no articles were found."""
    return (result.get("data_quality") or {}).get("reason") == "no_articles"


def _neutral(asset_id: str, error: str = "") -> dict:
    return {
        "asset_id":               asset_id,
        "sentiment_score":        0.0,
        "confidence":             0.0,
        "confidence_label":       "low",
        "signal_strength":        "weak",
        "trend":                  "stable",
        "last_updated":           datetime.now(tz=timezone.utc).isoformat(),
        "article_count":          0,
        "source_count":           0,
        "source_breakdown":       {"news_nlp": 0.5, "market_signals": 0.5},
        "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
        "top_headlines":          [],
        "market_signals":         {},
        "articles_by_source":     {},
        **({"error": error} if error else {}),
    }


def _map_sentiment(result: dict) -> dict:
    """
    Maps the raw output of the sentiment engine to conform to the
    SentimentResponse Pydantic schema (e.g. mapping asset_id to asset,
    article_count to post_count, last_updated to timestamp).
    """
    if not result:
        return {}

    # Normalise optional blocks so a partial engine result can't fail response validation.
    market_signals = result.get("market_signals") or None          # {} -> None
    headlines = [h for h in (result.get("top_headlines") or []) if isinstance(h, dict) and h.get("title")]

    dist = result.get("sentiment_distribution") or {}
    mapped_dist = {
        "positive": dist.get("positive") or dist.get("Positive") or 0,
        "negative": dist.get("negative") or dist.get("Negative") or 0,
        "neutral": dist.get("neutral") or dist.get("Neutral") or 0,
    }

    return {
        "asset": (result.get("asset_id") or result.get("asset") or "").upper(),
        "sentiment_score": result.get("sentiment_score") or 0.0,
        # The engine states which models scored the articles; don't claim FinBERT for records that don't say.
        "source": result.get("source") or "Sentiment engine",
        "post_count": result.get("article_count") or result.get("post_count") or 0,
        "timestamp": result.get("last_updated") or result.get("timestamp") or "",
        "confidence": result.get("confidence"),
        "confidence_label": result.get("confidence_label"),
        "signal_strength": result.get("signal_strength"),
        "trend": result.get("trend"),
        "source_count": result.get("source_count"),
        "source_breakdown": result.get("source_breakdown"),
        "sentiment_distribution": mapped_dist,
        "top_headlines": headlines,
        "market_signals": market_signals,
        "articles_by_source": result.get("articles_by_source"),
        "data_quality": result.get("data_quality") or None,
        "error": result.get("error"),
        "note": result.get("note") or result.get("error"),
    }


# ── GET /sentiment ─────────────────────────────────────────────────────────────

@router.get("/sentiment", response_model=List[SentimentResponse])
def get_all_sentiment():
    """
    Returns latest sentiment for every configured asset.
    Serves cached results from MongoDB where available; runs the pipeline
    only for assets that are missing from the cache (not already covered).
    This means adding new assets to _ACTIVE_ASSETS never requires a full
    cache flush — only the new ones are run on the next request.
    """
    run_pipeline, get_latest_sentiment, get_sentiment_history, get_all_latest, save_sentiment, ASSETS = _engine()

    # Build a map of asset_id -> cached result for active assets only
    all_cached = get_all_latest()
    cached_map: dict[str, dict] = {
        r.get("asset_id"): r
        for r in all_cached
        if r.get("asset_id") in _ACTIVE_ASSETS
    }

    # Which active assets have no cached entry yet?
    missing = [a for a in _ACTIVE_ASSETS if a not in cached_map]

    if missing:
        def _run_one(asset_id: str) -> tuple[str, dict]:
            try:
                history = get_sentiment_history(asset_id, days=1)
                raw = run_pipeline(asset_id, history=history)
                result: dict = raw[0] if isinstance(raw, tuple) else raw
                save_sentiment(result)
                return asset_id, result
            except Exception as exc:
                import logging
                logging.getLogger("sentiment_api").error("pipeline failed for %s: %s", asset_id, exc)
                # The exception text stays in the server log; clients get a fixed message.
                return asset_id, _neutral(asset_id, "Sentiment could not be computed for this asset right now.")

        with ThreadPoolExecutor(max_workers=len(missing)) as executor:
            future_to_asset = {
                executor.submit(_run_one, asset_id): asset_id
                for asset_id in missing
            }
            for future in as_completed(future_to_asset):
                aid, result = future.result()
                cached_map[aid] = result

    # Return in _ACTIVE_ASSETS order for a stable response shape. Each record is checked on its
    # own: FastAPI validates the whole list after we return, so one unreadable record would
    # otherwise turn the entire response into a 500 for every asset.
    mapped = []
    for asset_id in _ACTIVE_ASSETS:
        record = cached_map.get(asset_id)
        if record is None:
            continue
        try:
            item = _map_sentiment(record)
            SentimentResponse.model_validate(item)
        except (ValidationError, AttributeError, TypeError, ValueError) as exc:
            logging.getLogger("sentiment_api").error("unreadable sentiment record for %s: %s", asset_id, exc)
            item = _map_sentiment(_neutral(asset_id, "Stored sentiment for this asset could not be read."))
        mapped.append(item)
    return mapped


# ── GET /sentiment/themes ──────────────────────────────────────────────────────
# Declared before /sentiment/{asset} so "themes" isn't read as an asset id.

@router.get("/sentiment/themes")
def get_themes():
    """Recurring themes in the coverage, from the `sentiment_themes` collection."""
    from utils.http_errors import db_unavailable
    try:
        from db.queries import get_sentiment_themes
        docs = get_sentiment_themes()
    except Exception as exc:
        raise db_unavailable(exc)
    return [
        {"label": d.get("label"), "direction": d.get("direction"), "category": d.get("category")}
        for d in docs
        if d.get("label")
    ]


# ── GET /sentiment/mood-trend ──────────────────────────────────────────────────

@router.get("/sentiment/mood-trend")
def get_mood_trend(days: int = Query(default=30, ge=1, le=90, description="Days to look back")):
    """
    Overall crypto mood over time: the average sentiment score (-1..1) of every covered asset,
    bucketed by hour for a day or two of history and by day beyond that.
    """
    _, _, get_sentiment_history, _, _, _ = _engine()

    fmt = "%Y-%m-%dT%H:00:00Z" if days <= 2 else "%Y-%m-%dT00:00:00Z"
    buckets: dict[str, list[float]] = {}
    for asset_id in _ACTIVE_ASSETS:
        for row in get_sentiment_history(asset_id, days=days):
            score = row.get("sentiment_score")
            ts = row.get("last_updated") or row.get("timestamp")
            if score is None or not ts or not (row.get("confidence") or 0) > 0:
                continue  # skip neutral placeholders written when no articles were found
            try:
                when = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                continue
            buckets.setdefault(when.strftime(fmt), []).append(float(score))

    return [
        {"date": key, "value": round(sum(vals) / len(vals), 4), "assets": len(vals)}
        for key, vals in sorted(buckets.items())
    ]


# ── GET /sentiment/{asset} ─────────────────────────────────────────────────────

@router.get("/sentiment/{asset}", response_model=SentimentResponse)
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
        return _map_sentiment(cached)

    history = get_sentiment_history(asset_id, days=1)
    raw     = run_pipeline(asset_id, history=history)
    result: dict = raw[0] if isinstance(raw, tuple) else raw
    save_sentiment(result)
    # No articles this run: the last good (if stale) score beats a neutral 0.0.
    if cached and _is_no_articles(result):
        return _map_sentiment(cached)
    return _map_sentiment(result)


# ── GET /sentiment/{asset}/history ────────────────────────────────────────────

@router.get("/sentiment/{asset}/history")
def get_sentiment_history_route(
    asset: str,
    days: int = Query(default=7, ge=1, le=90, description="Days to look back"),
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
    raw     = run_pipeline(asset_id, history=history)
    result: dict = raw[0] if isinstance(raw, tuple) else raw
    save_sentiment(result)
    if _is_no_articles(result):
        cached = get_latest_sentiment(asset_id)
        if cached and not _is_no_articles(cached):
            return JSONResponse(content={"status": "no_new_articles", "result": _map_sentiment(cached)})
    return JSONResponse(content={"status": "refreshed", "result": _map_sentiment(result)})


# ── Background scheduled refresh ───────────────────────────────────────────────

# Pipeline refresh interval — every 15 minutes, well inside the 20 min cache
# TTL, so a user hitting /sentiment always gets data that is fresh.
_REFRESH_INTERVAL_SECONDS = 15 * 60


def _refresh_all_assets() -> None:
    """
    Runs the full sentiment pipeline for every active asset and saves results
    to MongoDB.  Intended to be called from the background scheduler thread.
    """
    import logging
    log = logging.getLogger("sentiment_scheduler")
    log.info("[scheduler] Starting scheduled pipeline refresh for all assets")

    try:
        run_pipeline, _, get_sentiment_history, _, save_sentiment, _ = _engine()
    except RuntimeError as exc:
        log.error(f"[scheduler] Engine unavailable, skipping refresh: {exc}")
        return

    def _run_one(asset_id: str) -> None:
        try:
            history = get_sentiment_history(asset_id, days=1)
            raw = run_pipeline(asset_id, history=history)
            # run_pipeline returns dict | tuple — extract the dict
            result: dict = raw[0] if isinstance(raw, tuple) else raw
            save_sentiment(result)
            log.info(f"[scheduler] Refreshed {asset_id.upper()} successfully")
        except Exception as exc:
            log.error(f"[scheduler] Failed to refresh {asset_id}: {exc}")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(_ACTIVE_ASSETS)) as executor:
        futures = {executor.submit(_run_one, a): a for a in _ACTIVE_ASSETS}
        for f in as_completed(futures):
            pass  # errors already logged inside _run_one

    log.info("[scheduler] Scheduled refresh complete for all assets")


def _run_scheduler() -> None:
    """
    Infinite loop that calls _refresh_all_assets() every
    _REFRESH_INTERVAL_SECONDS.  Designed to run in a daemon thread so it
    stops cleanly when the process exits.
    """
    import time
    import logging
    log = logging.getLogger("sentiment_scheduler")

    # Initial delay: let the FinBERT warmup finish first before the first run
    log.info(f"[scheduler] First pipeline run in 90 seconds, then every "
             f"{_REFRESH_INTERVAL_SECONDS // 60} minutes")
    time.sleep(90)

    while True:
        _refresh_all_assets()
        time.sleep(_REFRESH_INTERVAL_SECONDS)
