"""C5 (decided 2026-11-02): the ML no-change baseline counts as a neutral pred_score 50, and the AAI note says so."""
import pytest

from controllers import aai_controller as aai
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC

SENT = {"sentiment_score": 0.0, "confidence": 0.0, "available": True}


@pytest.fixture
def inputs(monkeypatch):
    rows = {"pred": dict(PREDICT_BTC), "risk": dict(RISK_BTC)}
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: rows["pred"])
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: rows["risk"])
    return rows


def test_baseline_is_neutral_50_with_a_note(inputs):
    out = aai.compute_aai_response("BTC", sentiment=SENT)
    assert out["pred_score"] == 50.0
    assert out["aai_score"] is not None
    assert out["note"] == aai.BASELINE_NOTE
    assert out["model_version"] == "baseline-last-value"


def test_no_baseline_note_for_another_model(inputs):
    inputs["pred"]["model_version"] = "some-model"
    assert aai.compute_aai_response("BTC", sentiment=SENT)["note"] is None


def test_missing_risk_keeps_the_missing_note(inputs):
    inputs["risk"] = None
    out = aai.compute_aai_response("BTC", sentiment=SENT)
    assert out["aai_score"] is None and out["missing_inputs"] == ["risk score"]
    assert out["note"].startswith("No risk score is stored for BTC yet")
