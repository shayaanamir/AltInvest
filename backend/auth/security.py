"""
backend/auth/security.py

Password hashing and JWT helpers for AUTH-01 (Login).

SECURITY NOTE (see AltInvest_Implementation_Checklist.md, Section 23):
JWT_SECRET MUST be set via environment variable in any real deployment.
The default below is for local development only and must never be
relied on outside a dev machine.
"""
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

_DEV_JWT_SECRET = "insecure-dev-secret-change-me"
# `or`, not a getenv default: docker-compose passes an unset variable through as "".
JWT_SECRET = os.getenv("JWT_SECRET") or _DEV_JWT_SECRET
if JWT_SECRET == _DEV_JWT_SECRET:
    logging.getLogger("auth").warning(
        "JWT_SECRET is not set; signing tokens with the built-in development secret. "
        "Anyone who knows it can forge logins. Set JWT_SECRET in .env for any shared or deployed instance."
    )
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


# Practical address check, not full RFC 5322: ASCII local part (no leading, trailing or doubled dots),
# then a domain of valid labels ending in an alphabetic TLD.
_EMAIL_RE = re.compile(
    r"^(?!\.)(?!.*\.\.)[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}(?<!\.)"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)
EMAIL_MAX_LENGTH = 254


def normalize_email(raw: str | None) -> str | None:
    """Trimmed, lower-cased address, or None if it isn't a plausible email."""
    email = (raw or "").strip().lower()
    if len(email) > EMAIL_MAX_LENGTH or not _EMAIL_RE.match(email):
        return None
    return email


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

def password_fingerprint(password_hash: str) -> str:
    """A short keyed digest of the stored hash. It changes whenever the password does (bcrypt salts
    every hash), and reveals nothing about the hash without JWT_SECRET."""
    return hmac.new(JWT_SECRET.encode(), (password_hash or "").encode(), hashlib.sha256).hexdigest()[:32]


def create_reset_token(user_id: str, email: str, password_hash: str) -> str:
    """
    Issues a short-lived, single-purpose JWT for password reset. It carries a fingerprint of the
    current password hash (`pwv`), so it stops working as soon as the password changes — which
    makes it single-use, and also kills older links after any password change.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "password_reset",
        "pwv": password_fingerprint(password_hash),
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
    if payload.get("purpose") != "password_reset":
        return None
    return payload