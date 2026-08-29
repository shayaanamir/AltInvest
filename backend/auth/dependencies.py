"""
backend/auth/dependencies.py

FastAPI dependency that extracts and validates the current user from the
Authorization header, for use on any USER-scoped route.
"""
from bson import ObjectId
from fastapi import Header, HTTPException

from auth.security import decode_access_token


def get_current_user_id(authorization: str = Header(...)) -> ObjectId:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header."
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    sub = payload.get("sub")
    try:
        return ObjectId(sub)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token subject.")