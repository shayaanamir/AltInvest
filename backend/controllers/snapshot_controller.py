"""
backend/controllers/snapshot_controller.py

Writes one `portfolio_snapshots` row per user per day, valued with the same
get_valued_holdings() the Portfolio and Dashboard pages use. This is what the
Dashboard's 1W / 1M / 3M / 1Y performance chart reads.
"""
import time
import logging
from datetime import datetime, timezone

from controllers.portfolio_controller import get_total_portfolio_value
from db.mongo_connection import get_db

log = logging.getLogger("portfolio_snapshots")

_INTERVAL_SECONDS = 60 * 60   # hourly; the upsert keeps it to one row per user per day


def record_snapshots() -> int:
    """Upserts today's snapshot for every user that has holdings. Returns rows written."""
    db = get_db()
    db.portfolio_snapshots.create_index([("user_id", 1), ("snapshot_date", -1)])

    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%dT00:00:00Z")
    written = 0
    for user_id in db.portfolio_holdings.distinct("user_id"):
        try:
            total = get_total_portfolio_value(user_id)
            if total is None:
                # A holding couldn't be valued; a snapshot without it would look like a drop.
                log.warning("snapshot skipped for %s: a holding has no price", user_id)
                continue
        except Exception as exc:
            log.error("snapshot skipped for %s: %s", user_id, exc)
            continue
        db.portfolio_snapshots.update_one(
            {"user_id": user_id, "snapshot_date": day},
            {"$set": {"total_value_usd": total, "source": "live", "nft_at_current_floor": False, "updated_at": now}},
            upsert=True,
        )
        written += 1
    return written


def run_snapshot_scheduler() -> None:
    """Daemon-thread loop: snapshot at startup, then hourly. Never raises."""
    while True:
        try:
            n = record_snapshots()
            log.info("[snapshots] recorded %d portfolio snapshot(s)", n)
        except Exception as exc:
            log.error("[snapshots] run failed: %s", exc)
        time.sleep(_INTERVAL_SECONDS)
