"""Audit G-20: the AAI never uses a prediction or risk row that is too old, and says so."""
from datetime import datetime, timedelta, timezone

import pytest

from controllers import aai_controller as aai
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
SENT = {"sentiment_score": 0.2, "confidence": 0.8, "available": True}


def _at(row, age):
    return {**row, "timestamp": NOW - age}          # stored rows hold aware datetimes (ml_pull_controller._to_row)


@pytest.fixture
def rows(monkeypatch):
    rows = {"pred": _at(PREDICT_BTC, timedelta(hours=12)), "risk": _at(RISK_BTC, timedelta(hours=12))}
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: rows["pred"])
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: rows["risk"])
    return rows


def test_fresh_inputs_give_a_score_and_their_as_of(rows):
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["aai_score"] is not None
    assert out["stale_inputs"] == [] and out["missing_inputs"] == []
    assert out["inputs_as_of"] == {"prediction": "2026-11-17T00:00:00Z", "risk": "2026-11-17T00:00:00Z"}
    assert out["as_of"] == "2026-11-17T00:00:00Z"
    assert out["timestamp"] == "2026-11-17T12:00:00Z"
    assert aai.is_complete(out) and not aai.is_stale(out)


def test_exactly_at_the_limit_is_still_fresh(rows):
    rows["risk"] = _at(RISK_BTC, aai.INPUT_MAX_AGE)
    assert aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)["aai_score"] is not None


def test_stale_risk_gives_no_score_and_says_inputs_stale(rows):
    rows["risk"] = _at(RISK_BTC, aai.INPUT_MAX_AGE + timedelta(minutes=1))
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["aai_score"] is None and out["risk_score"] is None
    assert out["stale_inputs"] == ["risk score"] and out["missing_inputs"] == ["risk score"]
    assert out["note"].startswith("Inputs stale: the stored risk score (from 2026-11-14T11:59:00Z)")
    assert "No risk score is stored" not in out["note"]
    assert out["inputs_as_of"]["risk"] == "2026-11-14T11:59:00Z"      # recorded even though it wasn't used
    assert out["as_of"] == "2026-11-17T00:00:00Z"                      # only the prediction was used
    assert aai.is_stale(out) and not aai.is_complete(out)


def test_stale_prediction_and_risk(rows):
    rows["pred"] = _at(PREDICT_BTC, timedelta(days=10))
    rows["risk"] = _at(RISK_BTC, timedelta(days=10))
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["aai_score"] is None and out["pred_score"] is None
    assert out["stale_inputs"] == ["prediction", "risk score"]
    assert out["as_of"] is None and out["model_version"] is None


def test_ml_stale_note_counts_as_stale_even_when_recent(rows):
    rows["pred"] = {**rows["pred"], "note": "No-change baseline. data stale: last bar 2026-11-10"}
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["aai_score"] is None and out["stale_inputs"] == ["prediction"]


def test_row_without_a_readable_time_is_stale(rows):
    rows["risk"] = {**RISK_BTC, "timestamp": "not a date"}
    assert aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)["stale_inputs"] == ["risk score"]


def test_iso_string_timestamps_are_read(rows):
    rows["pred"] = {**PREDICT_BTC, "timestamp": "2026-11-16T00:15:00Z"}
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["aai_score"] is not None and out["inputs_as_of"]["prediction"] == "2026-11-16T00:15:00Z"


def test_missing_input_is_not_called_stale(rows):
    rows["risk"] = None
    out = aai.compute_aai_response("BTC", sentiment=SENT, now=NOW)
    assert out["stale_inputs"] == [] and out["missing_inputs"] == ["risk score"]
    assert out["note"].startswith("No risk score is stored for BTC yet")
    assert out["inputs_as_of"]["risk"] is None


def test_refresh_stores_a_null_row_for_stale_inputs(rows, monkeypatch):
    """Lists read the newest aai_scores row: a stale asset must get a null-score row, not keep its old score."""
    import db.queries as q
    import controllers.market_controller as mc
    written = {}
    monkeypatch.setattr(q, "get_supported_assets", lambda: [{"asset_id": "BTC"}, {"asset_id": "ETH"}])
    monkeypatch.setattr(q, "upsert_aai_score_generalized", lambda t, i, p: written.__setitem__(i, p))
    monkeypatch.setattr(mc, "live_sentiment_by_symbol",
                        lambda: {s: {"score": 0.1, "confidence": 0.9, "trend": "flat"} for s in ("BTC", "ETH")})
    real = aai.compute_aai_response

    def fake(symbol, sentiment=None, now=None):
        if symbol == "ETH":
            rows["risk"] = _at(RISK_BTC, timedelta(days=5)) | {"asset": "ETH"}
        else:
            rows["risk"] = _at(RISK_BTC, timedelta(hours=1))
        return real(symbol, sentiment=sentiment, now=NOW)
    monkeypatch.setattr(aai, "compute_aai_response", fake)

    out = aai.refresh_all_aai_scores()
    assert out["stored"] == ["BTC"] and out["stale"] == ["ETH"]
    assert written["BTC"]["aai_score"] is not None and written["BTC"]["inputs_as_of"]["risk"] == "2026-11-17T11:00:00Z"
    assert written["ETH"]["aai_score"] is None and written["ETH"]["stale_inputs"] == ["risk score"]


def test_not_covered_response_has_the_new_fields():
    out = aai.not_covered_response("DAI")
    assert out["stale_inputs"] == [] and out["as_of"] is None and out["inputs_as_of"] == {"prediction": None, "risk": None}
