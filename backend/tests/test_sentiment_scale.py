"""Audit G-12: a sentiment shown or alerted on is always the reading (-1..1), never the AAI's 0-100 sentiment
component stored in the same aai_scores row. Without a live reading, lists, alerts and the detail page use the
row's `sentiment_raw`; a row without it (written before G-12) gives no sentiment at all, not 55."""
import pytest

import db.queries as queries
import controllers.market_controller as mc
from controllers import aai_controller as aai
from controllers import alert_controller as alerts
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC

OLD_ROW = {"target_id": "BTC", "aai_score": 61.0, "sentiment_score": 55.4, "sentiment_confidence": 0.8}  # no raw
NEW_ROW = {**OLD_ROW, "sentiment_raw": 0.21, "sentiment_trend": "rising"}


def test_aai_response_stores_the_reading_next_to_the_component(monkeypatch):
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: dict(PREDICT_BTC))
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: dict(RISK_BTC))
    out = aai.compute_aai_response("BTC", sentiment={"sentiment_score": 0.21, "confidence": 0.8, "available": True})
    assert out["sentiment_raw"] == 0.21
    assert 50 < out["sentiment_score"] <= 100                   # the 0-100 component, a different number


def test_no_reading_stores_no_raw(monkeypatch):
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: dict(PREDICT_BTC))
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: dict(RISK_BTC))
    out = aai.compute_aai_response("BTC", sentiment={"sentiment_score": 0.0, "confidence": 0.0, "available": False})
    assert out["sentiment_raw"] is None and out["sentiment_score"] == 50.0


def test_stored_sentiment_uses_only_the_raw_field():
    assert mc.stored_sentiment(OLD_ROW) is None
    assert mc.stored_sentiment(None) is None
    assert mc.stored_sentiment(NEW_ROW) == {"score": 0.21, "confidence": 0.8, "trend": "rising"}


@pytest.mark.parametrize("row, expected", [(OLD_ROW, None), (NEW_ROW, 0.21)])
def test_list_fields_never_show_the_component(row, expected):
    f = mc._aai_fields(row, None)
    assert f["sentiment_score"] == expected and f["aai_score"] == 61.0


def test_live_reading_still_wins():
    f = mc._aai_fields(NEW_ROW, {"score": -0.3, "confidence": 0.5, "trend": "falling"})
    assert (f["sentiment_score"], f["sentiment_confidence"], f["sentiment_trend"]) == (-0.3, 0.5, "falling")


@pytest.mark.parametrize("row, expected", [(OLD_ROW, None), (NEW_ROW, 0.21)])
def test_alert_values_never_use_the_component(monkeypatch, row, expected):
    monkeypatch.setattr(queries, "get_asset_market_data_all_latest", lambda: [])
    monkeypatch.setattr(queries, "get_nft_market_data_all_latest", lambda: [])
    monkeypatch.setattr(queries, "get_all_latest_aai_scores", lambda t: {"BTC": row} if t == "crypto" else {})
    monkeypatch.setattr(queries, "get_all_latest_risk_scores", lambda: {})
    monkeypatch.setattr(mc, "live_sentiment_by_symbol", lambda: {})
    values = alerts._current_values()
    assert values.get(("crypto", "BTC", "sentiment")) == expected
    assert values[("crypto", "BTC", "aai_score")] == 61.0
