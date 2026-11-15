"""
backend/controllers/nft_sentiment_controller.py

Runs the NFT sentiment pipeline (sentiment_engine/nft_sentiment) for every tracked collection and the
NFT market, and stores the readings (db.queries.save_nft_sentiment). The engine is pure; this module does
the I/O around it:

  in   news from the engine's collector (fetched once per cycle for every target),
       the latest ML-service rows of nft_market_data and nft_liquidity for the market signal,
       the stored readings around 24 h ago for the trend
  out  nft_sentiment (latest per slug) and nft_sentiment_history

Requests never run the pipeline (routes/nft.py only reads), so a page view never costs a Groq call.
Every 30 minutes is plenty for NFT news; the scorer's cache means a collection whose article list has not
changed costs no LLM call at all.
"""
import path_setup  # noqa: F401

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("nft_sentiment")

REFRESH_INTERVAL_SECONDS = 30 * 60
INITIAL_DELAY_SECONDS = 120          # after the ML pull (20 s) has had a chance to fill nft_market_data
MARKET_ROW_MAX_AGE = timedelta(days=3)

_run_lock = threading.Lock()


def _engine():
    """Lazy import, like routes/sentiment.py: the backend starts even if the engine's deps are missing."""
    try:
        from sentiment_engine.nft_sentiment import config, collector, market_signals
        from sentiment_engine.nft_sentiment.aggregator import ScoringUnavailable, run_collection_pipeline
    except ImportError:
        from nft_sentiment import config, collector, market_signals
        from nft_sentiment.aggregator import ScoringUnavailable, run_collection_pipeline
    return config, collector, market_signals, ScoringUnavailable, run_collection_pipeline


def _aware(ts):
    if not isinstance(ts, datetime):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def usable_ml_row(row, now: datetime):
    """Only rows the ML pull wrote (source ml-service) and recent enough to describe the market now."""
    if not row or row.get("source") != "ml-service":
        return None
    ts = _aware(row.get("timestamp"))
    if ts is None or now - ts > MARKET_ROW_MAX_AGE:
        return None
    return row


def refresh_all() -> dict:
    """
    One cycle for every target. Returns {target: outcome}, outcome being "saved", "placeholder" (no
    relevant news: the last real reading is kept), "scoring_unavailable" or "failed: ...". A target that
    fails never stops the others. Returns {"skipped": "already running"} if a cycle is in progress.
    """
    if not _run_lock.acquire(blocking=False):
        return {"skipped": "already running"}
    try:
        return _refresh_all()
    finally:
        _run_lock.release()


def _refresh_all() -> dict:
    from db.queries import (
        get_nft_collections_by_slug,
        get_nft_liquidity,
        get_nft_market_data_latest_by_slug,
        get_nft_sentiment_baseline,
        save_nft_sentiment,
    )

    cfg, collector, market_signals, ScoringUnavailable, run_collection_pipeline = _engine()
    now = datetime.now(timezone.utc)
    slugs = list(cfg.NFT_COLLECTIONS)

    try:
        names = {s: (c.get("name") or s) for s, c in get_nft_collections_by_slug(slugs).items()}
        market_rows = get_nft_market_data_latest_by_slug(slugs)
    except Exception as exc:
        log.warning("NFT collections/market rows unavailable, running on config names and no market signal: %s", exc)
        names, market_rows = {}, {}

    articles = collector.collect(slugs, include_market=True)
    outcome: dict = {}
    for target, items in articles.items():
        try:
            if target == cfg.NFT_MARKET_ID:
                name, signal = cfg.NFT_MARKET["name"], None
            else:
                name = names.get(target) or cfg.NFT_COLLECTIONS[target]["name"]
                signal = market_signals.build_market_signal(
                    usable_ml_row(market_rows.get(target), now), usable_ml_row(get_nft_liquidity(target), now))
            try:
                history = get_nft_sentiment_baseline(target)
            except Exception:
                history = []
            result = run_collection_pipeline(target, name, items, market_signal=signal, history=history)
            outcome[target] = save_nft_sentiment(result)
        except ScoringUnavailable as exc:
            log.warning("%s: %s; keeping the last reading", target, exc)
            outcome[target] = "scoring_unavailable"
        except Exception as exc:
            from utils.http_errors import redact
            log.error("%s failed: %s: %s", target, type(exc).__name__, redact(exc))
            outcome[target] = f"failed: {type(exc).__name__}"
    return outcome


def run_nft_sentiment_scheduler(initial_delay_seconds: int = INITIAL_DELAY_SECONDS) -> None:
    """
    Daemon-thread loop. Like the crypto scheduler, each tick first claims the run in MongoDB, so with
    several backend processes only one refreshes per interval. Never raises.
    """
    from utils.scheduler_gate import claim_run

    time.sleep(initial_delay_seconds)
    while True:
        try:
            if claim_run("nft-sentiment-refresh", REFRESH_INTERVAL_SECONDS - 60):
                log.info("[nft-sentiment] %s", refresh_all())
            else:
                log.info("[nft-sentiment] another process refreshed this interval; skipping")
        except Exception as exc:
            from utils.http_errors import redact
            log.error("[nft-sentiment] cycle failed: %s: %s", type(exc).__name__, redact(exc))
        time.sleep(REFRESH_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(refresh_all())
