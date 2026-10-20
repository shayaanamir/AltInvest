"""
backend/auth/rate_limit.py

Attempt limits for the auth endpoints (brute force, password spraying, email flooding).

Each counted attempt is a row in `auth_attempts` ({key, at, expires_at}); a limit is "at most N rows
for this key in the last W minutes", so the window slides and rows expire on their own (TTL index).
Mongo rather than process memory, so limits survive restarts and are shared if more workers run.

Client IP: request.client.host, which behind a reverse proxy (or Docker's port forwarding) is the
proxy's address for everyone. Set TRUST_PROXY_HEADERS=true when a trusted proxy sets
X-Forwarded-For, so the original client's address is used instead.
"""
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from utils.http_errors import db_unavailable


@dataclass(frozen=True)
class Limit:
    name: str
    max_attempts: int
    window: timedelta
    message: str


LOGIN_FAILURES_PER_ACCOUNT_IP = Limit(
    "login_fail_acct_ip", 5, timedelta(minutes=15),
    "Too many failed sign-in attempts for this account.",
)
LOGIN_FAILURES_PER_IP = Limit(
    "login_fail_ip", 30, timedelta(minutes=15),
    "Too many failed sign-in attempts from this network.",
)
SIGNUPS_PER_IP = Limit("signup_ip", 10, timedelta(hours=1), "Too many accounts created from this network.")
# Signup has to say when an email is taken (it signs the new user straight in), so those answers are
# capped tightly per IP to make probing which addresses have accounts impractical.
SIGNUP_TAKEN_PER_IP = Limit("signup_taken_ip", 5, timedelta(hours=1), "Too many signup attempts from this network.")
# At most one "someone tried to sign up with your email" notice per address per day.
SIGNUP_TAKEN_NOTICE_PER_EMAIL = Limit("signup_taken_notice", 1, timedelta(days=1), "")
FORGOT_PER_EMAIL = Limit("forgot_email", 3, timedelta(hours=1), "Too many password reset requests for this email.")
FORGOT_PER_IP = Limit("forgot_ip", 10, timedelta(hours=1), "Too many password reset requests.")
RESET_PER_IP = Limit("reset_ip", 10, timedelta(minutes=15), "Too many password reset attempts.")
WRONG_PASSWORD_PER_USER = Limit(
    "wrong_pw_user", 5, timedelta(minutes=15), "Too many incorrect password attempts.",
)

_TRUST_PROXY = (os.getenv("TRUST_PROXY_HEADERS") or "").lower() == "true"
_indexes_ready = False


def client_ip(request: Request) -> str:
    if _TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _attempts():
    global _indexes_ready
    from db.mongo_connection import get_db
    coll = get_db().auth_attempts
    if not _indexes_ready:
        coll.create_index([("key", 1), ("at", -1)])
        coll.create_index("expires_at", expireAfterSeconds=0)
        _indexes_ready = True
    return coll


def _key(limit: Limit, subject: str) -> str:
    return f"{limit.name}:{subject.lower()}"


def _wait_text(seconds: int) -> str:
    minutes = math.ceil(seconds / 60)
    return "a minute" if minutes <= 1 else f"{minutes} minutes"


def check(limit: Limit, subject: str) -> None:
    """Raises 429 (with Retry-After) if `subject` has used up `limit`. Records nothing."""
    now = datetime.now(timezone.utc)
    key = _key(limit, subject)
    since = now - limit.window
    try:
        coll = _attempts()
        if coll.count_documents({"key": key, "at": {"$gt": since}}, limit=limit.max_attempts) < limit.max_attempts:
            return
        # The window frees a slot when the oldest attempt still inside it ages out.
        oldest = coll.find_one({"key": key, "at": {"$gt": since}}, sort=[("at", 1)], projection={"at": 1})
    except Exception as exc:
        raise db_unavailable(exc)
    at = oldest["at"] if oldest else now
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    retry_after = max(1, int((at + limit.window - now).total_seconds()))
    raise HTTPException(
        status_code=429,
        detail=f"{limit.message} Try again in {_wait_text(retry_after)}.",
        headers={"Retry-After": str(retry_after)},
    )


def record(limit: Limit, subject: str) -> None:
    now = datetime.now(timezone.utc)
    try:
        _attempts().insert_one({"key": _key(limit, subject), "at": now, "expires_at": now + limit.window})
    except Exception as exc:
        raise db_unavailable(exc)


def hit(limit: Limit, subject: str) -> None:
    """check() then record(): for limits on every attempt, not just failed ones."""
    check(limit, subject)
    record(limit, subject)


def clear(limit: Limit, subject: str) -> None:
    try:
        _attempts().delete_many({"key": _key(limit, subject)})
    except Exception as exc:
        raise db_unavailable(exc)
