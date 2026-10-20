"""
routes/alerts.py

Alert CRUD and trigger history. Rule validation and the evaluator that sets status to
"triggered" (and writes notifications + trigger history) live in controllers/alert_controller.py.
"""
import path_setup  # noqa: F401

from bson import ObjectId
from utils.http_errors import require_object_id
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import AlertOut, AlertCreate, AlertUpdate
from utils.serialization import serialize_dates
from db.queries import get_alerts, create_alert, update_alert, delete_alert
from controllers.alert_controller import validate_rule, list_triggers, owned_alert

router = APIRouter(tags=["Alerts"])

_RULE_FIELDS = ("target_type", "target_symbol", "target_slug", "target_name", "metric_type",
                "condition", "threshold_value", "delivery_channel")


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
    rule = validate_rule(payload.model_dump())
    alert_id = create_alert(user_id, {k: v for k, v in rule.items() if v is not None})
    return {"id": alert_id}


# ── PATCH /alerts/{id} ───────────────────────────────────────────────────────

@router.patch("/alerts/{alert_id}")
def patch_alert(
    alert_id: str, payload: AlertUpdate, user_id: ObjectId = Depends(get_current_user_id)
):
    update = payload.model_dump(exclude_unset=True)
    if not update:
        raise HTTPException(status_code=422, detail="No updatable fields provided.")
    if "status" in update and update["status"] not in ("active", "paused"):
        raise HTTPException(status_code=422, detail="status can be set to 'active' or 'paused'; alerts become 'triggered' on their own.")

    require_object_id(alert_id, "alert")
    current = owned_alert(user_id, alert_id)

    changes = {}
    rule_changed = any(f in update for f in _RULE_FIELDS)
    if rule_changed:
        # Switching target type clears the other kind's identifier.
        if update.get("target_type") == "crypto":
            update.setdefault("target_slug", None)
        if update.get("target_type") == "nft":
            update.setdefault("target_symbol", None)
        merged = validate_rule({**{f: current.get(f) for f in _RULE_FIELDS}, **{k: v for k, v in update.items() if k in _RULE_FIELDS}})
        changes.update({f: merged.get(f) for f in _RULE_FIELDS})
        # A changed rule starts fresh: re-armed, and the next check takes a new baseline.
        changes.update({"last_observed_value": None, "status": update.get("status", "active")})
    if "status" in update:
        changes["status"] = update["status"]
        if update["status"] == "active" and current.get("status") == "triggered":
            changes["last_observed_value"] = None   # re-armed: watch for the next crossing from now

    update_alert(user_id, alert_id, changes)
    return {"status": "updated", "alert_status": changes.get("status", current.get("status"))}


# ── Trigger history ──────────────────────────────────────────────────────────

@router.get("/alerts/triggers")
def recent_triggers(limit: int = Query(50, ge=1, le=200), user_id: ObjectId = Depends(get_current_user_id)):
    return list_triggers(user_id, limit=limit)


@router.get("/alerts/{alert_id}/triggers")
def alert_triggers(alert_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    require_object_id(alert_id, "alert")
    owned_alert(user_id, alert_id)
    return list_triggers(user_id, alert_id)


# ── DELETE /alerts/{id} ──────────────────────────────────────────────────────

@router.delete("/alerts/{alert_id}", status_code=204)
def remove_alert(alert_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    require_object_id(alert_id, "alert")
    deleted = delete_alert(user_id, alert_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return None