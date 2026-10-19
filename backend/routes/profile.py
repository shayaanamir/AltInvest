"""
routes/profile.py

GET/PATCH the current user's profile, including a computed activity
summary (holdings/watchlists/alerts counts) — not stored, assembled fresh
per request from the relevant collections.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from utils.http_errors import db_unavailable

from auth.dependencies import get_current_user_id
from models.schemas import ProfileOut, ProfileUpdate
from db.queries import get_user_by_id, update_user, get_activity_counts

router = APIRouter(tags=["Profile"])

_VALID_RISK_PROFILES = {"conservative", "balanced", "aggressive"}
_VALID_LAYOUTS = {"minimal", "analyst", "trader", "ai-first"}
# Same keys the onboarding goal step and the profile page offer.
_VALID_GOALS = {"longterm", "trading", "research", "discovery", "portfolio"}
_MAX_NAME = 80
_MAX_BIO = 500


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
        "investment_goal": user.get("investment_goal"),
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
        raise db_unavailable(exc)

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
    if "investment_goal" in update and update["investment_goal"] not in _VALID_GOALS:
        raise HTTPException(status_code=422, detail=f"investment_goal must be one of {sorted(_VALID_GOALS)}.")
    if "name" in update:
        update["name"] = update["name"].strip()
        if not update["name"]:
            raise HTTPException(status_code=422, detail="Name can't be empty.")
        if len(update["name"]) > _MAX_NAME:
            raise HTTPException(status_code=422, detail=f"Name must be {_MAX_NAME} characters or fewer.")
    if "bio" in update and len(update["bio"]) > _MAX_BIO:
        raise HTTPException(status_code=422, detail=f"Bio must be {_MAX_BIO} characters or fewer.")

    try:
        update_user(user_id, update)
        user = get_user_by_id(str(user_id))
    except Exception as exc:
        raise db_unavailable(exc)

    return _serialize_profile(user, user_id)