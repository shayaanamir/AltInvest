"""
routes/profile.py

GET/PATCH the current user's profile, including a computed activity
summary (holdings/watchlists/alerts counts) — not stored, assembled fresh
per request from the relevant collections.
"""
import path_setup  # noqa: F401

import logging
import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from utils.http_errors import db_unavailable

from auth.dependencies import get_current_user_id
from models.schemas import OnboardingIn, ProfileOut, ProfileUpdate
from db.queries import (
    get_user_by_id, update_user, get_activity_counts, set_onboarding_if_open, update_user_settings,
    get_assets_by_id, get_nft_collections_by_slug, create_watchlist, watchlist_name_taken,
)

log = logging.getLogger("profile")
router = APIRouter(tags=["Profile"])

_VALID_RISK_PROFILES = {"conservative", "balanced", "aggressive"}
# The home focus: which dashboard widgets show, and which page the user lands on. The keys and the
# landing pages must match frontend/src/utils/homeFocus.js (a frontend test reads this file to check).
FOCUS_LANDING = {"everything": "Dashboard", "portfolio": "Portfolio", "markets": "Discover", "sentiment": "Sentiment"}
_VALID_FOCUS = set(FOCUS_LANDING)
# Same keys the onboarding goal step and the profile page offer.
_VALID_GOALS = {"longterm", "trading", "research", "discovery", "portfolio"}
# The markets AltInvest covers ("nfts" in onboarding; Discover's own key is "nft").
_VALID_MARKETS = {"crypto", "nfts"}
_SYMBOL = re.compile(r"^[A-Za-z0-9]{1,15}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
STARTER_WATCHLIST_NAME = "My Watchlist"
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
        "markets_followed": list(((user.get("onboarding") or {}).get("answers") or {}).get("markets") or []),
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
    if "layout_preference" in update and update["layout_preference"] not in _VALID_FOCUS:
        raise HTTPException(status_code=422, detail=f"layout_preference must be one of {sorted(_VALID_FOCUS)}.")
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

# ── PUT /profile/onboarding ──────────────────────────────────────────────────

def risk_profile_from_score(score: float) -> str:
    """The slider's buckets (frontend Step2RiskStyle.getProfile): up to 25, up to 65, above."""
    if score <= 25:
        return "conservative"
    return "balanced" if score <= 65 else "aggressive"


def _clean_onboarding_answers(a) -> dict:
    """Validated, normalised answers. Unknown choices are an error, not silently stored."""
    bad = [m for m in a.markets if m not in _VALID_MARKETS]
    if bad:
        raise HTTPException(status_code=422, detail=f"markets must be from {sorted(_VALID_MARKETS)}.")
    bad = [g for g in a.goals if g not in _VALID_GOALS]
    if bad:
        raise HTTPException(status_code=422, detail=f"goals must be from {sorted(_VALID_GOALS)}.")
    if a.focus is not None and a.focus not in _VALID_FOCUS:
        raise HTTPException(status_code=422, detail=f"focus must be one of {sorted(_VALID_FOCUS)}.")
    if any(not _SYMBOL.match(s) for s in a.assets):
        raise HTTPException(status_code=422, detail="assets must be coin symbols such as BTC.")
    if any(not _SLUG.match(s) for s in a.nfts):
        raise HTTPException(status_code=422, detail="nfts must be collection slugs such as azuki.")
    return {
        "markets": list(dict.fromkeys(a.markets)),
        "risk": int(round(a.risk)) if a.risk is not None else None,
        "goals": list(dict.fromkeys(a.goals)),
        "assets": list(dict.fromkeys(s.upper() for s in a.assets)),
        "nfts": list(dict.fromkeys(a.nfts)),
        "focus": a.focus,
        "density": a.density,
        "theme": a.theme,
    }


@router.put("/profile/onboarding", response_model=ProfileOut)
def save_onboarding(payload: OnboardingIn, user_id: ObjectId = Depends(get_current_user_id)):
    """
    Saves the onboarding answers (or records a skip). Finishing also fills the profile from them
    (risk profile, first goal, home focus), sets the home focus and the page to land on, the density
    and the theme, and creates a starter watchlist from the coins and NFT collections picked. Once
    onboarding is completed this changes nothing, so a double submit, or a second tab, is harmless.
    """
    now = datetime.now(timezone.utc)
    skipped = payload.skipped
    answers = {} if skipped else _clean_onboarding_answers(payload.answers)
    onboarding = {"completed": not skipped, "completed_at": None if skipped else now,
                  "skipped": skipped, "answers": answers}

    derived = {}
    if not skipped:
        if answers["risk"] is not None:
            derived["risk_profile"] = risk_profile_from_score(answers["risk"])
        if answers["goals"]:
            derived["investment_goal"] = answers["goals"][0]
        if answers["focus"]:
            derived["layout_preference"] = answers["focus"]

    try:
        if not get_user_by_id(str(user_id)):
            raise HTTPException(status_code=404, detail="User not found.")
        won = set_onboarding_if_open(user_id, onboarding, derived)
        if won and not skipped:
            _apply_onboarding_side_effects(user_id, answers)
        user = get_user_by_id(str(user_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise db_unavailable(exc)
    return _serialize_profile(user, user_id)


def _apply_onboarding_side_effects(user_id: ObjectId, answers: dict) -> None:
    """Follow-up work after onboarding was recorded. Best effort: a failure here is logged and doesn't
    undo the saved answers (the profile fields are already written with them)."""
    try:
        prefs = {}
        if answers["focus"]:
            prefs["default_dashboard_layout"] = answers["focus"]
            prefs["default_landing_page"] = FOCUS_LANDING[answers["focus"]]
        if prefs:
            update_user_settings(user_id, "preferences", prefs)
        look = {k: answers[k] for k in ("theme", "density") if answers[k]}
        if look:
            update_user_settings(user_id, "appearance", look)
    except Exception as exc:
        log.warning("[onboarding] display settings not saved: %s", type(exc).__name__)
    try:
        coins = get_assets_by_id(answers["assets"])
        collections = get_nft_collections_by_slug(answers["nfts"])
        items = ([("crypto", s) for s in answers["assets"] if s in coins]
                 + [("nft", s) for s in answers["nfts"] if s in collections])
        if items and not watchlist_name_taken(user_id, STARTER_WATCHLIST_NAME):
            create_watchlist(user_id, STARTER_WATCHLIST_NAME, items)
    except Exception as exc:
        log.warning("[onboarding] starter watchlist not created: %s", type(exc).__name__)
