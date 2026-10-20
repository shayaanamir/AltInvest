"""
utils/scheduler_gate.py

Lets several backend processes (uvicorn --workers N, or the reloader restarting the
server) share one periodic job without running it more than once per interval.

Every process still starts its own scheduler thread. Before each run the thread calls
claim_run(); only the process that wins the claim runs the job, the others skip that
tick. Because the claim is "has nobody run this in the last min_gap_seconds?", it needs
no leader election and survives a crash: if the process that was running the job dies,
another one claims the next tick.
"""

import logging
import os
import socket
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from db.mongo_connection import get_db

log = logging.getLogger("scheduler_gate")

_COLLECTION = "scheduler_runs"


def claim_run(name: str, min_gap_seconds: float) -> bool:
    """
    Atomically claims the right to run job `name` now. Returns True if the job has not
    been claimed within the last `min_gap_seconds` (the caller should run it), False if
    another process already has (the caller should skip this tick).

    If the database can't be reached the claim fails open — returns True — so a single
    process without Mongo still runs its job instead of silently never running it.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=min_gap_seconds)
    try:
        # Matches (and updates) the job's record only if it hasn't run recently. If the
        # record exists but ran recently the filter misses, the upsert then tries to insert
        # the same _id, and the duplicate-key error means another process holds the claim.
        get_db()[_COLLECTION].find_one_and_update(
            {"_id": name, "last_run": {"$lte": cutoff}},
            {"$set": {"last_run": now, "owner": f"{socket.gethostname()}:{os.getpid()}"}},
            upsert=True,
        )
        return True
    except DuplicateKeyError:
        return False
    except Exception as exc:
        log.warning("claim_run(%s) could not reach the database, running anyway: %s", name, exc)
        return True
