"""
routes/notifications.py

List (paged, filterable), unread count, mark one / all as read, dismiss. Notifications are
written by the alert evaluator (controllers/alert_controller.py) and system events, so there is
no create route on purpose.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from utils.http_errors import require_object_id
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import NotificationOut
from utils.serialization import serialize_dates
from db.queries import (
    get_notifications, mark_notification_read, count_unread_notifications,
    mark_all_notifications_read, delete_notification,
)

router = APIRouter(tags=["Notifications"])


# ── GET /notifications ───────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type: list[str] | None = Query(None, description="Only these types (repeatable)"),
    user_id: ObjectId = Depends(get_current_user_id),
):
    notifications = get_notifications(user_id, unread_only=unread_only, limit=limit, skip=offset, types=type)
    return [serialize_dates(n) for n in notifications]


# ── GET /notifications/unread-count ─────────────────────────────────────────

@router.get("/notifications/unread-count")
def unread_count(user_id: ObjectId = Depends(get_current_user_id)):
    return {"count": count_unread_notifications(user_id)}


# ── POST /notifications/read-all ────────────────────────────────────────────

@router.post("/notifications/read-all")
def read_all(user_id: ObjectId = Depends(get_current_user_id)):
    return {"updated": mark_all_notifications_read(user_id)}


# ── DELETE /notifications/{id} ──────────────────────────────────────────────

@router.delete("/notifications/{notification_id}", status_code=204)
def dismiss(notification_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    require_object_id(notification_id, "notification")
    if not delete_notification(user_id, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found.")
    return None


# ── PATCH /notifications/{id}/read ──────────────────────────────────────────

@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    require_object_id(notification_id, "notification")
    updated = mark_notification_read(user_id, notification_id)

    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"status": "read"}