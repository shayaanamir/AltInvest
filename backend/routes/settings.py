"""
routes/settings.py

GET the full settings document, PATCH one section at a time (preferences,
appearance, notifications, security, connected_accounts) — matches the
nested shape written by db/seed_user_data.py's user_settings doc.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user_id
from models.schemas import UserSettingsOut, SettingsSectionUpdate
from db.queries import get_user_settings, update_user_settings

router = APIRouter(tags=["Settings"])

_VALID_SECTIONS = {"preferences", "appearance", "notifications", "security", "connected_accounts"}


# ── GET /settings ─────────────────────────────────────────────────────────────

@router.get("/settings", response_model=UserSettingsOut)
def get_settings(user_id: ObjectId = Depends(get_current_user_id)):
    try:
        settings = get_user_settings(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found for this user.")

    return {**settings, "user_id": str(user_id)}


# ── PATCH /settings/{section} ────────────────────────────────────────────────

@router.patch("/settings/{section}", response_model=UserSettingsOut)
def patch_settings_section(
    section: str, payload: dict, user_id: ObjectId = Depends(get_current_user_id)
):
    if section not in _VALID_SECTIONS:
        raise HTTPException(status_code=422, detail=f"section must be one of {_VALID_SECTIONS}.")
    if not payload:
        raise HTTPException(status_code=422, detail="Payload cannot be empty.")

    try:
        update_user_settings(user_id, section, payload)
        settings = get_user_settings(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    return {**settings, "user_id": str(user_id)}