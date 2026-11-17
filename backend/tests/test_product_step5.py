"""
Audit 2026-11-16, Step 5 product gaps:
  G-15  no account enumeration: login always runs bcrypt; signup answers the same for new and
        existing emails; account emails go out in the background
  G-49  GET /account/export returns everything stored for the user
  G-23  Settings → Notifications is honoured: Email off means no alert email, quiet hours hold it
No database is needed: Mongo is replaced with small in-memory fakes.
"""
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from auth import rate_limit as rl
from auth import security
from auth.dependencies import get_current_user_id
from controllers import alert_controller as ac
from routes import auth as auth_routes

PASSWORD = "correct-horse-1"


# ── tiny in-memory Mongo ─────────────────────────────────────────────────────

def _matches(doc, query):
    for key, cond in query.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$lte" in cond and not (value is not None and value <= cond["$lte"]):
                return False
            if "$ne" in cond and value == cond["$ne"]:
                return False
        elif value != cond:
            return False
    return True


class _Result:
    def __init__(self, n=0, inserted_id=None):
        self.deleted_count = self.modified_count = self.matched_count = n
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self.rows = []

    def find(self, query=None, projection=None, **_):
        return [dict(r) for r in self.rows if _matches(r, query or {})]

    def find_one(self, query=None, projection=None, **_):
        found = self.find(query)
        return found[0] if found else None

    def insert_one(self, doc):
        doc = {"_id": ObjectId(), **doc}
        self.rows.append(doc)
        return _Result(1, doc["_id"])

    def update_one(self, query, update, **_):
        for r in self.rows:
            if _matches(r, query):
                r.update(update.get("$set", {}))
                return _Result(1)
        return _Result(0)

    def delete_one(self, query):
        for r in self.rows:
            if _matches(r, query):
                self.rows.remove(r)
                return _Result(1)
        return _Result(0)


class FakeDB(dict):
    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]

    __getattr__ = dict.__getitem__


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    for name in ("hit", "check", "record", "clear"):
        monkeypatch.setattr(rl, name, lambda *a, **k: None)


# ── G-15: login ──────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(monkeypatch):
    users = {}
    monkeypatch.setattr(queries, "get_user_by_email", lambda e: users.get(e))
    app = FastAPI()
    app.include_router(auth_routes.router)
    return TestClient(app), users


