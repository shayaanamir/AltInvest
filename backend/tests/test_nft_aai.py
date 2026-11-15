"""C6 (decided 2026-11-15): NFT AAI = 0.4 x neutral 50 + 0.3 x sentiment + 0.3 x ML NFT risk,
stored only once the sentiment engine has a usable reading for the collection's slug."""
import pytest

from controllers import aai_controller as aai

SENT = {"sentiment_score": 0.5, "confidence": 1.0, "available": True}
ML_RISK = {"slug": "azuki", "risk_score": 60.0, "source": "ml-service"}


@pytest.fixture
def risk(monkeypatch):
    rows = {"azuki": dict(ML_RISK)}
    monkeypatch.setattr(aai, "_get_nft_risk", lambda slug: rows.get(slug))
    return rows


def test_formula_uses_neutral_prediction(risk):
    out = aai.compute_nft_aai_response("azuki", SENT)
    # sentiment 0.5 -> 75; 0.4*50 + 0.3*75 + 0.3*60 = 60.5
    assert out["pred_score"] == 50.0
    assert out["aai_score"] == 60.5
    assert out["model_version"] == aai.NFT_AAI_MODEL_VERSION
    assert aai.NFT_AAI_NOTE in out["note"]
    assert aai.is_complete(out)


def test_missing_ml_risk_gives_no_score(risk):
    out = aai.compute_nft_aai_response("milady", SENT)
    assert out["aai_score"] is None and out["missing_inputs"] == ["risk score"]
    assert not aai.is_complete(out)


def test_no_sentiment_is_not_complete(risk):
    out = aai.compute_nft_aai_response("azuki", {"sentiment_score": 0.0, "confidence": 0.0, "available": False})
    assert out["aai_score"] is not None
    assert not aai.is_complete(out)


def test_non_ml_risk_row_is_ignored(monkeypatch):
    import db.queries as q
    monkeypatch.setattr(q, "get_nft_risk_breakdown", lambda slug: {"risk_score": 80.0, "source": "seed"})
    assert aai._get_nft_risk("azuki") is None


def _run_refresh(monkeypatch, live, risk_rows):
    import db.queries as q
    import controllers.market_controller as mc
    stored = []
    monkeypatch.setattr(mc, "live_sentiment_by_symbol", lambda: live)
    monkeypatch.setattr(q, "get_supported_assets", lambda: [])
    monkeypatch.setattr(q, "get_nft_collections", lambda: [{"slug": "azuki"}, {"slug": "milady"}])
    monkeypatch.setattr(q, "upsert_aai_score_generalized", lambda t, i, p: stored.append((t, i, p)))
    monkeypatch.setattr(aai, "_get_nft_risk", lambda slug: risk_rows.get(slug))
    return aai.refresh_all_aai_scores(), stored


def test_refresh_stores_nothing_without_nft_sentiment(monkeypatch):
    outcome, stored = _run_refresh(monkeypatch, {}, {"azuki": ML_RISK})
    assert stored == []
    assert outcome["skipped"] == {"nft:azuki": "recent sentiment", "nft:milady": "recent sentiment"}


def test_refresh_stores_nft_aai_once_sentiment_arrives(monkeypatch):
    live = {"AZUKI": {"score": 0.5, "confidence": 1.0, "trend": "up"},
            "MILADY": {"score": 0.1, "confidence": 1.0, "trend": "flat"}}
    outcome, stored = _run_refresh(monkeypatch, live, {"azuki": ML_RISK})
    assert outcome["stored"] == ["nft:azuki"]
    assert outcome["skipped"] == {"nft:milady": "risk score"}
    (target_type, target_id, payload), = stored
    assert (target_type, target_id) == ("nft", "azuki")
    assert payload["aai_score"] == 60.5 and payload["target_type"] == "nft"
    assert payload["sentiment_trend"] == "up"
