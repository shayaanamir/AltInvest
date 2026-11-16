"""
backend/auth/google_oauth.py

AUTH-11 — Sign in with Google.

The frontend opens Google's consent popup (Google Identity Services, authorization-code flow with
redirect_uri "postmessage") and hands the one-time `code` to POST /auth/google. Here that code is
traded for tokens at Google's token endpoint using the client secret, and the returned ID token is
verified against Google's published signing keys before anything about it is trusted.

Configuration (both required, otherwise Google sign-in answers 503):
    GOOGLE_CLIENT_ID      — the OAuth 2.0 "Web application" client ID
    GOOGLE_CLIENT_SECRET  — its secret (never sent to the browser)
"""
import logging
import os
from dataclasses import dataclass

import httpx
import jwt
from fastapi import HTTPException

log = logging.getLogger("auth")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
# The GIS popup code flow returns the code to the opener page rather than a redirect URL.
POPUP_REDIRECT_URI = "postmessage"

# Google rotates its keys rarely; PyJWKClient caches them and refetches on an unknown `kid`.
_jwks_client = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=6 * 3600)


def client_id() -> str:
    return (os.getenv("GOOGLE_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()


def configured() -> bool:
    return bool(client_id() and _client_secret())


@dataclass
class GoogleIdentity:
    sub: str            # Google's stable account id — the link key, unlike email it never changes
    email: str
    email_verified: bool
    name: str
    picture: str | None


def _exchange_code(code: str) -> str:
    """Trades the authorization code for tokens; returns the raw ID token."""
    try:
        res = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id(),
                "client_secret": _client_secret(),
                "redirect_uri": POPUP_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
    except httpx.HTTPError as exc:
        log.warning("google token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail="Couldn't reach Google. Try again.")

    if res.status_code != 200:
        # invalid_grant: the code was used already, expired, or came from another client.
        log.info("google token exchange rejected (%s): %s", res.status_code, res.text[:300])
        raise HTTPException(status_code=400, detail="Google sign-in didn't complete. Try again.")

    id_token = (res.json() or {}).get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="Google didn't return an identity. Try again.")
    return id_token


def verify_id_token(id_token: str) -> GoogleIdentity:
    """Checks the signature, audience, issuer and expiry of a Google ID token."""
    invalid = HTTPException(status_code=400, detail="Google sign-in couldn't be verified. Try again.")
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id(),
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=30,
        )
    except jwt.PyJWKClientError as exc:
        log.warning("google signing keys unavailable: %s", exc)
        raise HTTPException(status_code=502, detail="Couldn't reach Google. Try again.")
    except jwt.PyJWTError as exc:
        log.info("google id token rejected: %s", exc)
        raise invalid

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise invalid
    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Your Google account didn't share an email address.")

    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=email,
        email_verified=claims.get("email_verified") in (True, "true"),
        name=(claims.get("name") or claims.get("given_name") or email.split("@")[0]).strip(),
        picture=claims.get("picture"),
    )


def identity_from_code(code: str) -> GoogleIdentity:
    if not configured():
        raise HTTPException(status_code=503, detail="Google sign-in isn't set up on this server.")
    if not code:
        raise HTTPException(status_code=422, detail="Missing Google authorization code.")
    return verify_id_token(_exchange_code(code))
