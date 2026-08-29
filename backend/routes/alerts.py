"""
routes/alerts.py

Alert CRUD. The background evaluator job that flips status -> "triggered"
and writes to notifications (per the schema doc) is a separate concern —
not implemented here, this route only covers user-facing CRUD.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import AlertOut, AlertCreate, AlertUpdate
from utils.serialization import serialize_dates
from db.queries import get_alerts, create_alert, update_alert, delete_alert, get_asset, get_nft_collection

router = APIRouter(tags=["Alerts"])

_VALID_METRIC_TYPES = {"price", "aai_score", "sentiment", "risk"}
_VALID_CONDITIONS = {"above", "below", "shifts_bearish", "shifts_bullish"}
_VALID_CHANNELS = {"push", "in-app", "email"}


# ── GET /alerts ───────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    status: str | None = Query(None, pattern="^(active|paused|triggered)$"),
    user_id: ObjectId = Depends(get_current_user_id),
):
    alerts = get_alerts(user_id, status=status)
    return [serialize_dates(a) for a in alerts]


# ── POST /alerts ─────────────────────────────────────────────────────────────

@router.post("/alerts", status_code=201)
def create_new_alert(payload: AlertCreate, user_id: ObjectId = Depends(get_current_user_id)):
    if payload.target_type not in ("crypto", "nft"):
        raise HTTPException(status_code=422, detail="target_type must be 'crypto' or 'nft'.")
    if payload.metric_type not in _VALID_METRIC_TYPES:
        raise HTTPException(status_code=422, detail=f"metric_type must be one of {_VALID_METRIC_TYPES}.")
    if payload.condition not in _VALID_CONDITIONS:
        raise HTTPException(status_code=422, detail=f"condition must be one of {_VALID_CONDITIONS}.")
    if payload.delivery_channel not in _VALID_CHANNELS:
        raise HTTPException(status_code=422, detail=f"delivery_channel must be one of {_VALID_CHANNELS}.")

    if payload.target_type == "crypto":
        if not payload.target_symbol:
            raise HTTPException(status_code=422, detail="target_symbol is required for crypto alerts.")
        if not get_asset(payload.target_symbol):
            raise HTTPException(status_code=404, detail=f"Asset '{payload.target_symbol}' not found.")
    else:
        if not payload.target_slug:
            raise HTTPException(status_code=422, detail="target_slug is required for nft alerts.")
        if not get_nft_collection(payload.target_slug):
            raise HTTPException(status_code=404, detail=f"NFT collection '{payload.target_slug}' not found.")

    # threshold_value required for numeric conditions, not for sentiment-shift conditions
    if payload.condition in ("above", "below") and payload.threshold_value is None:
        raise HTTPException(
            status_code=422,
            detail="threshold_value is required when condition is 'above' or 'below'.",
        )

    alert_id = create_alert(user_id, payload.model_dump(exclude_none=True))
    return {"id": alert_id}


# ── PATCH /alerts/{id} ───────────────────────────────────────────────────────

@router.patch("/alerts/{alert_id}")
def patch_alert(
    alert_id: str, payload: AlertUpdate, user_id: ObjectId = Depends(get_current_user_id)
):
    update = payload.model_dump(exclude_none=True)
    if not update:
        raise HTTPException(status_code=422, detail="No updatable fields provided.")

    if "status" in update and update["status"] not in ("active", "paused", "triggered"):
        raise HTTPException(status_code=422, detail="status must be 'active', 'paused', or 'triggered'.")
    if "condition" in update and update["condition"] not in _VALID_CONDITIONS:
        raise HTTPException(status_code=422, detail=f"condition must be one of {_VALID_CONDITIONS}.")
    if "delivery_channel" in update and update["delivery_channel"] not in _VALID_CHANNELS:
        raise HTTPException(status_code=422, detail=f"delivery_channel must be one of {_VALID_CHANNELS}.")

    try:
        updated = update_alert(user_id, alert_id, update)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid alert id.")

    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"status": "updated"}


# ── DELETE /alerts/{id} ──────────────────────────────────────────────────────

@router.delete("/alerts/{alert_id}", status_code=204)
def remove_alert(alert_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    try:
        deleted = delete_alert(user_id, alert_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid alert id.")

    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return None