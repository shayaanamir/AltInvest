"""
routes/auth.py

AUTH-01 — Login.
AUTH-02 — Signup.

POST /auth/login and POST /auth/signup check/write against the `users`
collection in the unified MongoDB database (db/mongo_connection.py) and
issue a JWT.

AUTH-03/04 — Forgot / reset password.
AUTH-05 — Email verification: a link is emailed at signup and on request from the profile page.
AUTH-06 — Change password from Settings (requires the current password).
AUTH-07 — Sessions: every login is a row in `user_sessions`; Settings lists them and can
          revoke them (one, or all but this one). Logout drops the caller's own row.

Emails go out through utils/mailer.py (SMTP when configured, otherwise the link is logged).
"""
import logging
import os
import path_setup  # noqa: F401 — must be first, fixes sys.path

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from utils.http_errors import db_unavailable
from bson import ObjectId
from models.schemas import (
    LoginRequest, AuthResponse, AuthUser, SignupRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
    ChangePasswordRequest, SessionInfo,
)
from auth.security import (
    verify_password, create_access_token, hash_password,
    create_reset_token, decode_reset_token,
    create_verify_token, decode_verify_token,
    decode_access_token, JWT_EXPIRY_HOURS,
)
from auth.dependencies import get_current_user_id, get_current_session, CurrentSession
from utils.mailer import send_email, smtp_configured
from db.queries import create_default_user_settings

router = APIRouter(tags=["Auth"])
log = logging.getLogger("auth")

# Used to build the link embedded in the reset email. Override via env in
# any deployment where the frontend isn't on localhost:5173.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def _issue_token(user_id: str, email: str, request: Request) -> str:
    """Opens a session row for this sign-in and returns a token bound to it."""
    from db.queries import create_user_session
    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    try:
        session_id = create_user_session(
            ObjectId(user_id), expires_at,
            user_agent=(request.headers.get("user-agent") or "")[:512],
            ip=request.client.host if request.client else None,
        )
    except Exception as exc:
        raise db_unavailable(exc)
    return create_access_token(user_id=user_id, email=email, session_id=session_id, expires_at=expires_at)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request):
    email = (payload.email or "").strip().lower()
    password = payload.password or ""

    if not email or not password:
        raise HTTPException(
            status_code=422, detail="Email and password are required."
        )

    try:
        from db.queries import get_user_by_email
        user = get_user_by_email(email)
    except Exception as exc:
        raise db_unavailable(exc)

    invalid_credentials = HTTPException(
        status_code=401, detail="Invalid email or password."
    )

    if not user:
        raise invalid_credentials

    if not verify_password(password, user.get("password_hash", "")):
        raise invalid_credentials

    user_id = str(user["_id"])
    token = _issue_token(user_id, email, request)

    return AuthResponse(
        user=AuthUser(id=user_id, name=user.get("name", ""), email=email),
        token=token,
    )


