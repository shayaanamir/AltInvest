"""
routes/auth.py

AUTH-01 — Login.

POST /auth/login checks credentials against the `users` collection in
the unified MongoDB database (db/mongo_connection.py) and issues a JWT.

Signup (AUTH-02), forgot/reset password (AUTH-03/04), and email
verification (AUTH-05) are intentionally NOT implemented here — see
AltInvest_Implementation_Checklist.md Section 5. Until AUTH-02 exists,
use db/seed_users.py to create a test account.
"""
import path_setup  # noqa: F401 — must be first, fixes sys.path

from fastapi import APIRouter, HTTPException

from models.schemas import LoginRequest, AuthResponse, AuthUser
from auth.security import verify_password, create_access_token

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
        # Distinct from "wrong credentials" so the frontend/ops can tell
        # a DB outage apart from a bad login attempt.
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the database right now: {exc}",
        )

    # Same generic message for "no such user" and "wrong password" —
    # avoids leaking which emails are registered.
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