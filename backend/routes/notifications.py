"""
routes/notifications.py

Read-only-ish: list notifications, mark one as read. Notifications
themselves are written by the (not-yet-built) alert evaluator job and by
system events — no POST/create route here on purpose.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import NotificationOut
from utils.serialization import serialize_dates
from db.queries import get_notifications, mark_notification_read

router = APIRouter(tags=["Notifications"])


# ── GET /notifications ───────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user_id: ObjectId = Depends(get_current_user_id),
):
    notifications = get_notifications(user_id, unread_only=unread_only, limit=limit)
    return [serialize_dates(n) for n in notifications]


# ── PATCH /notifications/{id}/read ──────────────────────────────────────────

@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    try:
        updated = mark_notification_read(user_id, notification_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid notification id.")

    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"status": "read"}