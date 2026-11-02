"""C1: the ML pull with a mocked HTTP client and mocked database writes (no network, no Mongo)."""
from datetime import datetime, timezone

import httpx
import pytest

import db.queries as queries
from controllers import ml_pull_controller as pull

# Real ML responses of 2026-11-02 (ml/docs/PLAN_NEXT.md, Appendix).
PREDICT_BTC = {
    "asset": "BTC", "predicted_price": None, "prediction_30d": 0.0, "confidence": None,
    "model_version": "baseline-last-value", "timestamp": "2026-11-02T08:21:06Z", "lower_bound": None,
    "upper_bound": None, "risk_score": 97.795108, "trend": None, "agreement": None, "signal": "UNCERTAIN",
    "boosted_confidence": None, "ensemble_price": None,
    "note": "No model beats the no-change baseline (D35): prediction_30d is the last-value baseline (0%).",
}
RISK_BTC = {
    "asset": "BTC", "risk_score": 97.795108, "volatility": 0.284906, "sharpe_ratio": -0.772753,
    "timestamp": "2026-11-02T08:21:04Z", "note": "No risk model beats persistence (D27).",
}


@pytest.fixture
def stored(monkeypatch):
    rows = {"predictions": [], "risk_scores": []}
    monkeypatch.setattr(queries, "upsert_ml_prediction", lambda d: rows["predictions"].append(d))
    monkeypatch.setattr(queries, "upsert_ml_risk", lambda d: rows["risk_scores"].append(d))
    return rows


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _no_sleep(_):
    pass


def test_200_stores_every_field_with_a_datetime_timestamp(stored):
    def handler(req):
        return httpx.Response(200, json=PREDICT_BTC if "/predict/" in req.url.path else RISK_BTC)

    out = pull.pull_asset(_client(handler), "BTC", sleep=_no_sleep)
    assert out == {"predict": "stored", "risk": "stored"}
    p, r = stored["predictions"][0], stored["risk_scores"][0]
    for k, v in PREDICT_BTC.items():
        if k != "timestamp":
            assert p[k] == v
    assert p["timestamp"] == datetime(2026, 11, 2, 8, 21, 6, tzinfo=timezone.utc)
    assert isinstance(r["timestamp"], datetime)
    assert r["note"] == RISK_BTC["note"] and p["signal"] == "UNCERTAIN"


def test_404_skips_without_retry(stored):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(404, json={"detail": "not covered"})

    out = pull.pull_asset(_client(handler), "DOGE", sleep=_no_sleep)
    assert out["predict"].startswith("skipped") and out["risk"].startswith("skipped")
    assert len(calls) == 2                      # one call per endpoint, no retries
    assert stored == {"predictions": [], "risk_scores": []}


def test_503_retries_then_writes_nothing(stored):
    calls, waits = [], []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(503, json={"detail": "data failed its checks"})

    out = pull.pull_asset(_client(handler), "BTC", sleep=waits.append)
    assert out["predict"].startswith("failed: HTTP 503") and out["risk"].startswith("failed: HTTP 503")
    assert len(calls) == 2 * (pull.RETRIES + 1)
    assert waits == list(pull.BACKOFF_SECONDS) * 2
    assert stored == {"predictions": [], "risk_scores": []}


def test_timeout_writes_nothing(stored):
    def handler(req):
        raise httpx.ReadTimeout("timed out", request=req)

    out = pull.pull_asset(_client(handler), "BTC", sleep=_no_sleep)
    assert out["predict"].startswith("failed: timeout") and out["risk"].startswith("failed: timeout")
    assert stored == {"predictions": [], "risk_scores": []}


def test_recovers_after_one_timeout(stored):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        if n["calls"] == 1:
            raise httpx.ConnectTimeout("down", request=req)
        return httpx.Response(200, json=PREDICT_BTC if "/predict/" in req.url.path else RISK_BTC)

    assert pull.pull_asset(_client(handler), "BTC", sleep=_no_sleep) == {"predict": "stored", "risk": "stored"}


def test_wrong_asset_or_null_risk_is_not_stored(stored):
    def handler(req):
        if "/predict/" in req.url.path:
            return httpx.Response(200, json={**PREDICT_BTC, "asset": "ETH"})
        return httpx.Response(200, json={**RISK_BTC, "risk_score": None})

    out = pull.pull_asset(_client(handler), "BTC", sleep=_no_sleep)
    assert out["predict"].startswith("failed: bad body") and out["risk"].startswith("failed: bad body")
    assert stored == {"predictions": [], "risk_scores": []}


def test_upsert_refuses_a_string_timestamp():
    with pytest.raises(TypeError):
        queries._upsert_ml_row("predictions", {**PREDICT_BTC})


def test_next_pull_is_0015_utc():
    now = datetime(2026, 11, 2, 8, 21, tzinfo=timezone.utc)
    assert pull.seconds_until_next_pull(now) == (15 * 3600 + 54 * 60)
    just_before = datetime(2026, 11, 2, 0, 14, tzinfo=timezone.utc)
    assert pull.seconds_until_next_pull(just_before) == 60
