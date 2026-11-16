"""Alert evaluation: an email is sent only to a verified address (G-34); the in-app notification
and the trigger row are written for everyone. The database and the mailer are faked."""
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


def _alert(channel="email"):
    return {
        "_id": ObjectId(), "user_id": USER, "status": "active", "target_type": "crypto",
        "target_symbol": "BTC", "target_name": "Bitcoin", "metric_type": "price", "condition": "above",
        "threshold_value": 100.0, "last_observed_value": 90.0, "delivery_channel": channel,
    }


@pytest.fixture
def run(monkeypatch):
    """run(alert, user_doc) -> (db, sent_emails). The price crosses 100 on this pass."""
    def _run(alert, user):
        db = SimpleNamespace(
            alerts=FakeColl([alert]), alert_triggers=FakeColl(), notifications=FakeColl(),
            users=FakeColl([user] if user else []),
        )
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
