"""Contract test (PLAN Phase 6 done-when): real responses validate against docs/CONTRACT.md for every asset.

Unlike the other tests, this one runs the real service on the real validated CSVs (ml/data/raw/, git-ignored)
through FastAPI's TestClient. Both schemas are parsed from CONTRACT.md itself (the single source).
"""

import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.contract import load_schemas, validator
from ml.api.service import app
from ml.data.loader import raw_csv_path

pytestmark = pytest.mark.skipif(not all(raw_csv_path(a).exists() for a in config.ASSETS),
                                reason="raw CSVs missing (git-ignored); run ml.data.fetch and ml.data.validate")

SCHEMAS = load_schemas()
client = TestClient(app)


def _errors(title: str, body: dict) -> list[str]:
    return [f"{list(e.path)}: {e.message}" for e in validator(SCHEMAS[title]).iter_errors(body)]


def test_both_schemas_parsed_and_closed():
    assert set(SCHEMAS) == {"PredictionResponse", "RiskResponse"}
    assert all(s["additionalProperties"] is False for s in SCHEMAS.values())


def test_validator_rejects_bad_timestamp_and_extra_field():
    """Guards against a silent pass: date-time is really checked, and extra fields are refused."""
    ok = {"asset": "BTC", "risk_score": 50.0, "timestamp": "2026-10-20T00:00:00Z"}
    assert _errors("RiskResponse", ok) == []
    assert _errors("RiskResponse", {**ok, "timestamp": "not-a-date"})
    assert _errors("RiskResponse", {**ok, "regime": "calm"})


@pytest.mark.parametrize("asset", config.ASSETS)
def test_predict_and_risk_validate_against_contract(asset):
    pred, risk = client.get(f"/predict/{asset}"), client.get(f"/risk/{asset}")
    assert pred.status_code == 200 and risk.status_code == 200
    p, r = pred.json(), risk.json()
    assert _errors("PredictionResponse", p) == []
    assert _errors("RiskResponse", r) == []
    assert p["asset"] == r["asset"] == asset.upper()
    assert p["risk_score"] == r["risk_score"]
    assert 0 <= r["risk_score"] <= 100
    assert p["prediction_30d"] == 0
    assert p["predicted_price"] is None and p["lower_bound"] is None and p["upper_bound"] is None
    assert p["signal"] == "UNCERTAIN" and p["confidence"] is None
    assert p["model_version"] == config.MODEL_VERSION_PRICE
    assert p["note"] and r["note"]


@pytest.mark.parametrize("route", ["predict", "risk", "debug"])
def test_unknown_asset_is_404(route):
    assert client.get(f"/{route}/doge").status_code == 404


@pytest.mark.parametrize("asset", config.ASSETS)
def test_asset_is_case_insensitive(asset):
    bodies = [client.get(f"/risk/{a}") for a in (asset.lower(), asset.upper(), asset.capitalize())]
    assert all(b.status_code == 200 for b in bodies)
    assert len({b.json()["risk_score"] for b in bodies}) == 1
    assert client.get(f"/predict/{asset.upper()}").json()["asset"] == asset.upper()


def test_health_and_debug():
    h = client.get("/health").json()
    assert h["status"] == "ok"
    assert h["model_version"] == {"price": config.MODEL_VERSION_PRICE, "risk": config.MODEL_VERSION_RISK}
    assert set(h["data_last_bar"]) == set(config.ASSETS)
    d = client.get("/debug/btc").json()
    assert d["inputs"]["risk_score"] == pytest.approx(client.get("/risk/btc").json()["risk_score"], abs=1e-6)
    assert d["inputs"]["pool_assets"] == list(config.ASSETS)
