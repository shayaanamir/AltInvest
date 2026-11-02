"""
backend/controllers/ml_pull_controller.py

Daily pull of the ML service (ml/, port 8001) into MongoDB: GET /predict/{asset} -> `predictions`,
GET /risk/{asset} -> `risk_scores`, for the assets in db.queries.ML_COVERED_ASSETS.
Responses follow ml/docs/CONTRACT.md and are stored field for field (including `note` and `signal`).

Rules (ml/docs/PLAN_NEXT.md, task C1):
  - each call: 10 s timeout, 3 retries with backoff;
  - 404 -> the asset is not covered: skip it, no retry;
  - 503, a timeout or a bad body -> write nothing, so the last good row stays the newest;
  - `timestamp` is stored as a datetime (Mongo sorts Date above String).
Schedule: once at startup, then daily at 00:15 UTC (ML refreshes its data at 00:05 UTC).

Manual run (inside the backend container): python -m controllers.ml_pull_controller
"""
import path_setup  # noqa: F401  (puts the repo root on sys.path for `db`)

import os
import time
from datetime import datetime, timedelta, timezone

import httpx

ML_BASE_URL = os.getenv("ML_BASE_URL", "http://ml:8001").rstrip("/")
TIMEOUT_SECONDS = 10.0
RETRIES = 3                       # retries after the first attempt
BACKOFF_SECONDS = (2, 4, 8)       # wait before retry 1, 2, 3
PULL_AT_UTC = (0, 15)             # HH, MM
RETRY_AFTER_FAILURE_SECONDS = 15 * 60   # ML can be down for minutes after it starts (ml bug A1)

_PREDICT_REQUIRED = ("asset", "predicted_price", "prediction_30d", "confidence", "model_version", "timestamp")
_RISK_REQUIRED = ("asset", "risk_score", "timestamp")


def _log(msg: str) -> None:
    print(f"[ml-pull] {msg}", flush=True)


def _parse_ts(value) -> datetime:
    """ISO-8601 'YYYY-MM-DDTHH:MM:SSZ' -> aware UTC datetime. Raises ValueError otherwise."""
    if not isinstance(value, str):
        raise ValueError(f"timestamp is not a string: {value!r}")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value!r}")
    return dt.astimezone(timezone.utc)


def fetch(client: httpx.Client, path: str, sleep=time.sleep) -> tuple[str, dict | None, str]:
    """
    GET {ML_BASE_URL}{path}. Returns (status, body, reason) with status one of
    "ok" (body is the JSON dict), "not_covered" (404) or "failed" (503 / timeout / other).
    """
    url = f"{ML_BASE_URL}{path}"
    reason = ""
    for attempt in range(RETRIES + 1):
        if attempt:
            sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
        try:
            resp = client.get(url, timeout=TIMEOUT_SECONDS)
        except httpx.TimeoutException:
            reason = "timeout"
            continue
        except httpx.HTTPError as exc:
            reason = f"{type(exc).__name__}: {exc}"
            continue
        if resp.status_code == 404:
            return "not_covered", None, "404"
        if resp.status_code == 200:
            try:
                body = resp.json()
            except ValueError:
                return "failed", None, "200 with a body that is not JSON"
            if not isinstance(body, dict):
                return "failed", None, "200 with a body that is not an object"
            return "ok", body, "200"
        reason = f"HTTP {resp.status_code}"
    return "failed", None, reason


def _to_row(body: dict, asset: str, required: tuple, now: datetime) -> dict:
    """The response as a Mongo row; raises ValueError if it can't be stored."""
    missing = [k for k in required if k not in body]
    if missing:
        raise ValueError(f"missing fields {missing}")
    if str(body["asset"]).upper() != asset:
        raise ValueError(f"asked for {asset}, got {body['asset']!r}")
    return {**body, "asset": asset, "timestamp": _parse_ts(body["timestamp"]),
            "source": "ml-service", "pulled_at": now}


def pull_asset(client: httpx.Client, asset: str, sleep=time.sleep, now: datetime | None = None) -> dict:
    """Pulls /predict and /risk for one asset and stores what came back. Returns {endpoint: outcome}."""
    from db.queries import upsert_ml_prediction, upsert_ml_risk

    now = now or datetime.now(timezone.utc)
    outcome = {}
    for name, path, required, store in (
        ("predict", f"/predict/{asset.lower()}", _PREDICT_REQUIRED, upsert_ml_prediction),
        ("risk", f"/risk/{asset.lower()}", _RISK_REQUIRED, upsert_ml_risk),
    ):
        status, body, reason = fetch(client, path, sleep=sleep)
        if status == "not_covered":
            outcome[name] = "skipped: 404 not covered"
            continue
        if status == "failed":
            outcome[name] = f"failed: {reason}; nothing written"
            continue
        try:
            row = _to_row(body, asset, required, now)
            if name == "risk" and not isinstance(row.get("risk_score"), (int, float)):
                raise ValueError("risk_score is not a number")
            store(row)
            outcome[name] = "stored"
        except ValueError as exc:
            outcome[name] = f"failed: bad body ({exc}); nothing written"
    return outcome


def pull_all(client: httpx.Client | None = None, sleep=time.sleep) -> dict:
    """Pulls every covered asset. Returns {asset: {endpoint: outcome}}. Never raises for HTTP errors."""
    from db.queries import ML_COVERED_ASSETS

    own = client is None
    client = client or httpx.Client()
    try:
        return {a: pull_asset(client, a, sleep=sleep) for a in ML_COVERED_ASSETS}
    finally:
        if own:
            client.close()


def has_failures(result: dict) -> bool:
    return any(v.startswith("failed") for per in result.values() for v in per.values())


def seconds_until_next_pull(now: datetime) -> float:
    hh, mm = PULL_AT_UTC
    nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


def run_ml_pull_scheduler(initial_delay_seconds: int = 20) -> None:
    """
    Daemon-thread loop: a pull shortly after startup, then daily at 00:15 UTC. After a run with a
    failure it tries again in 15 min (but never later than the next 00:15). Never raises.
    """
    time.sleep(initial_delay_seconds)
    while True:
        try:
            result = pull_all()
            _log(f"{ML_BASE_URL}: {result}")
            failed = has_failures(result)
        except Exception as exc:   # database down etc.; keep the thread alive
            from utils.http_errors import redact
            _log(f"run failed: {type(exc).__name__}: {redact(exc)}")
            failed = True
        wait = seconds_until_next_pull(datetime.now(timezone.utc))
        if failed:
            wait = min(wait, RETRY_AFTER_FAILURE_SECONDS)
        _log(f"next pull in {int(wait)} s")
        time.sleep(wait)


if __name__ == "__main__":
    print(pull_all())
