"""D94: an asset outside db.queries.ML_COVERED_ASSETS (DAI, BASE) gets no AAI anywhere: the controller computes
nothing, the refresh stores nothing, and the read functions return nothing even if an old seeded row remains."""
import pytest

import db.queries as queries
from controllers import aai_controller as aai
from models.schemas import AAIResponse
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC


def _fresh(row):
    """The fixture row as if pulled just now: older rows count as stale since G-20."""
    from datetime import datetime, timezone
    return {**row, "timestamp": datetime.now(timezone.utc)}


UNCOVERED = ["DAI", "BASE"]


def _boom(*a, **k):
    raise AssertionError("must not be called for an uncovered asset")


@pytest.mark.parametrize("asset", UNCOVERED)
def test_controller_computes_nothing_for_an_uncovered_asset(monkeypatch, asset):
    monkeypatch.setattr(aai, "_get_real_prediction", _boom)
    monkeypatch.setattr(aai, "_get_real_risk", _boom)
    monkeypatch.setattr(aai, "_get_real_sentiment", _boom)
    out = aai.compute_aai_response(asset.lower())
    assert out["covered"] is False and out["asset"] == asset
    assert all(out[k] is None for k in ("aai_score", "pred_score", "risk_score", "sentiment_score", "model_version"))
    assert out["note"] == aai.NOT_COVERED_NOTE and not aai.is_complete(out)
    AAIResponse(**out)                          # the /aai and /intelligence response model accepts it


def test_covered_asset_is_marked_covered(monkeypatch):
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: _fresh(PREDICT_BTC))
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: _fresh(RISK_BTC))
    out = aai.compute_aai_response("BTC", sentiment={"sentiment_score": 0.2, "confidence": 0.5, "available": True})
    assert out["covered"] is True and out["aai_score"] is not None


def test_refresh_skips_uncovered_assets(monkeypatch):
    import controllers.market_controller as mc
    stored = []
    monkeypatch.setattr(queries, "get_supported_assets", lambda: [{"asset_id": a} for a in ("BTC", "DAI", "BASE")])
    monkeypatch.setattr(queries, "upsert_aai_score_generalized", lambda t, i, p: stored.append(i))
    monkeypatch.setattr(mc, "live_sentiment_by_symbol",
                        lambda: {a: {"score": 0.1, "confidence": 0.9, "trend": "flat"} for a in ("BTC", "DAI", "BASE")})
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: _fresh(PREDICT_BTC))
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: _fresh(RISK_BTC))
    monkeypatch.setattr(aai, "_refresh_nft_aai_scores", lambda *a: None)    # NFT half: tests/test_nft_aai.py
    out = aai.refresh_all_aai_scores()
    assert stored == ["BTC"] and out["stored"] == ["BTC"]
    assert out["skipped"] == {"DAI": "not covered by the ML service", "BASE": "not covered by the ML service"}


class _Coll:
    def __init__(self):
        self.calls = []

    def find_one(self, flt, **kw):
        self.calls.append(("find_one", flt))
        return {"target_id": flt["target_id"], "aai_score": 99}

    def aggregate(self, pipeline, **kw):
        match = pipeline[0]["$match"]
        self.calls.append(("aggregate", match))
        ids = match["target_id"]["$in"] if "target_id" in match else ["DAI", "BASE", "BTC", "azuki"]
        return [{"target_id": i, "aai_score": 99} for i in ids]


@pytest.fixture
def coll(monkeypatch):
    c = _Coll()
    monkeypatch.setattr(queries, "get_db", lambda: type("DB", (), {"aai_scores": c})())
    return c


@pytest.mark.parametrize("asset", UNCOVERED)
def test_reads_return_nothing_for_uncovered_crypto(coll, asset):
    assert queries.get_latest_aai_score("crypto", asset) is None
    assert queries.get_latest_aai_score("crypto", asset.lower()) is None
    assert coll.calls == []                     # not even queried
    assert asset not in queries.get_all_latest_aai_scores("crypto")
    assert queries.get_latest_aai_scores_for("crypto", [asset, "BTC"]) == {"BTC": {"target_id": "BTC", "aai_score": 99}}


def test_reads_are_unchanged_for_covered_crypto_and_nft(coll):
    assert queries.get_latest_aai_score("crypto", "BTC")["aai_score"] == 99
    assert set(queries.get_all_latest_aai_scores("crypto")) == set(queries.ML_COVERED_ASSETS)
    assert queries.get_latest_aai_score("nft", "azuki")["aai_score"] == 99      # NFTs are not gated
    assert "azuki" in queries.get_all_latest_aai_scores("nft")
