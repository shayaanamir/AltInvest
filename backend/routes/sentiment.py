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
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from concurrent.futures import TimeoutError as FuturesTimeout

import logging
import threading
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError
from fastapi.responses import JSONResponse

from models.schemas import SentimentResponse

router = APIRouter(tags=["Sentiment"])

_CACHE_TTL_MINUTES = 20

# ── Coverage ──────────────────────────────────────────────────────────────────
# The assets this API serves sentiment for are exactly the ones the engine is configured
# for (ASSETS in sentiment_engine/utils/config.py): add an asset there and it is covered
# here. The engine is imported lazily elsewhere in this module so the backend can start
# without it; if it isn't installed, nothing is covered.

def _covered_assets() -> list:
    try:
        try:
            from sentiment_engine.utils.config import ASSETS
        except ImportError:
            from utils.config import ASSETS
        return list(ASSETS)
    except Exception:
        return []


_ACTIVE_ASSETS = _covered_assets()


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


def _is_stale(result: dict, max_age_minutes: float = _CACHE_TTL_MINUTES) -> bool:
    ts_str = result.get("last_updated")
    if not ts_str:
        return True
    try:
        ts = datetime.fromisoformat(ts_str)
        return (datetime.now(tz=timezone.utc) - ts) > timedelta(minutes=max_age_minutes)
    except Exception:
        return True


def _is_no_articles(result: dict) -> bool:
    """True for the neutral placeholder run_pipeline returns when no articles were found."""
    return (result.get("data_quality") or {}).get("reason") == "no_articles"


# ── Refreshing one asset ──────────────────────────────────────────────────────
# Every path that runs the pipeline (request, forced refresh, scheduler) goes through
# _refresh_asset, so two callers never run the same asset's pipeline at the same time.

_asset_locks = {a: threading.Lock() for a in _ACTIVE_ASSETS}
_last_attempt: dict[str, float] = {}

# After a refresh attempt, don't start another for the same asset this soon unless it's
# forced. Without it, an asset that keeps coming back empty or failing would re-run the
# whole pipeline on every request.
_MIN_RETRY_SECONDS = 120

# Requests wait at most this long for pipelines: under the frontend's 18s GET timeout, with
# room left to serialise the response. Requests hand their pipelines to a shared pool instead
# of running them inline, so a request giving up doesn't cancel the work.
_REQUEST_BUDGET_SECONDS = 12
_request_pool = ThreadPoolExecutor(max_workers=max(1, len(_ACTIVE_ASSETS)), thread_name_prefix="sentiment-request")

_UNAVAILABLE = "Sentiment could not be computed for this asset right now."
_PENDING = "Sentiment is still being computed for this asset. Try again shortly."

# ── In-process cache ─────────────────────────────────────────────────────────
# MongoDB is the shared cache, but when it is down nothing can be saved and every request
# would look like a cold start, re-running every pipeline. Each process therefore keeps the
# results it computed, and reads the newer of this and MongoDB.

_memory_cache: dict[str, dict] = {}


def _ts(record):
    try:
        ts = datetime.fromisoformat(record["last_updated"])
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _newer(a, b):
    if not a or not b:
        return a or b
    ta, tb = _ts(a), _ts(b)
    if ta is None or tb is None:
        return a if tb is None else b
    return a if ta >= tb else b


def _remember(result: dict) -> None:
    """Keeps a computed result in memory, but (like save_sentiment) never lets a no-articles
    placeholder replace a real reading."""
    previous = _memory_cache.get(result.get("asset_id"))
    if _is_no_articles(result) and previous and not _is_no_articles(previous):
        return
    _memory_cache[result["asset_id"]] = result


def _latest(asset_id: str):
    """Latest record for an asset: MongoDB or this process's memory, whichever is newer."""
    _, get_latest_sentiment, _, _, _, _ = _engine()
    return _newer(get_latest_sentiment(asset_id), _memory_cache.get(asset_id))


def _all_latest() -> dict:
    """Latest record per active asset, merging MongoDB with this process's memory."""
    _, _, _, get_all_latest, _, _ = _engine()
    merged: dict = {}
    for record in get_all_latest():
        if record.get("asset_id") in _ACTIVE_ASSETS:
            merged[record["asset_id"]] = record
    for asset_id, record in list(_memory_cache.items()):
        if asset_id in _ACTIVE_ASSETS:
            merged[asset_id] = _newer(merged.get(asset_id), record)
    return merged


