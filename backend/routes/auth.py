"""
routes/auth.py

AUTH-01 — Login.
AUTH-02 — Signup.

POST /auth/login and POST /auth/signup check/write against the `users`
collection in the unified MongoDB database (db/mongo_connection.py) and
issue a JWT.

Forgot/reset password (AUTH-03/04) and email verification (AUTH-05) are
still intentionally NOT implemented — see AltInvest_Implementation_Checklist.md
Section 5.
"""
import os
import path_setup  # noqa: F401 — must be first, fixes sys.path

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models.schemas import (
    LoginRequest, AuthResponse, AuthUser, SignupRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from auth.security import (
    verify_password, create_access_token, hash_password,
    create_reset_token, decode_reset_token,
)
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
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the database right now: {exc}",
        )

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
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the database right now: {exc}",
        )

    token = create_access_token(user_id=user_id, email=email)

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
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the database right now: {exc}",
        )

    if user:
        token = create_reset_token(str(user["_id"]), email)
        reset_link = f"{FRONTEND_BASE_URL}/reset-password?token={token}"
        # TODO(deployment): send this via a real email provider instead of
        # logging it — see AltInvest_Implementation_Checklist.md Section 28.
        print(f"[auth] Password reset link for {email}: {reset_link}")

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
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the database right now: {exc}",
        )

    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")

    return {"message": "Password updated. You can now sign in with your new password."}