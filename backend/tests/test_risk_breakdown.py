"""D96: measured risk breakdown (ranking, missing inputs, DAI/BASE exclusion) and the AAI formula for the 16 coins.

All numbers are HAND-MADE test values, not market data.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import db.queries as queries
from controllers import aai_controller as aai
from controllers import risk_breakdown_controller as rb
from controllers.market_controller import volatility_rank
from routes.assets import get_asset_risk_breakdown, risk_overview_rows
from tests.test_ml_pull import PREDICT_BTC, RISK_BTC

NOW = datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc)


# ── ranking ───────────────────────────────────────────────────────────────────

def test_safety_scores_rank_higher_is_safer():
    vols = {"A": 0.2, "B": 0.5, "C": 0.8}                       # riskier when higher
    assert rb.safety_scores(vols, riskier_when_higher=True) == {"A": 100.0, "B": 50.0, "C": 0.0}
    liq = {"A": 0.01, "B": 0.10, "C": 0.05}                     # riskier when lower
    assert rb.safety_scores(liq, riskier_when_higher=False) == {"A": 0.0, "B": 100.0, "C": 50.0}


def test_ties_share_half_and_missing_values_are_not_ranked():
    out = rb.safety_scores({"A": 0.3, "B": 0.3, "C": 0.9, "D": None}, riskier_when_higher=True)
    assert out == {"A": 75.0, "B": 75.0, "C": 0.0, "D": None}


def test_fewer_than_two_values_give_no_scores():
    assert rb.safety_scores({"A": 0.3, "B": None}, True) == {"A": None, "B": None}
    assert rb.safety_scores({}, True) == {}


def test_max_drawdown_and_daily_closes():
    assert rb.max_drawdown([100, 120, 90, 110, 60, 70]) == pytest.approx(0.5)     # 120 -> 60
    assert rb.max_drawdown([1, 2, 3]) == 0.0
    assert rb.max_drawdown([]) is None
    t = datetime(2026, 11, 1, tzinfo=timezone.utc)
    rows = [(t, 10), (t + timedelta(hours=23), 11), (t + timedelta(days=1), 12), (t + timedelta(days=1, hours=1), None)]
    assert rb.daily_closes(rows) == [11.0, 12.0]                 # last valid price of each UTC day


# ── inputs: fresh, stale, missing ─────────────────────────────────────────────

def _prices(days, last=NOW, start=100.0, step=1.0):
    return [(last - timedelta(days=days - 1 - i), start + step * i) for i in range(days)]


@pytest.fixture
def db_rows(monkeypatch):
    data = {
        "risk": {a: {"asset": a, "source": "ml-service", "volatility": v, "timestamp": NOW - timedelta(hours=1)}
                 for a, v in {"BTC": 0.44, "ETH": 0.59, "SOL": 0.58}.items()},
        "market": [{"asset_id": a, "volume_24h": vol, "market_cap": cap, "timestamp": NOW - timedelta(minutes=2)}
                   for a, vol, cap in (("BTC", 3e10, 1.3e12), ("ETH", 2e10, 2.2e11), ("SOL", 4e9, 8e10))],
        "prices": {"BTC": _prices(90), "ETH": _prices(90, step=-0.5), "SOL": _prices(90, step=0.2)},
    }
    monkeypatch.setattr(queries, "get_all_latest_risk_scores", lambda: data["risk"])
    monkeypatch.setattr(queries, "get_asset_market_data_all_latest", lambda: data["market"])
    monkeypatch.setattr(queries, "get_prices_since", lambda a, since: [r for r in data["prices"].get(a, []) if r[0] >= since])
    return data


def test_all_inputs_fresh_gives_three_ranked_metrics(db_rows):
    rows = {r["asset"]: r for r in rb.build_rows(rb.gather_inputs(["BTC", "ETH", "SOL"], NOW), NOW)}
    btc = rows["BTC"]["metrics"]
    assert set(btc) == {"volatility", "liquidity", "market_risk"}             # no regulatory risk
    assert btc["volatility"]["score"] == 100.0 and btc["volatility"]["raw"] == 0.44
    assert btc["volatility"]["as_of"] == "2026-11-17T00:00:00Z" and btc["volatility"]["source"].startswith("ML service")
    assert rows["ETH"]["metrics"]["liquidity"]["score"] == 100.0                # 2e10 / 2.2e11 is the highest ratio
    assert rows["ETH"]["metrics"]["market_risk"]["score"] == 0.0                # the only coin that fell
    assert btc["market_risk"]["raw"] == 0.0 and btc["market_risk"]["status"] == rb.OK
    assert all(r["source"] == rb.SOURCE and r["direction"] == "higher = safer" for r in rows.values())


def test_stale_or_missing_inputs_are_not_available_never_a_default(db_rows):
    db_rows["risk"]["SOL"]["timestamp"] = NOW - rb.ML_MAX_AGE - timedelta(minutes=1)    # stale ML row
    db_rows["market"][0]["timestamp"] = NOW - timedelta(days=2)                         # BTC snapshot too old
    db_rows["prices"]["ETH"] = _prices(40)                                              # too few daily closes
    del db_rows["risk"]["ETH"]["volatility"]                                            # no value at all
    rows = {r["asset"]: r for r in rb.build_rows(rb.gather_inputs(["BTC", "ETH", "SOL"], NOW), NOW)}

    for asset, metric in (("SOL", "volatility"), ("ETH", "volatility"), ("BTC", "liquidity"), ("ETH", "market_risk")):
        m = rows[asset]["metrics"][metric]
        assert m["score"] is None and m["status"] == rb.NOT_AVAILABLE and m["why"], (asset, metric)
    assert rows["SOL"]["metrics"]["volatility"]["raw"] is None                          # stale value not shown
    # Only BTC has a usable volatility: one value can't be ranked, so nobody gets a volatility score.
    assert rows["BTC"]["metrics"]["volatility"]["score"] is None
    assert rows["ETH"]["metrics"]["liquidity"]["ranked_among"] == 2                     # BTC left out of the ranking


def test_seeded_risk_rows_are_ignored(db_rows):
    db_rows["risk"]["BTC"]["source"] = None
    m = rb.gather_inputs(["BTC"], NOW)["BTC"]["volatility"]
    assert m["value"] is None and "ML service" in m["why"]


def test_refresh_covers_the_16_and_never_dai_or_base(db_rows, monkeypatch):
    written = []
    monkeypatch.setattr(queries, "upsert_risk_breakdown", written.append)
    out = rb.refresh_risk_breakdowns(now=NOW)
    assets = sorted(r["asset"] for r in written)
    assert assets == sorted(queries.ML_COVERED_ASSETS) and len(assets) == 16
    assert "DAI" not in assets and "BASE" not in assets
    assert "ADA" in out["not_available"]                         # no hand-made inputs for ADA: all not available
    assert rb.refresh_risk_breakdowns(now=NOW, write=False)["rows"] and len(written) == 16   # dry run writes nothing


# ── API rows and Discover ─────────────────────────────────────────────────────

def _measured_row():
    return {"asset": "BTC", "source": rb.SOURCE, "metrics": {
        "volatility": {"label": "Volatility", "score": 80.0, "raw": 0.44, "source": "s", "as_of": "2026-11-17T00:00:00Z",
                       "status": "ok", "ranked_among": 16},
        "liquidity": {"label": "Liquidity", "score": None, "raw": None, "status": "not available", "why": "old"},
        "market_risk": {"label": "Market risk", "score": 20.0, "raw": 0.3, "status": "ok"},
    }}


def test_risk_overview_rows_are_three_with_source_as_of_and_direction():
    rows = risk_overview_rows(_measured_row())
    assert [r["label"] for r in rows] == ["Volatility", "Liquidity", "Market risk"]
    assert rows[0]["level"] == "low" and rows[2]["level"] == "high"            # higher score = safer = low risk
    assert rows[1]["value"] is None and rows[1]["level"] is None and rows[1]["status"] == "not available"
    assert all(r["direction"] == "higher = safer" for r in rows)
    assert rows[0]["as_of"] == "2026-11-17T00:00:00Z" and rows[0]["ranked_among"] == 16
    assert risk_overview_rows({"asset": "BTC", "volatility_index": 40, "regulatory_risk": 50}) == []   # seeded row
    assert risk_overview_rows(None) == []


def test_discover_volatility_is_the_inverse_rank():
    assert volatility_rank(_measured_row()) == 20.0                              # 100 - safety 80
    assert volatility_rank({"volatility_index": 40}) is None                     # not a measured row
    assert volatility_rank(None) is None


@pytest.mark.parametrize("symbol", ["DAI", "BASE", "dai"])
def test_risk_route_says_not_covered_for_dai_and_base(symbol):
    with pytest.raises(HTTPException) as exc:
        get_asset_risk_breakdown(symbol)
    assert exc.value.status_code == 404 and "not covered" in exc.value.detail


def test_risk_route_hides_seeded_rows(monkeypatch):
    monkeypatch.setattr(queries, "get_latest_risk_breakdown", lambda a: {"asset": a, "volatility_index": 40})
    with pytest.raises(HTTPException) as exc:
        get_asset_risk_breakdown("BTC")
    assert exc.value.status_code == 404
    monkeypatch.setattr(queries, "get_latest_risk_breakdown",
                        lambda a: {**_measured_row(), "timestamp": NOW})
    assert get_asset_risk_breakdown("BTC")["timestamp"] == "2026-11-17T01:00:00Z"


# ── AAI = 0.4 x 50 + 0.3 x sentiment + 0.3 x risk ─────────────────────────────

@pytest.mark.parametrize("compound,confidence,risk", [(0.0, 1.0, 90.83), (0.5, 0.8, 56.31), (-0.4, 0.3, 10.0)])
def test_aai_formula_for_a_served_coin(monkeypatch, compound, confidence, risk):
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: {**PREDICT_BTC, "asset": a, "timestamp": NOW})
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: {**RISK_BTC, "asset": a, "risk_score": risk, "timestamp": NOW})
    out = aai.compute_aai_response("LINK", sentiment={"sentiment_score": compound, "confidence": confidence,
                                                      "available": True}, now=NOW)
    sentiment = confidence * (compound + 1) * 50 + (1 - confidence) * 50
    assert out["pred_score"] == 50.0                                   # no-change baseline = neutral 50 (C5)
    assert out["aai_score"] == pytest.approx(0.4 * 50 + 0.3 * sentiment + 0.3 * risk, abs=0.01)


def test_aai_formula_respects_the_age_check(monkeypatch):
    monkeypatch.setattr(aai, "_get_real_prediction", lambda a: {**PREDICT_BTC, "timestamp": NOW})
    monkeypatch.setattr(aai, "_get_real_risk", lambda a: {**RISK_BTC, "timestamp": NOW - timedelta(days=4)})
    out = aai.compute_aai_response("BTC", sentiment={"sentiment_score": 0.1, "confidence": 1.0, "available": True}, now=NOW)
    assert out["aai_score"] is None and out["stale_inputs"] == ["risk score"]
