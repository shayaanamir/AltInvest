"""
backend/auth/security.py

Password hashing and JWT helpers for AUTH-01 (Login).

SECURITY NOTE: JWT_SECRET must be set (at least 32 bytes) in every environment except
APP_ENV=dev/test (shared/app_env.py). Without it, or with a short one, the backend refuses to
start; in dev it falls back to a public development secret and logs a warning.
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from shared.app_env import app_env, is_dev

_DEV_JWT_SECRET = "insecure-dev-secret-change-me"
JWT_SECRET_MIN_BYTES = 32


def _load_jwt_secret() -> str:
    # `or`, not a getenv default: docker-compose passes an unset variable through as "".
    secret = os.getenv("JWT_SECRET") or ""
    if len(secret.encode("utf-8")) >= JWT_SECRET_MIN_BYTES and secret != _DEV_JWT_SECRET:
        return secret
    if not is_dev():
        raise RuntimeError(
            f"JWT_SECRET must be set to at least {JWT_SECRET_MIN_BYTES} bytes (APP_ENV={app_env()!r}). "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))" '
            "or set APP_ENV=dev on a development machine."
        )
    logging.getLogger("auth").warning(
        "JWT_SECRET is missing or shorter than %d bytes; APP_ENV=%s, so signing tokens with the "
        "built-in development secret. Anyone who knows it can forge logins.",
        JWT_SECRET_MIN_BYTES, app_env(),
    )
    return secret or _DEV_JWT_SECRET


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
# Sliding sessions: a token lives JWT_EXPIRY_HOURS; while the user is active the client trades it for
# a fresh one (POST /auth/refresh), so only 24h of inactivity signs them out — or SESSION_MAX_DAYS
# after the original sign-in, whichever comes first.
JWT_EXPIRY_HOURS = 24
SESSION_MAX_DAYS = 30
RESET_TOKEN_EXPIRY_MINUTES = 30
VERIFY_TOKEN_EXPIRY_HOURS = 24

PASSWORD_MIN_LENGTH = 8
# bcrypt only reads the first 72 bytes (newer versions raise past that), so longer is refused.
PASSWORD_MAX_BYTES = 72


def password_problem(password: str, label: str = "Password") -> str | None:
    """Why a new password is unacceptable, or None if it's fine."""
    if len(password or "") < PASSWORD_MIN_LENGTH:
        return f"{label} must be at least {PASSWORD_MIN_LENGTH} characters."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"{label} is too long (at most {PASSWORD_MAX_BYTES} bytes, about {PASSWORD_MAX_BYTES} characters)."
    return None


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


def create_access_token(user_id: str, email: str, session_id: str, expires_at: datetime) -> str:
    """Issues a signed JWT for an authenticated user, tied to a row in user_sessions (`sid`)."""
    payload = {
        "sub": user_id,
        "email": email,
        "sid": session_id,
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodes/validates a login JWT. Returns the payload, or None if invalid/expired or not a
    login token (reset and verification tokens carry a `purpose` and no session id)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") or not payload.get("sid"):
        return None
    return payload

def password_fingerprint(password_hash: str | None) -> str:
    """A short keyed digest of the stored password hash. A reset token carries it, so the token
    stops working the moment the password changes: it is single-use, and any reset or change
    invalidates every other outstanding link."""
    digest = hmac.new(JWT_SECRET.encode("utf-8"), (password_hash or "").encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()[:32]


def create_reset_token(user_id: str, email: str, password_hash: str | None) -> str:
    """Issues a short-lived, single-purpose, single-use JWT for password reset."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "password_reset",
        "pwf": password_fingerprint(password_hash),
        "iat": now,
        "exp": now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_verify_token(user_id: str, email: str) -> str:
    """Issues a single-purpose JWT for confirming an email address (valid 24 hours)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "email_verify",
        "iat": now,
        "exp": now + timedelta(hours=VERIFY_TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_verify_token(token: str) -> dict | None:
    """Returns the payload of a valid, unexpired email-verification token, else None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "email_verify":
        return None
    return payload


def decode_reset_token(token: str) -> dict | None:
    """Decodes/validates a reset token. Returns None if invalid, expired,
    or not actually a reset token (rejects a stray login JWT, say)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "password_reset" or not payload.get("pwf"):
        return None
    return payload