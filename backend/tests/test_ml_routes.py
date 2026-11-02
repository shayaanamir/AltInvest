"""C2 + C3: /prediction and /risk pass `note` through, never mock a covered asset, mark stale rows."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
import utils.asset_gate as gate
from routes import prediction, risk
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC


def _row(body: dict, age_hours: float) -> dict:
    # As Mongo returns it: a naive UTC datetime.
    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).replace(tzinfo=None)
    return {**body, "timestamp": ts}


@pytest.fixture
def db(monkeypatch):
    rows = {"pred": None, "risk": None}
    monkeypatch.setattr(gate, "require_known_asset", lambda a: a.upper())
    monkeypatch.setattr(prediction, "require_known_asset", lambda a: a.upper())
    monkeypatch.setattr(risk, "require_known_asset", lambda a: a.upper())
    monkeypatch.setattr(queries, "get_latest_prediction", lambda a: rows["pred"])
    monkeypatch.setattr(queries, "get_latest_risk", lambda a: rows["risk"])
    return rows


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(prediction.router)
    app.include_router(risk.router)
    return TestClient(app)


def test_note_and_signal_pass_through(db, client):
    db["pred"], db["risk"] = _row(PREDICT_BTC, 1), _row(RISK_BTC, 1)
    p = client.get("/prediction/BTC").json()
    r = client.get("/risk/BTC").json()
    assert p["note"] == PREDICT_BTC["note"] and p["signal"] == "UNCERTAIN"
    assert p["model_version"] == "baseline-last-value" and p["predicted_price"] is None
    assert r["note"] == RISK_BTC["note"] and r["risk_score"] == RISK_BTC["risk_score"]


@pytest.mark.parametrize("asset", ["BTC", "ETH", "SOL"])
def test_no_mock_for_covered_assets(db, client, asset):
    resp = client.get(f"/risk/{asset}")
    assert resp.status_code == 404
    assert "mock" not in resp.text.lower()


def test_null_risk_score_is_404_not_500(db, client):
    db["risk"] = _row({**RISK_BTC, "risk_score": None}, 1)
    assert client.get("/risk/BTC").status_code == 404


def test_row_37h_old_gets_the_stale_note(db, client):
    db["pred"], db["risk"] = _row(PREDICT_BTC, 37), _row(RISK_BTC, 37)
    for url, ml_note in (("/prediction/BTC", PREDICT_BTC["note"]), ("/risk/BTC", RISK_BTC["note"])):
        note = client.get(url).json()["note"]
        assert note.startswith(ml_note)          # ML's own note is kept
        assert "data stale" in note and "37 h old" in note


def test_row_35h_old_is_not_stale(db, client):
    db["pred"] = _row(PREDICT_BTC, 35)
    assert "data stale" not in client.get("/prediction/BTC").json()["note"]
