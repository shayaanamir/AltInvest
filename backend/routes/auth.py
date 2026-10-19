"""
routes/auth.py

AUTH-01 — Login.
AUTH-02 — Signup.

POST /auth/login and POST /auth/signup check/write against the `users`
collection in the unified MongoDB database (db/mongo_connection.py) and
issue a JWT.

AUTH-03/04 — Forgot / reset password.
AUTH-05 — Email verification: a link is emailed at signup and on request from the profile page.

Emails go out through utils/mailer.py (SMTP when configured, otherwise the link is logged).
"""
import os
import path_setup  # noqa: F401 — must be first, fixes sys.path

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from utils.http_errors import db_unavailable
from bson import ObjectId
from models.schemas import (
    LoginRequest, AuthResponse, AuthUser, SignupRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
)
from auth.security import (
    verify_password, create_access_token, hash_password,
    create_reset_token, decode_reset_token,
    create_verify_token, decode_verify_token,
)
from auth.dependencies import get_current_user_id
from utils.mailer import send_email, smtp_configured
from db.queries import create_default_user_settings

router = APIRouter(tags=["Auth"])

# Used to build the link embedded in the reset email. Override via env in
# any deployment where the frontend isn't on localhost:5173.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
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

    user_id = str(user.get("_id", email))
    token = create_access_token(user_id=user_id, email=email)

    return AuthResponse(
        user=AuthUser(id=user_id, name=user.get("name", ""), email=email),
        token=token,
    )


@router.post("/auth/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest):
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

    token = create_access_token(user_id=user_id, email=email)
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
