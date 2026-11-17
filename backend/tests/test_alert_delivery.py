"""Alert evaluation: an email is sent only to a verified address (G-34), on top of the Settings ->
Notifications rules (G-23); the in-app notification and the trigger row are written for everyone.
The database and the mailer are faked."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from controllers import alert_controller as ctl
import utils.mailer as mailer

USER = ObjectId()


class FakeColl:
    def __init__(self, docs=None):
        self.docs, self.inserts, self.updates = list(docs or []), [], []

    def find(self, flt=None, *a, **k):
        return list(self.docs)

    def find_one(self, flt, projection=None):
        return next((d for d in self.docs if d.get("_id") == flt.get("_id")), None)

    def insert_one(self, doc):
        self.inserts.append(doc)

    def update_one(self, flt, update, **k):
        self.updates.append((flt, update))

    def delete_one(self, flt):
        for d in self.docs:
            if d.get("_id") == flt.get("_id"):
                self.docs.remove(d)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)


def _alert(channel="email"):
    return {
        "_id": ObjectId(), "user_id": USER, "status": "active", "target_type": "crypto",
        "target_symbol": "BTC", "target_name": "Bitcoin", "metric_type": "price", "condition": "above",
        "threshold_value": 100.0, "last_observed_value": 90.0, "delivery_channel": channel,
    }


@pytest.fixture
def run(monkeypatch):
    """run(alert, user_doc, settings=None) -> (db, sent_emails). The price crosses 100 on this pass.
    `settings` is the user's notifications settings (None: nothing saved, so defaults apply)."""
    def _run(alert, user, settings=None):
        db = SimpleNamespace(
            alerts=FakeColl([alert]), alert_triggers=FakeColl(), notifications=FakeColl(),
            users=FakeColl([user] if user else []),
            user_settings=FakeColl(), pending_alert_emails=FakeColl(),
        )
        if settings is not None:
            # FakeColl.find_one matches on _id, which is what the settings lookup doesn't use, so serve it directly.
            db.user_settings.find_one = lambda flt, projection=None: {"notifications": settings}
        sent = []
        monkeypatch.setattr(ctl, "get_db", lambda: db)
        monkeypatch.setattr(ctl, "_current_values", lambda: {("crypto", "BTC", "price"): 110.0})
        monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append((to, subject)) or True)
        result = ctl.evaluate_alerts()
        assert result["triggered"] == 1
        return db, sent
    return _run


def test_verified_user_gets_the_email(run):
    db, sent = run(_alert("email"), {"_id": USER, "email": "a@x.com", "email_verified": True})
    assert [to for to, _ in sent] == ["a@x.com"]
    assert len(db.notifications.inserts) == 1 and len(db.alert_triggers.inserts) == 1


@pytest.mark.parametrize("flag", [False, None, "yes"])
def test_unverified_or_legacy_user_gets_no_email_but_still_the_in_app_alert(run, flag):
    user = {"_id": USER, "email": "a@x.com"}
    if flag is not None:
        user["email_verified"] = flag
    db, sent = run(_alert("email"), user)
    assert sent == []
    assert len(db.notifications.inserts) == 1 and len(db.alert_triggers.inserts) == 1


def test_missing_user_sends_nothing(run):
    db, sent = run(_alert("email"), None)
    assert sent == [] and len(db.notifications.inserts) == 1


@pytest.mark.parametrize("channel", ["in-app", "push"])
def test_non_email_alerts_never_send(run, channel):
    db, sent = run(_alert(channel), {"_id": USER, "email": "a@x.com", "email_verified": True})
    assert sent == [] and len(db.notifications.inserts) == 1


# ── together with the Settings -> Notifications rules ────────────────────────

VERIFIED = {"_id": USER, "email": "a@x.com", "email_verified": True}
UNVERIFIED = {"_id": USER, "email": "a@x.com", "email_verified": False}
# Quiet hours covering the whole day in UTC except one minute, so "now" is always inside them.
ALWAYS_QUIET = {"enabled": True, "start": "00:00", "end": "23:59", "timezone": "UTC"}


def test_email_off_in_settings_still_sends_nothing(run):
    db, sent = run(_alert("email"), VERIFIED, {"channels": {"email": False}})
    assert sent == [] and len(db.notifications.inserts) == 1


def test_a_verified_user_in_quiet_hours_has_the_email_held_not_sent(run):
    db, sent = run(_alert("email"), VERIFIED, {"quiet_hours": ALWAYS_QUIET})
    assert sent == []
    assert len(db.pending_alert_emails.inserts) == 1 and len(db.notifications.inserts) == 1


def test_an_unverified_user_in_quiet_hours_has_nothing_held_for_later(run):
    db, sent = run(_alert("email"), UNVERIFIED, {"quiet_hours": ALWAYS_QUIET})
    assert sent == [] and db.pending_alert_emails.inserts == []
    assert len(db.notifications.inserts) == 1


def test_a_held_email_is_sent_once_the_window_ends_only_to_a_verified_address(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append(to) or True)
    now = datetime.now(timezone.utc)
    row = {"_id": ObjectId(), "user_id": USER, "subject": "s", "body": "b", "send_after": now}

    for user, expected in ((VERIFIED, ["a@x.com"]), (UNVERIFIED, [])):
        sent.clear()
        db = SimpleNamespace(pending_alert_emails=FakeColl([dict(row)]), users=FakeColl([user]), user_settings=FakeColl())
        ctl._send_due_emails(db, now)
        assert sent == expected
        assert db.pending_alert_emails.docs == []        # the row is consumed either way
