"""NFT AAI (ml/docs/DECISIONS.md D98, decision C6): neutral 50 prediction, NFT sentiment, ML NFT risk score."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import db.queries as queries
from aai_engine.aai import compute_aai, compute_nft_aai
from controllers import aai_controller as aai

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
SENT = {"sentiment_score": 0.4, "confidence": 1.0, "available": True}


def _risk(age=timedelta(hours=12), **kw):
    return {"slug": "azuki", "risk_score": 70.0, "source": "ml-service", "timestamp": NOW - age,
            "note": "persistence vol_30d", **kw}


@pytest.fixture
def risk(monkeypatch):
    holder = {"row": _risk()}
    monkeypatch.setattr(queries, "get_nft_risk_breakdown", lambda slug: holder["row"])
    return holder


def test_engine_is_the_crypto_formula_with_a_neutral_prediction():
    assert compute_nft_aai(70, 70) == compute_aai(50, 70, 70) == 62.0
    assert compute_nft_aai(0, 0) == 20.0 and compute_nft_aai(100, 100) == 80.0


def test_score_from_sentiment_and_ml_risk(risk):
    out = aai.compute_nft_aai_response("azuki", sentiment=SENT, now=NOW)
    # sentiment 0.4 -> 70; 0.4 x 50 + 0.3 x 70 + 0.3 x 70 = 62
    assert out["aai_score"] == 62.0
    assert out["pred_score"] == 50.0 and out["expected_return_30d"] is None
    assert out["sentiment_score"] == 70.0 and out["sentiment_raw"] == 0.4
    assert out["risk_score"] == 70.0
    assert out["missing_inputs"] == [] and out["stale_inputs"] == []
    assert out["as_of"] == "2026-11-20T00:00:00Z" and out["inputs_as_of"]["prediction"] is None
    assert out["model_version"] == aai.NFT_AAI_MODEL_VERSION
    assert "not comparable to a crypto AAI score" in out["note"]
    assert aai.is_complete(out) and not aai.is_stale(out)


def test_low_confidence_pulls_sentiment_toward_neutral(risk):
    out = aai.compute_nft_aai_response("azuki", sentiment={**SENT, "confidence": 0.5}, now=NOW)
    assert out["sentiment_score"] == 60.0


def test_no_sentiment_uses_neutral_and_is_not_complete(risk):
    out = aai.compute_nft_aai_response("azuki", sentiment=dict(aai.NFT_NO_SENTIMENT), now=NOW)
    assert out["aai_score"] == 56.0            # 20 + 15 + 21
    assert out["sentiment_available"] is False and out["sentiment_raw"] is None
    assert out["sentiment_note"] and not aai.is_complete(out)


def test_no_risk_row_gives_no_score(risk):
    risk["row"] = None
    out = aai.compute_nft_aai_response("azuki", sentiment=SENT, now=NOW)
    assert out["aai_score"] is None and out["missing_inputs"] == ["risk score"] and out["stale_inputs"] == []
    assert "No ML risk score is stored for azuki" in out["note"]


def test_seeded_risk_row_does_not_count(risk):
    risk["row"] = _risk(source="seed")
    assert aai.compute_nft_aai_response("azuki", sentiment=SENT, now=NOW)["aai_score"] is None


def test_stale_risk_gives_no_score(risk):
    risk["row"] = _risk(age=aai.INPUT_MAX_AGE + timedelta(minutes=1))
    out = aai.compute_nft_aai_response("azuki", sentiment=SENT, now=NOW)
    assert out["aai_score"] is None and out["stale_inputs"] == ["risk score"]
    assert out["note"].startswith("Inputs stale") and out["as_of"] is None
    assert aai.is_stale(out)


def test_ml_stale_note_counts_as_stale(risk):
    risk["row"] = _risk(note="data stale: last floor 2026-11-15")
    assert aai.compute_nft_aai_response("azuki", sentiment=SENT, now=NOW)["stale_inputs"] == ["risk score"]


def test_sentiment_is_read_by_slug(monkeypatch, risk):
    import controllers.market_controller as mc
    monkeypatch.setattr(mc, "live_nft_sentiment", lambda: {"azuki": {"score": -0.2, "confidence": 1.0}})
    out = aai.compute_nft_aai_response("azuki", now=NOW)
    assert out["sentiment_raw"] == -0.2 and out["sentiment_score"] == 40.0


def test_refresh_stores_complete_nft_scores_and_skips_the_rest(monkeypatch):
    import controllers.market_controller as mc
    upserts = []
    rows = {"azuki": _risk(age=timedelta(0)), "doodles-official": _risk(age=timedelta(days=10)),
            "milady": _risk(age=timedelta(0)), "pudgypenguins": None}
    monkeypatch.setattr(queries, "get_supported_assets", lambda: [])
    monkeypatch.setattr(queries, "get_nft_collections", lambda: [{"slug": s} for s in rows])
    monkeypatch.setattr(queries, "get_nft_risk_breakdown", lambda slug: rows[slug])
    monkeypatch.setattr(queries, "upsert_aai_score_generalized", lambda t, i, p: upserts.append((t, i, p)))
    monkeypatch.setattr(mc, "live_sentiment_by_symbol", lambda: {})
    live = {s: {"score": 0.1, "confidence": 0.9, "trend": "up"} for s in ("azuki", "doodles-official", "pudgypenguins")}
    monkeypatch.setattr(mc, "live_nft_sentiment", lambda: live)

    out = aai.refresh_all_aai_scores()
    assert out["stored"] == ["nft:azuki"]
    assert out["stale"] == ["nft:doodles-official"]
    assert out["skipped"] == {"nft:milady": "recent sentiment", "nft:pudgypenguins": "risk score"}
    stored = {i: p for t, i, p in upserts if t == "nft"}
    assert set(stored) == {"azuki", "doodles-official"}
    assert stored["azuki"]["target_type"] == "nft" and stored["azuki"]["sentiment_trend"] == "up"
    assert stored["doodles-official"]["aai_score"] is None


def test_nft_refresh_failure_keeps_the_crypto_result(monkeypatch):
    import controllers.market_controller as mc
    monkeypatch.setattr(queries, "get_supported_assets", lambda: [])
    monkeypatch.setattr(mc, "live_sentiment_by_symbol", lambda: {})

    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(mc, "live_nft_sentiment", boom)
    out = aai.refresh_all_aai_scores()
    assert out["skipped"] == {"nft": "refresh failed (RuntimeError)"}


def test_route_404s_an_unknown_collection(monkeypatch):
    from routes.aai import get_nft_aai
    monkeypatch.setattr(queries, "get_nft_collection", lambda slug: None)
    with pytest.raises(HTTPException) as exc:
        get_nft_aai("not-a-collection")
    assert exc.value.status_code == 404


def test_route_returns_the_collection_score(monkeypatch, risk):
    import controllers.market_controller as mc
    from routes.aai import get_nft_aai
    monkeypatch.setattr(queries, "get_nft_collection", lambda slug: {"slug": slug})
    monkeypatch.setattr(mc, "live_nft_sentiment", lambda: {"azuki": {"score": 0.4, "confidence": 1.0}})
    risk["row"] = _risk(age=timedelta(0)) | {"timestamp": datetime.now(timezone.utc)}
    out = get_nft_aai("azuki")
    assert out["asset"] == "azuki" and out["aai_score"] == 62.0
