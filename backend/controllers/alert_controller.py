"""
backend/controllers/alert_controller.py

Alert rules: what a valid rule is, and the background job that checks them.

Which metrics exist for which targets, and which conditions each metric takes:
  crypto: price (USD), aai_score (0-100), risk (0-100), sentiment (-1..1)
  nft:    price (floor, USD), aai_score (0-100)    -- there is no NFT sentiment or risk score
  above / below           any metric, with a threshold in that metric's range
  shifts_bullish/bearish  sentiment only, no threshold (crossing +0.15 / -0.15, the dashboard's mood cut-offs)

Evaluation (every 5 minutes): conditions fire on a *crossing*. The first check of a rule just
records the current value; it triggers when a later value crosses the line (e.g. was <= 80,000,
now > 80,000). A triggered alert stops being checked until the user re-arms it. Each trigger is
written to `alert_triggers` (the alert's history) and to `notifications`, and emailed when the
alert's channel is email.
"""
import time
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from db.mongo_connection import get_db

log = logging.getLogger("alerts")

EVAL_SECONDS = 5 * 60
BULLISH_ABOVE, BEARISH_BELOW = 0.15, -0.15

METRICS_BY_TARGET = {"crypto": {"price", "aai_score", "risk", "sentiment"}, "nft": {"price", "aai_score"}}
CONDITIONS_BY_METRIC = {
    "price": {"above", "below"},
    "aai_score": {"above", "below"},
    "risk": {"above", "below"},
    "sentiment": {"above", "below", "shifts_bullish", "shifts_bearish"},
}
RANGES = {"price": (0, None), "aai_score": (0, 100), "risk": (0, 100), "sentiment": (-1, 1)}
CHANNELS = {"in-app", "push", "email"}
METRIC_LABELS = {"price": "price", "aai_score": "AAI score", "risk": "risk score", "sentiment": "sentiment"}


def _bad(msg):
    raise HTTPException(status_code=422, detail=msg)


def validate_rule(rule: dict) -> dict:
    """Checks a complete rule (target, metric, condition, threshold, channel) and normalises the target."""
    from db.queries import get_asset, get_nft_collection

    t = rule.get("target_type")
    if t not in METRICS_BY_TARGET:
        _bad("target_type must be 'crypto' or 'nft'.")
    if t == "crypto":
        sym = (rule.get("target_symbol") or "").strip().upper()
        if not sym:
            _bad("target_symbol is required for crypto alerts.")
        if not get_asset(sym):
            raise HTTPException(status_code=404, detail=f"Asset '{sym}' not found.")
        rule["target_symbol"], rule["target_slug"] = sym, None
    else:
        slug = (rule.get("target_slug") or "").strip().lower()
        if not slug:
            _bad("target_slug is required for nft alerts.")
        if not get_nft_collection(slug):
            raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")
        rule["target_slug"], rule["target_symbol"] = slug, None

    metric, cond = rule.get("metric_type"), rule.get("condition")
    if metric not in METRICS_BY_TARGET[t]:
        _bad(f"{'NFT collections' if t == 'nft' else 'Crypto assets'} can't have a {METRIC_LABELS.get(metric, metric)} alert. "
             f"Use one of: {', '.join(sorted(METRICS_BY_TARGET[t]))}.")
    if cond not in CONDITIONS_BY_METRIC[metric]:
        _bad(f"'{cond}' doesn't apply to {METRIC_LABELS[metric]}. Use one of: {', '.join(sorted(CONDITIONS_BY_METRIC[metric]))}.")

    if cond in ("above", "below"):
        v = rule.get("threshold_value")
        if v is None:
            _bad("threshold_value is required for 'above' and 'below'.")
        lo, hi = RANGES[metric]
        if (lo is not None and v < lo) or (hi is not None and v > hi) or (metric == "price" and v <= 0):
            span = "greater than 0" if metric == "price" else f"between {lo} and {hi}"
            _bad(f"A {METRIC_LABELS[metric]} threshold must be {span}.")
    else:
        rule["threshold_value"] = None

    if rule.get("delivery_channel", "in-app") not in CHANNELS:
        _bad(f"delivery_channel must be one of {sorted(CHANNELS)}.")
    if not (rule.get("target_name") or "").strip():
        _bad("target_name is required.")
    return rule


# ── evaluation ───────────────────────────────────────────────────────────────

def _current_values() -> dict:
    """{(target_type, id, metric): value} for everything an alert can watch, in a handful of queries."""
    from db.queries import (
        get_asset_market_data_all_latest, get_nft_market_data_all_latest,
        get_all_latest_aai_scores, get_all_latest_risk_scores,
    )
    from controllers.market_controller import live_sentiment_by_symbol

    values = {}
    for m in get_asset_market_data_all_latest():
        values[("crypto", m["asset_id"], "price")] = m.get("price")
    for m in get_nft_market_data_all_latest():
        values[("nft", m["slug"], "price")] = m.get("floor_usd")
    for t in ("crypto", "nft"):
        for k, a in get_all_latest_aai_scores(t).items():
            values[(t, k, "aai_score")] = a.get("aai_score")
            if t == "crypto" and a.get("sentiment_score") is not None:
                values[("crypto", k, "sentiment")] = a["sentiment_score"]
    for k, r in get_all_latest_risk_scores().items():
        values[("crypto", k, "risk")] = r.get("risk_score")
    for k, s in live_sentiment_by_symbol().items():   # live reading beats the stored one
        values[("crypto", k, "sentiment")] = s["score"]
    return values


