"""
backend/auth/security.py

Password hashing and JWT helpers for AUTH-01 (Login).

SECURITY NOTE (see AltInvest_Implementation_Checklist.md, Section 23):
JWT_SECRET MUST be set via environment variable in any real deployment.
The default below is for local development only and must never be
relied on outside a dev machine.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "insecure-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
RESET_TOKEN_EXPIRY_MINUTES = 30

def hash_password(plain_password: str) -> str:
    """Hashes a plaintext password with bcrypt for storage."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str) -> str:
    """Issues a signed JWT for an authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodes/validates a JWT. Returns the payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

def create_reset_token(user_id: str, email: str) -> str:
    """Issues a short-lived, single-purpose JWT for password reset."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "password_reset",
        "iat": now,
        "exp": now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_reset_token(token: str) -> dict | None:
    """Decodes/validates a reset token. Returns None if invalid, expired,
    or not actually a reset token (rejects a stray login JWT, say)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "password_reset":
        return None
    return payload