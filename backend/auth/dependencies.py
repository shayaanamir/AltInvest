"""
backend/auth/dependencies.py

FastAPI dependency that extracts and validates the current user from the
Authorization header, for use on any USER-scoped route.

A login token is only honoured while its row in `user_sessions` exists, so deleting
that row ("log out of other sessions", logout, password change) revokes it at once.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Depends, Header, HTTPException

from auth.security import decode_access_token
from utils.http_errors import db_unavailable

# How stale `last_active` may get before a request writes a fresh value.
_TOUCH_INTERVAL = timedelta(minutes=5)


@dataclass
class CurrentSession:
    user_id: ObjectId
    session_id: ObjectId


def _resolve(token: str) -> Optional[CurrentSession]:
    """The live session behind a token, or None if the token is bad, expired or revoked.
    Database errors propagate."""
    payload = decode_access_token(token)
    if not payload:
        return None
    try:
        user_id = ObjectId(payload.get("sub"))
        session_id = ObjectId(payload.get("sid"))
    except Exception:
        return None

    from db.queries import get_user_session, touch_user_session
    row = get_user_session(str(session_id))
    if not row or row.get("user_id") != user_id:
        return None

    now = datetime.now(timezone.utc)
    last = row.get("last_active")
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or now - last > _TOUCH_INTERVAL:
        touch_user_session(session_id, now)
    return CurrentSession(user_id=user_id, session_id=session_id)


def get_current_session(authorization: str = Header(...)) -> CurrentSession:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header."
        )
    try:
        session = _resolve(authorization.split(" ", 1)[1])
    except Exception as exc:
        raise db_unavailable(exc)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return session


def get_current_user_id(session: CurrentSession = Depends(get_current_session)) -> ObjectId:
    return session.user_id


def get_optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[ObjectId]:
    """
    For public routes that personalise when a valid token is present (e.g. the
    held/watching flags on /discover). A missing, bad or revoked token means anonymous,
    never a 401 — and so does a session lookup that fails.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        session = _resolve(authorization.split(" ", 1)[1])
    except Exception:
        return None
    return session.user_id if session else None