def crossed(condition: str, threshold, prev, now) -> bool:
    if prev is None or now is None:
        return False
    if condition == "above":
        return prev <= threshold < now
    if condition == "below":
        return prev >= threshold > now
    if condition == "shifts_bullish":
        return prev <= BULLISH_ABOVE < now
    if condition == "shifts_bearish":
        return prev >= BEARISH_BELOW > now
    return False


def _fmt(metric, v):
    if v is None:
        return "—"
    return f"${v:,.2f}" if metric == "price" else (f"{v:+.2f}" if metric == "sentiment" else f"{v:g}")


def _message(a: dict, value) -> tuple[str, str]:
    name, metric, cond = a.get("target_name"), METRIC_LABELS[a["metric_type"]], a["condition"]
    if cond in ("above", "below"):
        title = f"{name} {metric} {'rose above' if cond == 'above' else 'fell below'} {_fmt(a['metric_type'], a['threshold_value'])}"
    else:
        title = f"{name} sentiment turned {'bullish' if cond == 'shifts_bullish' else 'bearish'}"
    return title, f"{name}'s {metric} is now {_fmt(a['metric_type'], value)}."


def evaluate_alerts() -> dict:
    """One pass over every active alert. Returns {"checked": n, "triggered": n}."""
    db = get_db()
    values = _current_values()
    now = datetime.now(timezone.utc)
    checked = triggered = 0
    for a in db.alerts.find({"status": "active"}):
        key_id = a.get("target_symbol") if a.get("target_type") == "crypto" else a.get("target_slug")
        value = values.get((a.get("target_type"), key_id, a.get("metric_type")))
        checked += 1
        if value is None:
            db.alerts.update_one({"_id": a["_id"]}, {"$set": {"last_checked_at": now}})
            continue
        fire = crossed(a.get("condition"), a.get("threshold_value"), a.get("last_observed_value"), value)
        update = {"last_observed_value": value, "last_checked_at": now}
        if fire:
            title, message = _message(a, value)
            update.update({"status": "triggered", "last_triggered_at": now})
            db.alert_triggers.insert_one({
                "alert_id": str(a["_id"]), "user_id": a["user_id"], "triggered_at": now,
                "value": value, "previous_value": a.get("last_observed_value"),
                "condition": a["condition"], "threshold_value": a.get("threshold_value"),
                "metric_type": a["metric_type"], "message": title,
            })
            db.notifications.insert_one({
                "user_id": a["user_id"], "type": "alert_triggered", "title": title, "message": message,
                "read": False, "timestamp": now,
                "deep_link": {"page": "AssetDetail", "symbol": a.get("target_symbol"), "slug": None}
                if a.get("target_type") == "crypto" else {"page": "Discover", "symbol": None, "slug": a.get("target_slug")},
            })
            if a.get("delivery_channel") == "email":
                user = db.users.find_one({"_id": a["user_id"]}, {"email": 1})
                if user and user.get("email"):
                    from utils.mailer import send_email
                    send_email(user["email"], f"AltInvest alert: {title}", f"{message}\n\nThe alert is paused until you re-arm it on the Alerts page.")
            triggered += 1
        db.alerts.update_one({"_id": a["_id"]}, {"$set": update})
    return {"checked": checked, "triggered": triggered}


def run_alert_scheduler(initial_delay_seconds: int = 60) -> None:
    """Daemon-thread loop: every 5 minutes. Never raises."""
    time.sleep(initial_delay_seconds)
    while True:
        try:
            result = evaluate_alerts()
            if result["triggered"]:
                log.info("[alerts] %s", result)
        except Exception as exc:
            from utils.http_errors import redact
            log.error("[alerts] evaluation failed: %s: %s", type(exc).__name__, redact(exc))
        time.sleep(EVAL_SECONDS)


def list_triggers(user_id, alert_id: str | None = None, limit: int = 50) -> list:
    query = {"user_id": user_id}
    if alert_id:
        query["alert_id"] = alert_id
    out = []
    for t in get_db().alert_triggers.find(query, sort=[("triggered_at", -1)], limit=limit):
        t["id"] = str(t.pop("_id"))
        t.pop("user_id", None)
        if hasattr(t.get("triggered_at"), "strftime"):
            t["triggered_at"] = t["triggered_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(t)
    return out


def owned_alert(user_id, alert_id: str) -> dict:
    a = get_db().alerts.find_one({"_id": ObjectId(alert_id), "user_id": user_id})
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return a