@router.post("/auth/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, request: Request):
    email = (payload.email or "").strip().lower()
    password = payload.password or ""
    name = (payload.name or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="A valid email is required.")
    if not name:
        raise HTTPException(status_code=422, detail="Name is required.")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    try:
        from db.queries import email_exists, create_user
        if email_exists(email):
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

        user_id = create_user(email, name, hash_password(password))
        create_default_user_settings(ObjectId(user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise db_unavailable(exc)

    token = _issue_token(user_id, email, request)
    _send_verification(user_id, email)

    return AuthResponse(
        user=AuthUser(id=user_id, name=name, email=email),
        token=token,
    )

# ── AUTH-03 — Forgot Password ────────────────────────────────────────────────

@router.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required.")

    # Always the same message regardless of outcome — prevents account
    # enumeration via this endpoint, per the AUTH-03 spec.
    generic_response = {
        "message": "If an account exists for that email, we've sent password reset instructions."
    }

    try:
        from db.queries import get_user_by_email
        user = get_user_by_email(email)
    except Exception as exc:
        raise db_unavailable(exc)

    if user:
        token = create_reset_token(str(user["_id"]), email)
        reset_link = f"{FRONTEND_BASE_URL}/reset-password?token={token}"
        send_email(
            email,
            "Reset your AltInvest password",
            f"Someone asked to reset the password for this AltInvest account.\n\n"
            f"Reset it here (the link works for 30 minutes):\n{reset_link}\n\n"
            f"If that wasn't you, you can ignore this email.",
        )

    return generic_response


# ── AUTH-04 — Reset Password ─────────────────────────────────────────────────

@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    token_payload = decode_reset_token(payload.token)
    if not token_payload:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user_id = token_payload.get("sub")
    try:
        from db.queries import update_user
        updated = update_user(ObjectId(user_id), {"password_hash": hash_password(payload.new_password)})
    except Exception as exc:
        raise db_unavailable(exc)

    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")

    return {"message": "Password updated. You can now sign in with your new password."}


# ── AUTH-06 — Change password (signed in) ────────────────────────────────────

@router.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest, session: CurrentSession = Depends(get_current_session)):
    user_id = session.user_id
    new_password = payload.new_password or ""
    if len(new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters.")
    if new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="New password must be different from your current one.")

    from db.queries import get_user_by_id, update_user, delete_other_user_sessions
    try:
        user = get_user_by_id(str(user_id))
    except Exception as exc:
        raise db_unavailable(exc)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")

    # 400, not 401: a wrong current password must not look like an expired session to the client.
    if not verify_password(payload.current_password or "", user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    try:
        update_user(user_id, {
            "password_hash": hash_password(new_password),
            "password_changed_at": datetime.now(timezone.utc),
        })
        # Anyone signed in with the old password is signed out; this device stays in.
        signed_out = delete_other_user_sessions(user_id, session.session_id)
    except Exception as exc:
        raise db_unavailable(exc)

    return {"message": "Password updated.", "signed_out_sessions": signed_out}


# ── AUTH-05 — Email verification ─────────────────────────────────────────────

_RESEND_COOLDOWN = timedelta(seconds=60)


def _send_verification(user_id: str, email: str) -> bool:
    link = f"{FRONTEND_BASE_URL}/verify-email?token={create_verify_token(user_id, email)}"
    return send_email(
        email,
        "Confirm your AltInvest email",
        f"Confirm this email address for your AltInvest account:\n{link}\n\n"
        f"The link works for 24 hours. If you didn't create an account, you can ignore this email.",
    )


@router.post("/auth/resend-verification")
def resend_verification(user_id: ObjectId = Depends(get_current_user_id)):
    from db.queries import get_user_by_id, update_user
    try:
        user = get_user_by_id(str(user_id))
    except Exception as exc:
        raise db_unavailable(exc)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    if user.get("email_verified"):
        return {"message": "Your email is already verified.", "already_verified": True}

    last = user.get("verification_sent_at")
    now = datetime.now(timezone.utc)
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last < _RESEND_COOLDOWN:
            raise HTTPException(status_code=429, detail="A verification email was just sent. Try again in a minute.")

    sent = _send_verification(str(user_id), user["email"])
    try:
        update_user(user_id, {"verification_sent_at": now})
    except Exception as exc:
        raise db_unavailable(exc)

    if not sent and smtp_configured():
        raise HTTPException(status_code=502, detail="We couldn't send the verification email. Try again later.")
    return {
        "message": f"We've sent a verification link to {user['email']}." if sent
        else "Email sending isn't set up on this server, so the verification link was written to the server log.",
        "sent": sent,
    }


@router.post("/auth/verify-email")
def verify_email(payload: VerifyEmailRequest):
    data = decode_verify_token(payload.token)
    if not data:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")

    from db.queries import get_user_by_id, update_user
    try:
        user = get_user_by_id(data.get("sub"))
        # The link only counts for the address it was sent to.
        if not user or user.get("email") != data.get("email"):
            raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")
        update_user(user["_id"], {"email_verified": True, "email_verified_at": datetime.now(timezone.utc)})
    except HTTPException:
        raise
    except Exception as exc:
        raise db_unavailable(exc)

    return {"message": "Your email is verified."}


# ── AUTH-07 — Sessions ───────────────────────────────────────────────────────

_BROWSERS = (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"), ("Safari/", "Safari"))
_SYSTEMS = (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
            ("Mac OS X", "macOS"), ("CrOS", "ChromeOS"), ("Linux", "Linux"))


def _device_label(user_agent: str) -> str:
    """A short "Chrome on Windows" style label; good enough to tell sessions apart."""
    ua = user_agent or ""
    browser = next((name for marker, name in _BROWSERS if marker in ua), None)
    system = next((name for marker, name in _SYSTEMS if marker in ua), None)
    if browser and system:
        return f"{browser} on {system}"
    return browser or system or "Unknown device"


def _utc(dt: datetime) -> datetime:
    # PyMongo hands back naive datetimes; they are UTC.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


@router.get("/auth/sessions", response_model=list[SessionInfo])
def list_sessions(session: CurrentSession = Depends(get_current_session)):
    from db.queries import list_user_sessions
    try:
        rows = list_user_sessions(session.user_id)
    except Exception as exc:
        raise db_unavailable(exc)
    return [
        SessionInfo(
            id=str(row["_id"]),
            device=_device_label(row.get("user_agent", "")),
            ip=row.get("ip"),
            created_at=_utc(row["created_at"]),
            last_active=_utc(row.get("last_active") or row["created_at"]),
            current=row["_id"] == session.session_id,
        )
        for row in rows
    ]


@router.post("/auth/sessions/revoke-others")
def revoke_other_sessions(session: CurrentSession = Depends(get_current_session)):
    from db.queries import delete_other_user_sessions
    try:
        revoked = delete_other_user_sessions(session.user_id, session.session_id)
    except Exception as exc:
        raise db_unavailable(exc)
    return {"revoked": revoked}


@router.delete("/auth/sessions/{session_id}", status_code=204)
def revoke_session(session_id: str, session: CurrentSession = Depends(get_current_session)):
    try:
        target = ObjectId(session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found.")
    if target == session.session_id:
        raise HTTPException(status_code=400, detail="Use Log out to end this session.")

    from db.queries import delete_user_session
    try:
        deleted = delete_user_session(session.user_id, target)
    except Exception as exc:
        raise db_unavailable(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return Response(status_code=204)


@router.post("/auth/logout", status_code=204)
def logout(authorization: str | None = Header(None)):
    """Ends the caller's session. Always 204: a token that is already invalid has nothing to end,
    and a client logging out shouldn't be told its session expired."""
    payload = decode_access_token(authorization.split(" ", 1)[1]) if authorization and authorization.startswith("Bearer ") else None
    if payload:
        from db.queries import delete_user_session
        try:
            delete_user_session(ObjectId(payload["sub"]), ObjectId(payload["sid"]))
        except Exception as exc:
            # The token still lapses at its expiry; logging out locally shouldn't fail over this.
            log.warning("logout: couldn't delete session: %s", exc)
    return Response(status_code=204)
