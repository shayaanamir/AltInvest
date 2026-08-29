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
import path_setup  # noqa: F401 — must be first, fixes sys.path

from fastapi import APIRouter, HTTPException
from bson import ObjectId
from models.schemas import LoginRequest, AuthResponse, AuthUser, SignupRequest
from auth.security import verify_password, create_access_token, hash_password
from db.queries import create_default_user_settings

router = APIRouter(tags=["Auth"])


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