def _refresh_asset(asset_id: str, force: bool = False) -> tuple[dict, str]:
    """
    Runs the pipeline for one asset, saves the result and returns (record to serve, outcome).

    outcome is "refreshed" (computed and saved), "not_saved" (computed and served, but
    MongoDB couldn't store it — only this process's memory has it), "no_new_articles"
    (nothing to read; the last good record is returned), "failed" (the pipeline raised, or a recent attempt did; the last record, or
    a neutral placeholder if there is none, is returned) or "cached" (someone else just
    refreshed it, or it was attempted too recently).

    force skips the freshness and retry checks (scheduler, POST /refresh) and lets a
    pipeline failure raise instead of falling back to the last record.
    """
    run_pipeline, _, _, _, save_sentiment, _ = _engine()

    with _asset_locks[asset_id]:
        cached = _latest(asset_id)
        if not force:
            if cached and not _is_stale(cached):
                return cached, "cached"        # another caller refreshed it while we waited
            if time.monotonic() - _last_attempt.get(asset_id, float("-inf")) < _MIN_RETRY_SECONDS:
                # Attempted moments ago and still nothing usable: don't run it all again.
                return (cached, "cached") if cached else (_neutral(asset_id, _UNAVAILABLE), "failed")
        _last_attempt[asset_id] = time.monotonic()

        try:
            raw = run_pipeline(asset_id)
        except Exception:
            if force or not cached:
                raise
            logging.getLogger("sentiment_api").exception("pipeline failed for %s; serving the last record", asset_id)
            return cached, "failed"

        result: dict = raw[0] if isinstance(raw, tuple) else raw
        saved = save_sentiment(result)      # False if MongoDB is down or the write failed
        _remember(result)
        if _is_no_articles(result):
            return (cached if cached and not _is_no_articles(cached) else result), "no_new_articles"
        if not saved:
            logging.getLogger("sentiment_api").warning(
                "computed sentiment for %s but could not save it; serving it from memory only", asset_id
            )
            return result, "not_saved"
        return result, "refreshed"


# ── Readings other features can rely on ──────────────────────────────────────
# Other parts of the backend (AAI, dashboard, market lists) consume sentiment. They should
# only ever see a real, recent reading for a covered asset: not a no-articles placeholder,
# not an error row, not a record from days ago, not an asset outside the active scope.

# How old a reading may be before it's left out of aggregates and lists. Looser than the
# cache TTL (which decides when to recompute) so one slow scheduler cycle doesn't blank them.
_DISPLAY_MAX_AGE_MINUTES = 60


def is_usable(record, max_age_minutes: float = _CACHE_TTL_MINUTES) -> bool:
    """True for a real, recent reading: not a placeholder or error row, with some confidence."""
    return bool(
        record
        and not record.get("error")
        and not _is_no_articles(record)
        and record.get("sentiment_score") is not None
        and (record.get("confidence") or 0) > 0
        and not _is_stale(record, max_age_minutes)
    )


def usable_sentiment_records(max_age_minutes: float = _DISPLAY_MAX_AGE_MINUTES) -> list:
    """
    Usable readings for the active assets only (MongoDB merged with this process's memory).
    Reads only; never runs the pipeline. Empty if the engine isn't installed.
    """
    try:
        _engine()
    except RuntimeError:
        return []
    return [r for r in _all_latest().values() if is_usable(r, max_age_minutes)]


def current_sentiment(asset_id: str):
    """
    A usable reading for one asset, refreshing it (within the request budget) if the stored
    one is stale. Returns None if there isn't one: unknown or out-of-scope asset, no articles,
    pipeline failure or timeout. Callers must treat None as "no sentiment", not as neutral.
    """
    if asset_id not in _ACTIVE_ASSETS:
        return None
    try:
        record = _latest(asset_id)
        if not is_usable(record):
            future = _request_pool.submit(_refresh_asset, asset_id)
            record, _ = future.result(timeout=_REQUEST_BUDGET_SECONDS)
    except (FuturesTimeout, Exception) as exc:
        logging.getLogger("sentiment_api").warning("no current sentiment for %s: %s", asset_id, exc)
        return None
    return record if is_usable(record) else None


