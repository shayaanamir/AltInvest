"""
routes/settings.py

GET the full settings document, PATCH one section at a time (preferences,
appearance, notifications, security, connected_accounts) — matches the
nested shape written by db/seed_user_data.py's user_settings doc.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from utils.http_errors import db_unavailable

from auth.dependencies import get_current_user_id
from models.schemas import (
    UserSettingsOut,
    PreferencesPatch,
    AppearancePatch,
    NotificationsPatch,
    SecurityPatch,
    ConnectedAccountsPatch,
)
from db.queries import get_user_settings, update_user_settings
from controllers.fx_controller import SUPPORTED_CURRENCIES

router = APIRouter(tags=["Settings"])

_VALID_SECTIONS = {"preferences", "appearance", "notifications", "security", "connected_accounts"}


# ── GET /settings ─────────────────────────────────────────────────────────────

@router.get("/settings", response_model=UserSettingsOut)
def get_settings(user_id: ObjectId = Depends(get_current_user_id)):
    try:
        settings = get_user_settings(user_id)
    except Exception as exc:
        raise db_unavailable(exc)

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found for this user.")

    return {**settings, "user_id": str(user_id)}


# ── PATCH /settings/{section} ────────────────────────────────────────────────
# One route per section, each with its own typed body (see the *Patch models in
# models/schemas.py), so only known keys with valid values ever reach the database.

def _flatten(updates: dict, prefix: str = "") -> dict:
    """{"channels": {"push": False}} -> {"channels.push": False}, so a partial nested update
    changes just that key instead of replacing the whole nested object."""
    out = {}
    for key, value in updates.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, f"{path}."))
        else:
            out[path] = value
    return out


def _save_section(section: str, body, user_id: ObjectId) -> dict:
    updates = _flatten(body.model_dump(exclude_none=True))
    if not updates:
        raise HTTPException(status_code=422, detail="Payload cannot be empty.")
    try:
        update_user_settings(user_id, section, updates)
        settings = get_user_settings(user_id)
    except Exception as exc:
        raise db_unavailable(exc)
    return {**settings, "user_id": str(user_id)}


@router.patch("/settings/preferences", response_model=UserSettingsOut)
def patch_preferences(payload: PreferencesPatch, user_id: ObjectId = Depends(get_current_user_id)):
    if payload.display_currency is not None and payload.display_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=422, detail=f"display_currency must be one of {SUPPORTED_CURRENCIES}.")
    return _save_section("preferences", payload, user_id)


@router.patch("/settings/appearance", response_model=UserSettingsOut)
def patch_appearance(payload: AppearancePatch, user_id: ObjectId = Depends(get_current_user_id)):
    return _save_section("appearance", payload, user_id)


@router.patch("/settings/notifications", response_model=UserSettingsOut)
def patch_notifications(payload: NotificationsPatch, user_id: ObjectId = Depends(get_current_user_id)):
    return _save_section("notifications", payload, user_id)


@router.patch("/settings/security", response_model=UserSettingsOut)
def patch_security(payload: SecurityPatch, user_id: ObjectId = Depends(get_current_user_id)):
    return _save_section("security", payload, user_id)


@router.patch("/settings/connected_accounts", response_model=UserSettingsOut)
def patch_connected_accounts(payload: ConnectedAccountsPatch, user_id: ObjectId = Depends(get_current_user_id)):
    return _save_section("connected_accounts", payload, user_id)


@router.patch("/settings/{section}")
def patch_unknown_settings_section(section: str):
    """Any other section name. Declared last so it only catches names the routes above don't."""
    raise HTTPException(status_code=422, detail=f"section must be one of {sorted(_VALID_SECTIONS)}.")
