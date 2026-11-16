"""AUTH-11: Google sign-in account matching, linking and unlinking, with Google and Mongo faked."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from auth import google_oauth
from auth import rate_limit as rl
from auth.dependencies import get_current_user_id
from auth.security import hash_password
from routes import auth as auth_routes

GOOGLE = google_oauth.GoogleIdentity(
    sub="google-123", email="ada@example.com", email_verified=True, name="Ada Lovelace", picture=None,
)


class FakeUsers:
    def __init__(self):
        self.rows: dict[ObjectId, dict] = {}
        self.sessions_ended: list[ObjectId] = []
        self.settings_created: list[ObjectId] = []

    def add(self, **fields) -> dict:
        row = {"_id": ObjectId(), "name": "Existing", "email_verified": False, **fields}
        self.rows[row["_id"]] = row
        return row

    def by(self, key, value):
        return next((r for r in self.rows.values() if r.get(key) == value), None)


@pytest.fixture
def users(monkeypatch):
    store = FakeUsers()

    def create_user(email, name, password_hash, *, email_verified=False, extra=None):
        row = store.add(email=email, name=name, password_hash=password_hash,
                        email_verified=email_verified, **(extra or {}))
        return str(row["_id"])

    def update_user(user_id, payload):
        store.rows[user_id].update(payload)
        return True

    def unset_user_fields(user_id, *fields):
        for f in fields:
            store.rows[user_id].pop(f, None)
        return True

    monkeypatch.setattr(queries, "get_user_by_google_sub", lambda sub: store.by("google_sub", sub))
    monkeypatch.setattr(queries, "get_user_by_email", lambda email: store.by("email", email))
    monkeypatch.setattr(queries, "get_user_by_id", lambda uid: store.rows.get(ObjectId(uid)))
    monkeypatch.setattr(queries, "create_user", create_user)
    monkeypatch.setattr(queries, "update_user", update_user)
    monkeypatch.setattr(queries, "unset_user_fields", unset_user_fields)
    monkeypatch.setattr(queries, "delete_all_user_sessions", lambda uid: store.sessions_ended.append(uid) or 1)
    monkeypatch.setattr(queries, "update_user_settings", lambda *a, **k: True)
    monkeypatch.setattr(auth_routes, "create_default_user_settings", store.settings_created.append)
    monkeypatch.setattr(auth_routes, "_issue_token", lambda uid, email, req: f"token-for-{uid}")
    for name in ("hit", "check", "record", "clear"):
        monkeypatch.setattr(rl, name, lambda *a, **k: None)
    monkeypatch.setattr(google_oauth, "identity_from_code", lambda code: GOOGLE)
    return store


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(auth_routes.router)
    return TestClient(app)


def _signed_in_as(client, user_id):
    client.app.dependency_overrides[get_current_user_id] = lambda: user_id


def test_first_google_sign_in_creates_a_passwordless_verified_account(users, client):
    res = client.post("/auth/google", json={"code": "c"})
    assert res.status_code == 200
    body = res.json()
    assert body["created"] is True
    row = users.by("google_sub", "google-123")
    assert row["email"] == "ada@example.com" and row["name"] == "Ada Lovelace"
    assert row["password_hash"] is None and row["email_verified"] is True
    assert users.settings_created == [row["_id"]]
    assert body["token"] == f"token-for-{row['_id']}"


def test_returning_google_user_signs_into_the_same_account(users, client):
    existing = users.add(email="renamed@example.com", google_sub="google-123", email_verified=True)
    body = client.post("/auth/google", json={"code": "c"}).json()
    assert body["created"] is False
    assert body["user"]["id"] == str(existing["_id"])
    # Matched by Google's id, so the account keeps its own email even if Google's changed.
    assert body["user"]["email"] == "renamed@example.com"
    assert len(users.rows) == 1


def test_verified_email_account_gets_google_linked_and_keeps_its_password(users, client):
    existing = users.add(email="ada@example.com", password_hash="hash", email_verified=True)
    body = client.post("/auth/google", json={"code": "c"}).json()
    assert body["user"]["id"] == str(existing["_id"]) and body["created"] is False
    assert existing["google_sub"] == "google-123" and existing["password_hash"] == "hash"
    assert users.sessions_ended == []


def test_unverified_email_account_loses_its_password_and_sessions(users, client):
    # Someone registered ada@ without proving they own it; Google proves Ada does.
    squatter = users.add(email="ada@example.com", password_hash="attacker-hash", email_verified=False)
    client.post("/auth/google", json={"code": "c"})
    assert squatter["password_hash"] is None and squatter["email_verified"] is True
    assert users.sessions_ended == [squatter["_id"]]


def test_unverified_google_email_is_refused(users, client, monkeypatch):
    monkeypatch.setattr(google_oauth, "identity_from_code",
                        lambda code: google_oauth.GoogleIdentity("g", "x@example.com", False, "X", None))
    assert client.post("/auth/google", json={"code": "c"}).status_code == 400
    assert users.rows == {}


def test_link_from_settings(users, client):
    me = users.add(email="other@example.com", password_hash="h", email_verified=True)
    _signed_in_as(client, me["_id"])
    res = client.post("/auth/google/link", json={"code": "c"})
    assert res.status_code == 200 and me["google_sub"] == "google-123"


def test_link_refuses_a_google_account_used_elsewhere(users, client):
    users.add(email="ada@example.com", google_sub="google-123", email_verified=True)
    me = users.add(email="other@example.com", password_hash="h", email_verified=True)
    _signed_in_as(client, me["_id"])
    assert client.post("/auth/google/link", json={"code": "c"}).status_code == 409
    assert "google_sub" not in me


def test_unlink_needs_a_password_on_the_account(users, client):
    me = users.add(email="ada@example.com", google_sub="google-123", password_hash=None, email_verified=True)
    _signed_in_as(client, me["_id"])
    res = client.post("/auth/google/unlink", json={"password": ""})
    assert res.status_code == 400 and me["google_sub"] == "google-123"


def test_unlink_with_the_right_password(users, client):
    me = users.add(email="ada@example.com", google_sub="google-123",
                   password_hash=hash_password("correct horse"), email_verified=True)
    _signed_in_as(client, me["_id"])
    assert client.post("/auth/google/unlink", json={"password": "wrong pass"}).status_code == 400
    assert client.post("/auth/google/unlink", json={"password": "correct horse"}).status_code == 200
    assert "google_sub" not in me


def test_providers_reports_whether_google_is_configured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    assert client.get("/auth/providers").json()["google"] == {"enabled": False, "client_id": None}
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")
    assert client.get("/auth/providers").json()["google"]["enabled"] is True


def test_sign_in_without_configuration_is_503(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    assert client.post("/auth/google", json={"code": "c"}).status_code == 503


# ── ID token verification (needs `cryptography`, i.e. PyJWT[crypto]) ──────────

@pytest.fixture
def signing_key(monkeypatch):
    rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")
    import jwt
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Keys:
        def get_signing_key_from_jwt(self, token):
            return jwt.PyJWK.from_dict({**jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True), "alg": "RS256"})

    monkeypatch.setattr(google_oauth, "_jwks_client", Keys())
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
    return key


def _id_token(key, **overrides):
    import jwt
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://accounts.google.com", "aud": "abc.apps.googleusercontent.com", "sub": "g-1",
        "email": "Ada@Example.com", "email_verified": True, "name": "Ada",
        "iat": now, "exp": now + timedelta(minutes=5), **overrides,
    }
    return jwt.encode(claims, key, algorithm="RS256")


def test_valid_id_token(signing_key):
    ident = google_oauth.verify_id_token(_id_token(signing_key))
    assert ident.sub == "g-1" and ident.email == "ada@example.com" and ident.email_verified


@pytest.mark.parametrize("overrides", [
    {"aud": "someone-elses-client"},
    {"iss": "https://evil.example.com"},
    {"exp": datetime.now(timezone.utc) - timedelta(hours=1)},
])
def test_rejected_id_tokens(signing_key, overrides):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        google_oauth.verify_id_token(_id_token(signing_key, **overrides))
    assert exc.value.status_code == 400
