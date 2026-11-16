"""
GET /health: liveness plus the two things that actually break the app.

- database: pinged on every call. When it doesn't answer, the response is 503, so a load balancer,
  a compose healthcheck or an uptime monitor sees the outage (it used to return a constant "ok").
- jobs: when each background scheduler last claimed a run (the scheduler_runs collection written by
  utils/scheduler_gate.claim_run). A timestamp that stops moving means that job is stuck or failing
  to start. Only names and times are returned, never the owning host or process.
"""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db.mongo_connection import get_db, ping
from models.schemas import HealthResponse
from utils.http_errors import redact

router = APIRouter(tags=["System"])
_log = logging.getLogger("health")

VERSION = "1.0"


def _iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(value, "strftime") else None


def _job_runs() -> dict:
    try:
        rows = get_db().scheduler_runs.find({}, {"last_run": 1}).limit(100)
        return {str(r["_id"]): _iso(r.get("last_run")) for r in rows}
    except Exception as exc:
        _log.warning("health: could not read scheduler_runs: %s", redact(exc))
        return {}


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health_check():
    try:
        ping()
    except Exception as exc:
        _log.error("health: database unreachable: %s: %s", type(exc).__name__, redact(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "version": VERSION, "database": "unreachable", "jobs": {}},
        )
    return {"status": "ok", "version": VERSION, "database": "ok", "jobs": _job_runs()}
