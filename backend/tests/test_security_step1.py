"""
Audit 2026-11-16, Step 1 security fixes:
  G-03  JWT_SECRET is required outside APP_ENV=dev
  G-08  reset links are single-use and sign out every session
  G-09  forced sentiment refreshes are admin-only
  G-31  CORS allows only the frontend origin
  G-16  the demo user is seeded only in dev
  G-10  email bodies (reset links) are not logged outside dev
"""
import importlib

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from auth import rate_limit as rl
from auth import security
from auth.dependencies import CurrentSession, get_current_session, is_admin_user
from routes import auth as auth_routes

STRONG = "x" * 48


# ── G-03 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("secret", ["", "short-secret", security._DEV_JWT_SECRET])
def test_weak_or_missing_secret_refused_in_production(monkeypatch, secret):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        security._load_jwt_secret()


def test_unset_app_env_counts_as_production(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        security._load_jwt_secret()


def test_strong_secret_used_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", STRONG)
    assert security._load_jwt_secret() == STRONG


def test_dev_falls_back_to_dev_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    assert security._load_jwt_secret() == security._DEV_JWT_SECRET


# ── G-08 ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def reset_env(monkeypatch):
    uid = ObjectId()
    user = {"_id": uid, "email": "ada@example.com", "password_hash": security.hash_password("old-password-1")}
    sessions_ended = []

    def replace_password_if_unchanged(user_id, expected_hash, payload):
        if user_id != uid or user.get("password_hash") != expected_hash:
            return False
        user.update(payload)
        return True

    monkeypatch.setattr(queries, "get_user_by_id", lambda s: user if ObjectId(s) == uid else None)
    monkeypatch.setattr(queries, "replace_password_if_unchanged", replace_password_if_unchanged)
    monkeypatch.setattr(queries, "delete_all_user_sessions", lambda u: sessions_ended.append(u) or 3)
    for name in ("hit", "check", "record", "clear"):
        monkeypatch.setattr(rl, name, lambda *a, **k: None)
    app = FastAPI()
    app.include_router(auth_routes.router)
    return TestClient(app), user, sessions_ended


def _reset(client, token, password):
    return client.post("/auth/reset-password", json={"token": token, "new_password": password})


def test_reset_link_works_once_and_signs_out_everywhere(reset_env):
    client, user, sessions_ended = reset_env
    token = security.create_reset_token(str(user["_id"]), user["email"], user["password_hash"])

    assert _reset(client, token, "new-password-1").status_code == 200
    assert security.verify_password("new-password-1", user["password_hash"])
    assert user.get("password_changed_at") is not None
    assert sessions_ended == [user["_id"]]

    again = _reset(client, token, "attacker-password")
    assert again.status_code == 400
    assert security.verify_password("new-password-1", user["password_hash"])


def test_password_change_kills_outstanding_reset_links(reset_env):
    client, user, _ = reset_env
    token = security.create_reset_token(str(user["_id"]), user["email"], user["password_hash"])
    user["password_hash"] = security.hash_password("changed-in-settings")
    assert _reset(client, token, "new-password-1").status_code == 400


def test_reset_token_without_fingerprint_rejected(reset_env):
    import jwt
    client, user, _ = reset_env
    legacy = jwt.encode({"sub": str(user["_id"]), "purpose": "password_reset", "exp": 9999999999},
                        security.JWT_SECRET, algorithm=security.JWT_ALGORITHM)
    assert _reset(client, legacy, "new-password-1").status_code == 400


# ── G-09 ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def sentiment_client(monkeypatch):
    from routes import sentiment as sentiment_routes
    monkeypatch.setattr(sentiment_routes, "_engine", lambda: None)
    monkeypatch.setattr(sentiment_routes, "_refresh_asset", lambda a, force: ({}, "refreshed"))
    monkeypatch.setattr(sentiment_routes, "_map_sentiment", lambda r: r)
    monkeypatch.setattr(sentiment_routes.threading, "Thread", lambda *a, **k: type("T", (), {"start": lambda s: None})())
    app = FastAPI()
    app.include_router(sentiment_routes.router)
    return TestClient(app)


def _as_user(client, monkeypatch, user):
    client.app.dependency_overrides[get_current_session] = lambda: CurrentSession(user["_id"], ObjectId(), user["email"])
    monkeypatch.setattr(queries, "get_user_by_id", lambda s: user)


@pytest.mark.parametrize("path", ["/sentiment/refresh", "/sentiment/btc/refresh"])
def test_refresh_needs_sign_in(sentiment_client, path):
    assert sentiment_client.post(path).status_code == 401


@pytest.mark.parametrize("path", ["/sentiment/refresh", "/sentiment/btc/refresh"])
def test_refresh_refused_for_non_admin(sentiment_client, monkeypatch, path):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    _as_user(sentiment_client, monkeypatch, {"_id": ObjectId(), "email": "user@example.com", "email_verified": True})
    assert sentiment_client.post(path).status_code == 403


def test_refresh_allowed_for_admin(sentiment_client, monkeypatch):
    from routes import sentiment as sentiment_routes
    if "btc" not in sentiment_routes._ACTIVE_ASSETS:
        pytest.skip("btc not an active asset in this checkout")
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com, other@example.com")
    _as_user(sentiment_client, monkeypatch, {"_id": ObjectId(), "email": "Boss@Example.com", "email_verified": True})
    assert sentiment_client.post("/sentiment/btc/refresh").status_code == 200


def test_unverified_admin_email_is_not_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    assert not is_admin_user({"email": "boss@example.com", "email_verified": False})
    assert is_admin_user({"email": "boss@example.com", "email_verified": True})
    monkeypatch.delenv("ADMIN_EMAILS")
    assert not is_admin_user({"email": "boss@example.com", "email_verified": True})


# ── G-31 ─────────────────────────────────────────────────────────────────────

def test_cors_allows_only_frontend_origin(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://app.example.com/")
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", "*, http://127.0.0.1:5173")
    import main
    assert main._cors_origins() == ["http://127.0.0.1:5173", "https://app.example.com"]


# ── G-16 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", ["db.seed_users", "db.seed_user_data"])
def test_demo_user_not_seeded_outside_dev(monkeypatch, module):
    mod = importlib.import_module(module)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(mod, "get_db", lambda: pytest.fail("touched the database outside dev"))
    mod.seed()


# ── G-10 ─────────────────────────────────────────────────────────────────────

def test_mailer_withholds_body_outside_dev(monkeypatch, capsys, caplog):
    from utils import mailer
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert mailer.send_email("a@example.com", "Reset", "https://x/reset?token=SECRET") is False
    assert "SECRET" not in capsys.readouterr().out
    assert "SECRET" not in caplog.text