def _count_bcrypt(monkeypatch):
    calls = []
    real = auth_routes.verify_password
    monkeypatch.setattr(auth_routes, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    return calls


@pytest.mark.parametrize("account", ["none", "google_only", "wrong_password"])
def test_login_always_runs_one_bcrypt_check(auth_client, monkeypatch, account):
    client, users = auth_client
    if account == "google_only":
        users["ada@example.com"] = {"_id": ObjectId(), "email": "ada@example.com", "password_hash": None}
    elif account == "wrong_password":
        users["ada@example.com"] = {"_id": ObjectId(), "email": "ada@example.com",
                                    "password_hash": security.hash_password("something-else-1")}
    calls = _count_bcrypt(monkeypatch)
    r = client.post("/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."
    assert len(calls) == 1 and calls[0]   # a real hash, never an empty one that returns at once


def test_unverified_signup_account_cannot_sign_in(auth_client, monkeypatch):
    client, users = auth_client
    uid = ObjectId()
    users["ada@example.com"] = {"_id": uid, "email": "ada@example.com", "password_hash": security.hash_password(PASSWORD),
                                "email_verification_required": True, "email_verified": False}
    sent = []
    monkeypatch.setattr(auth_routes, "_send_verification", lambda u, e: sent.append(e) or True)
    monkeypatch.setattr(auth_routes, "_mark_verification_sent", lambda u: None)
    monkeypatch.setattr(auth_routes, "_issue_token", lambda *a: pytest.fail("no session before verification"))
    r = client.post("/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 403
    assert sent == ["ada@example.com"]


def test_older_unverified_accounts_still_sign_in(auth_client, monkeypatch):
    client, users = auth_client
    users["ada@example.com"] = {"_id": ObjectId(), "email": "ada@example.com", "name": "Ada",
                                "password_hash": security.hash_password(PASSWORD), "email_verified": False}
    monkeypatch.setattr(auth_routes, "_issue_token", lambda *a: "tok")
    r = client.post("/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token"] == "tok"


# ── G-15: signup ─────────────────────────────────────────────────────────────

@pytest.fixture
def signup_env(auth_client, monkeypatch):
    client, users = auth_client
    emails = []

    def create_user(email, name, password_hash, **kw):
        uid = ObjectId()
        users[email] = {"_id": uid, "email": email, "name": name, "password_hash": password_hash,
                        **(kw.get("extra") or {})}
        return str(uid)

    monkeypatch.setattr(queries, "create_user", create_user)
    monkeypatch.setattr(auth_routes, "create_default_user_settings", lambda u: None)
    monkeypatch.setattr(auth_routes, "_mark_verification_sent", lambda u: None)
    monkeypatch.setattr(auth_routes, "_send_verification", lambda u, e: emails.append(("verify", e)) or True)
    monkeypatch.setattr(auth_routes, "_send_account_exists", lambda e: emails.append(("exists", e)) or True)
    return client, users, emails


def _signup(client, email="ada@example.com", password=PASSWORD):
    return client.post("/auth/signup", json={"name": "Ada", "email": email, "password": password})


def test_signup_answers_the_same_for_new_and_existing_emails(signup_env):
    client, users, emails = signup_env
    first = _signup(client)
    second = _signup(client, password="another-password-1")
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json() == auth_routes.SIGNUP_RESPONSE
    assert "token" not in first.json()
    assert emails == [("verify", "ada@example.com"), ("exists", "ada@example.com")]
    assert users["ada@example.com"]["email_verification_required"] is True


def test_signup_retry_with_same_password_resends_verification(signup_env):
    client, _, emails = signup_env
    _signup(client)
    _signup(client)
    assert emails == [("verify", "ada@example.com"), ("verify", "ada@example.com")]


def test_signup_runs_bcrypt_once_either_way(signup_env, monkeypatch):
    client, _, _ = signup_env
    hashed, checked = [], []
    real_hash, real_check = auth_routes.hash_password, auth_routes.verify_password
    monkeypatch.setattr(auth_routes, "hash_password", lambda p: hashed.append(1) or real_hash(p))
    monkeypatch.setattr(auth_routes, "verify_password", lambda p, h: checked.append(1) or real_check(p, h))
    _signup(client)
    assert (len(hashed), len(checked)) == (1, 0)
    _signup(client, password="another-password-1")
    assert (len(hashed), len(checked)) == (1, 1)


def test_forgot_password_sends_in_background(auth_client, monkeypatch):
    client, users = auth_client
    users["ada@example.com"] = {"_id": ObjectId(), "email": "ada@example.com", "password_hash": "x"}
    queued = []
    monkeypatch.setattr(auth_routes.BackgroundTasks, "add_task", lambda self, fn, *a, **k: queued.append(fn))
    r = client.post("/auth/forgot-password", json={"email": "ada@example.com"})
    assert r.status_code == 200
    assert queued == [auth_routes.send_email]


# ── G-15: the verification link signs in once ───────────────────────────────

def test_verify_link_signs_in_only_on_first_use(auth_client, monkeypatch):
    client, _ = auth_client
    uid = ObjectId()
    user = {"_id": uid, "email": "ada@example.com", "name": "Ada", "email_verified": False}
    monkeypatch.setattr(queries, "get_user_by_id", lambda s: user)

    def mark(user_id, email):
        if user["email_verified"]:
            return False
        user["email_verified"] = True
        return True

    monkeypatch.setattr(queries, "mark_email_verified", mark)
    monkeypatch.setattr(auth_routes, "_issue_token", lambda *a: "tok")
    token = security.create_verify_token(str(uid), "ada@example.com")
    first = client.post("/auth/verify-email", json={"token": token}).json()
    again = client.post("/auth/verify-email", json={"token": token}).json()
    assert first["token"] == "tok" and first["user"]["email"] == "ada@example.com"
    assert "token" not in again


# ── G-49: export ─────────────────────────────────────────────────────────────

def test_export_covers_every_owned_collection_and_hides_credentials(monkeypatch):
    db, me, other = FakeDB(), ObjectId(), ObjectId()
    db.users.insert_one({"_id": me, "email": "ada@example.com", "password_hash": "secret", "google_sub": "g-1",
                         "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)})
    for name in queries._USER_OWNED_COLLECTIONS:
        db[name].insert_one({"user_id": me, "what": f"mine-{name}"})
        db[name].insert_one({"user_id": other, "what": "not mine"})
    db.user_sessions.insert_one({"user_id": me, "ip": "1.2.3.4"})
    monkeypatch.setattr(queries, "get_db", lambda: db)
    monkeypatch.setattr(queries, "_sessions", lambda: db.user_sessions)

    app = FastAPI()
    app.include_router(auth_routes.router)
    app.dependency_overrides[get_current_user_id] = lambda: me
    r = TestClient(app).get("/account/export")

    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    for name in queries._USER_OWNED_COLLECTIONS:
        assert [row["what"] for row in data[name]] == [f"mine-{name}"], name
    assert "password_hash" not in data["account"] and "google_sub" not in data["account"]
    assert data["account"]["_id"] == str(me)
    assert data["account"]["created_at"].startswith("2026-01-02")
    assert data["user_sessions"][0]["ip"] == "1.2.3.4"
    assert "not mine" not in r.text


# ── G-23: notification settings ──────────────────────────────────────────────

NOON_UTC = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def test_email_off_skips_email():
    assert ac.email_plan({"channels": {"email": False}}, NOON_UTC) == ("skip", None)


def test_email_on_outside_quiet_hours_sends():
    settings = {"channels": {"email": True}, "quiet_hours": {"enabled": True, "start": "22:00", "end": "07:00", "timezone": "UTC"}}
    assert ac.email_plan(settings, NOON_UTC) == ("send", None)


def test_quiet_hours_across_midnight_hold_until_morning():
    quiet = {"enabled": True, "start": "22:00", "end": "07:00", "timezone": "UTC"}
    late = datetime(2026, 11, 16, 23, 30, tzinfo=timezone.utc)
    early = datetime(2026, 11, 17, 3, 0, tzinfo=timezone.utc)
    assert ac.quiet_hours_end(quiet, late) == datetime(2026, 11, 17, 7, 0, tzinfo=timezone.utc)
    assert ac.quiet_hours_end(quiet, early) == datetime(2026, 11, 17, 7, 0, tzinfo=timezone.utc)


def test_quiet_hours_use_the_users_timezone():
    # 12:00 UTC is 21:00 in Tokyo: inside 20:00-08:00 there, ending 08:00 Tokyo = 23:00 UTC.
    quiet = {"enabled": True, "start": "20:00", "end": "08:00", "timezone": "Asia/Tokyo"}
    assert ac.quiet_hours_end(quiet, NOON_UTC) == datetime(2026, 11, 16, 23, 0, tzinfo=timezone.utc)
    assert ac.quiet_hours_end({**quiet, "enabled": False}, NOON_UTC) is None
    assert ac.quiet_hours_end({**quiet, "timezone": "Not/AZone"}, NOON_UTC) is None


def _alert_db(email_on: bool, quiet: dict | None = None):
    db, uid = FakeDB(), ObjectId()
    # Verified: alert emails go only to a verified address (G-34), so these tests exercise the settings rules.
    db.users.insert_one({"_id": uid, "email": "ada@example.com", "email_verified": True})
    db.user_settings.insert_one({"user_id": uid, "notifications": {
        "channels": {"email": email_on}, "quiet_hours": quiet or {"enabled": False}}})
    db.alerts.insert_one({
        "user_id": uid, "status": "active", "target_type": "crypto", "target_symbol": "BTC", "target_name": "Bitcoin",
        "metric_type": "price", "condition": "above", "threshold_value": 100.0, "last_observed_value": 90.0,
        "delivery_channel": "email",
    })
    return db


def _evaluate(monkeypatch, db, now):
    sent = []
    monkeypatch.setattr(ac, "get_db", lambda: db)
    monkeypatch.setattr(ac, "_current_values", lambda: {("crypto", "BTC", "price"): 120.0})
    monkeypatch.setattr("utils.mailer.send_email", lambda to, subject, body: sent.append(subject) or True)

    class FixedNow(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(ac, "datetime", FixedNow)
    result = ac.evaluate_alerts()
    return result, sent


def test_evaluator_sends_no_email_when_email_is_off(monkeypatch):
    db = _alert_db(email_on=False)
    result, sent = _evaluate(monkeypatch, db, NOON_UTC)
    assert result["triggered"] == 1
    assert sent == []
    assert len(db.notifications.rows) == 1   # still shown in-app


def test_evaluator_holds_email_in_quiet_hours_then_sends(monkeypatch):
    quiet = {"enabled": True, "start": "11:00", "end": "13:00", "timezone": "UTC"}
    db = _alert_db(email_on=True, quiet=quiet)
    _, sent = _evaluate(monkeypatch, db, NOON_UTC)
    assert sent == []
    assert len(db.pending_alert_emails.rows) == 1

    later = datetime(2026, 11, 16, 13, 5, tzinfo=timezone.utc)
    _, sent = _evaluate(monkeypatch, db, later)
    assert len(sent) == 1 and sent[0].startswith("AltInvest alert: Bitcoin price rose above")
    assert db.pending_alert_emails.rows == []


def test_push_channel_is_gone():
    assert "push" not in ac.CHANNELS
