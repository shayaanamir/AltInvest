"""
routes/profile.py

GET/PATCH the current user's profile, including a computed activity
summary (holdings/watchlists/alerts counts) — not stored, assembled fresh
per request from the relevant collections.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user_id
from models.schemas import ProfileOut, ProfileUpdate
from db.queries import get_user_by_id, update_user, get_activity_counts

router = APIRouter(tags=["Profile"])

_VALID_RISK_PROFILES = {"conservative", "balanced", "aggressive"}
_VALID_LAYOUTS = {"minimal", "analyst", "trader", "ai-first"}


def _serialize_profile(user: dict, user_id: ObjectId) -> dict:
    created_at = user.get("created_at")
    return {
        "id": str(user["_id"]),
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "avatar_initials": user.get("avatar_initials"),
        "avatar_color": user.get("avatar_color"),
        "bio": user.get("bio"),
        "risk_profile": user.get("risk_profile"),
        "layout_preference": user.get("layout_preference"),
        "display_currency": user.get("display_currency"),
        "email_verified": user.get("email_verified"),
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(created_at, "strftime") else created_at,
        "activity_summary": get_activity_counts(user_id),
    }


# ── GET /profile ─────────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileOut)
def get_profile(user_id: ObjectId = Depends(get_current_user_id)):
    try:
        user = get_user_by_id(str(user_id))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return _serialize_profile(user, user_id)


# ── PATCH /profile ───────────────────────────────────────────────────────────

@router.patch("/profile", response_model=ProfileOut)
def patch_profile(payload: ProfileUpdate, user_id: ObjectId = Depends(get_current_user_id)):
    update = payload.model_dump(exclude_none=True)
    if not update:
        raise HTTPException(status_code=422, detail="No updatable fields provided.")

    if "risk_profile" in update and update["risk_profile"] not in _VALID_RISK_PROFILES:
        raise HTTPException(status_code=422, detail=f"risk_profile must be one of {_VALID_RISK_PROFILES}.")
    if "layout_preference" in update and update["layout_preference"] not in _VALID_LAYOUTS:
        raise HTTPException(status_code=422, detail=f"layout_preference must be one of {_VALID_LAYOUTS}.")
    if "name" in update and not update["name"].strip():
        raise HTTPException(status_code=422, detail="name cannot be empty.")

    try:
        update_user(user_id, update)
        user = get_user_by_id(str(user_id))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    return _serialize_profile(user, user_id)