def _neutral(asset_id: str, error: str = "") -> dict:
    return {
        "asset_id":               asset_id,
        "sentiment_score":        0.0,
        "confidence":             0.0,
        "confidence_label":       "low",
        "signal_strength":        "weak",
        "trend":                  "unknown",
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
    Serves cached results from MongoDB where they are fresh; runs the pipeline for assets
    that are missing from the cache or whose cached result is stale (the same freshness
    rule as GET /sentiment/{asset}). Adding a new asset to the engine's ASSETS never requires
    a full cache flush — only the new one is run on the next request.
    """
    _engine()  # fail early with a clear error if the engine isn't installed

    # Latest record per active asset (MongoDB merged with this process's memory)
    cached_map = _all_latest()

    # Which active assets have no cached entry yet, or only a stale one?
    missing = [a for a in _ACTIVE_ASSETS if a not in cached_map or _is_stale(cached_map[a])]

    if missing:
        def _run_one(asset_id: str) -> tuple[str, dict]:
            try:
                record, _ = _refresh_asset(asset_id)
                return asset_id, record
            except Exception as exc:
                logging.getLogger("sentiment_api").error("pipeline failed for %s: %s", asset_id, exc)
                # Keep serving the stale record if there is one. The exception text stays in
                # the server log; clients get a fixed message.
                return asset_id, cached_map.get(asset_id) or _neutral(asset_id, _UNAVAILABLE)

        # Wait only as long as the client will. Pipelines that are still running keep going
        # in the pool and land in the cache, so the next request finds them; this one serves
        # the last record (or a "still computing" placeholder) for those assets.
        futures = {_request_pool.submit(_run_one, a): a for a in missing}
        done, pending = wait(futures, timeout=_REQUEST_BUDGET_SECONDS)
        for future in done:
            aid, result = future.result()
            cached_map[aid] = result
        for future in pending:
            aid = futures[future]
            cached_map[aid] = cached_map.get(aid) or _neutral(aid, _PENDING)

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
    _engine()  # fail early with a clear error if the engine isn't installed
    try:
        from sentiment_engine.storage.mongo_handler import get_mood_trend as engine_mood_trend
    except ImportError:
        from storage.mongo_handler import get_mood_trend as engine_mood_trend

    return engine_mood_trend(_ACTIVE_ASSETS, days)


# ── GET /sentiment/{asset} ─────────────────────────────────────────────────────

@router.get("/sentiment/{asset}", response_model=SentimentResponse)
def get_sentiment(asset: str):
    """
    Returns latest sentiment for a single asset.
    Serves from MongoDB cache if fresh; otherwise re-runs the pipeline.
    """
    _engine()  # fail early with a clear error if the engine isn't installed

    asset_id = asset.lower()
    if asset_id not in _ACTIVE_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not active. Active assets: {_ACTIVE_ASSETS}",
        )

    cached = _latest(asset_id)
    if cached and not _is_stale(cached):
        return _map_sentiment(cached)

    # No articles this run (or a failed run): the last good, if stale, score beats a neutral 0.0.
    # Wait only as long as the client will; a slow pipeline keeps running and lands in the cache.
    future = _request_pool.submit(_refresh_asset, asset_id)
    try:
        record, _ = future.result(timeout=_REQUEST_BUDGET_SECONDS)
    except FuturesTimeout:
        if cached:
            return _map_sentiment(cached)
        raise HTTPException(status_code=503, detail=_PENDING, headers={"Retry-After": "10"})
    return _map_sentiment(record)


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
    _engine()  # fail early with a clear error if the engine isn't installed

    asset_id = asset.lower()
    if asset_id not in _ACTIVE_ASSETS:
        raise HTTPException(
            status_code=422,
            detail=f"Asset '{asset}' is not active. Active assets: {_ACTIVE_ASSETS}",
        )

    # force=True: a pipeline failure raises (-> 500) rather than being reported as a refresh.
    record, outcome = _refresh_asset(asset_id, force=True)
    return JSONResponse(content={"status": outcome, "result": _map_sentiment(record)})


# ── Background scheduled refresh ───────────────────────────────────────────────

# Pipeline refresh interval — every 15 minutes, well inside the 20 min cache
# TTL, so a user hitting /sentiment always gets data that is fresh.
_REFRESH_INTERVAL_SECONDS = 15 * 60


def _refresh_all_assets() -> None:
    """
    Runs the full sentiment pipeline for every active asset and saves results
    to MongoDB.  Intended to be called from the background scheduler thread.
    """
    log = logging.getLogger("sentiment_scheduler")
    log.info("[scheduler] Starting scheduled pipeline refresh for all assets")

    try:
        _engine()
    except RuntimeError as exc:
        log.error(f"[scheduler] Engine unavailable, skipping refresh: {exc}")
        return

    def _run_one(asset_id: str) -> None:
        try:
            # force: refresh regardless of freshness, but still serialised per asset with
            # any request that is refreshing the same asset right now.
            _, outcome = _refresh_asset(asset_id, force=True)
            log.info(f"[scheduler] {asset_id.upper()}: {outcome}")
        except Exception as exc:
            log.error(f"[scheduler] Failed to refresh {asset_id}: {exc}")

    with ThreadPoolExecutor(max_workers=max(1, len(_ACTIVE_ASSETS))) as executor:
        futures = {executor.submit(_run_one, a): a for a in _ACTIVE_ASSETS}
        for f in as_completed(futures):
            pass  # errors already logged inside _run_one

    log.info("[scheduler] Scheduled refresh complete for all assets")


def _run_scheduler() -> None:
    """
    Infinite loop that calls _refresh_all_assets() every
    _REFRESH_INTERVAL_SECONDS.  Designed to run in a daemon thread so it
    stops cleanly when the process exits.

    Every backend process starts one of these (uvicorn --workers N, and the reloader
    restarts the server on each code change), so each tick first claims the run in
    MongoDB: only one process refreshes per interval and the rest skip that tick. If the
    process doing the work dies, another one claims a later tick.
    """
    from utils.scheduler_gate import claim_run

    log = logging.getLogger("sentiment_scheduler")

    # Initial delay: let the FinBERT warmup finish first before the first run
    log.info(f"[scheduler] First pipeline run in 90 seconds, then every "
             f"{_REFRESH_INTERVAL_SECONDS // 60} minutes")
    time.sleep(90)

    while True:
        # A minute of slack so a tick that fires slightly early (clock drift, loop timing)
        # still counts as a new interval instead of being skipped for a whole one.
        if claim_run("sentiment-refresh", _REFRESH_INTERVAL_SECONDS - 60):
            _refresh_all_assets()
        else:
            log.info("[scheduler] Another process already refreshed this interval; skipping")
        time.sleep(_REFRESH_INTERVAL_SECONDS)
