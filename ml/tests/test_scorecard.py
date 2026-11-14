"""Tests for the offline scorecard (Phase 6d): every number is copied from its source report, nothing recomputed.

Reads the committed reports under ml/reports (no data, no network). Nothing is written: build() and markdown()
are called directly; the committed scorecard.json is only read.
"""

import json

import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.service import app
from ml.evaluation import scorecard as sc


@pytest.fixture(scope="module")
def card():
    return sc.build()


def _report(asset, name):
    return json.loads((sc.REPORTS / asset / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("asset", config.ASSETS)
@pytest.mark.parametrize("model", list(sc.MODELS))
def test_model_numbers_equal_the_source_report(card, asset, model):
    report, _, mfield, _, bfield, dfield, _ = sc.MODELS[model]
    src = _report(asset, report)
    row = card["assets"][asset]["models"][model]
    conf = src["confirmation_last_40pct"]
    assert row["model"] == conf[mfield] and row["baseline"] == conf[bfield]
    assert row["gain_ci95"] == {k: conf[dfield][k] for k in ("estimate", "low", "high")}
    assert row["approved"] is src["verdict"]["approved"] and row["top_config"] == src["verdict"]["top_config"]
    assert row["n_effective"] == conf["n_effective"]


@pytest.mark.parametrize("asset", config.ASSETS)
def test_backtest_numbers_equal_the_source_report(card, asset):
    src = _report(asset, "backtest")
    rows = card["assets"][asset]["backtest"]["rows"]
    for name, group in sc.BACKTEST_ROWS:
        for f in ("mean_window_return", "cumulative_return", "max_drawdown", "sharpe_annualised", "hit_rate"):
            assert rows[name][f] == src[group][name][f]
    assert rows["served"]["trades"] == src["strategies"]["served"]["trades"]
    assert card["assets"][asset]["backtest"]["n_windows"] == src["protocol"]["n_windows"]


def test_served_flags_follow_config_and_approval_is_not_serving(card):
    for a, x in card["assets"].items():
        for m, r in x["models"].items():
            assert r["served"] is (m == "direction" and config.DIRECTION_SERVED[a])
    s = card["summary"]
    assert s["models_total"] == len(config.ASSETS) * len(sc.MODELS)
    assert s["models_approved"] == sum(r["approved"] for x in card["assets"].values() for r in x["models"].values())


def test_markdown_lists_every_asset_and_model(card):
    md = sc.markdown(card)
    for a, x in card["assets"].items():
        assert f"## {a.upper()}" in md and x["verdict"] in md
        for m in sc.MODELS:
            assert f"| {m} |" in md


def test_committed_scorecard_matches_the_reports(card):
    """The committed ml/reports/scorecard.json was generated from the current reports (rerun the module if not)."""
    committed = json.loads(sc.OUT_JSON.read_text(encoding="utf-8"))
    assert committed["assets"] == card["assets"] and committed["summary"] == card["summary"]


def test_debug_scorecard_endpoint_serves_the_file_not_an_asset():
    r = TestClient(app).get("/debug/scorecard")
    assert r.status_code == 200
    assert r.json() == json.loads(sc.OUT_JSON.read_text(encoding="utf-8"))


def test_phase9_nothing_served_after_d82(card):
    """D82: the logged D49 EWMA risk approvals do not stand under top-only (D81); the ETH logistic regression
    direction approval does (it is not served anyway, D33/D50). No Phase 9 row is served."""
    for a, x in card["assets"].items():
        assert [r for r in x["phase9"] if r["served"]] == []
        top = [(r["part"], r["model"]) for r in x["phase9"] if r["approved_top_only"]]
        assert top == ([("direction", "logreg")] if a == "eth" else [])           # D82: only ETH direction stands
        src = {(v["model"], v["horizon"]): v for v in _report(a, "walkforward_risk_v2")["verdict_table"]}
        row = next(r for r in x["phase9"] if r["part"] == "risk" and r["model"] == "ewma" and r["horizon"] == 30)
        assert row["model_value"] == src[("ewma", 30)]["model_qlike"]
        assert row["approved"] == src[("ewma", 30)]["approved"]                  # the logged D49 verdict, unchanged
    assert card["summary"]["phase9_served"] == 0 and card["summary"]["phase9_approved_top_only"] == 1
    assert card["summary"]["phase9_approved"] > 0                                # BTC/ETH EWMA, logged under D49


def test_nft_section_copies_the_phase_10_reports(card):
    """Phase 10 close: the scorecard's NFT rows are copied from ml/reports/nft and match the committed file."""
    rows = {(r["part"], r["model"]): r for r in card["nft"]["rows"]}
    sealed = json.loads((sc.REPORTS / "nft" / "sealed_fair_value.json").read_text(encoding="utf-8"))["verdict"]
    s = rows[("nft fair value (sealed test, once)", "served setup")]
    assert s["model_value"] == sealed["mdape"]["served"] and s["approved"] is sealed["pass"] is True
    assert rows[("nft risk (pooled, h = 30)", "ewma")]["served"] is False                      # D73
    committed = json.loads(sc.OUT_JSON.read_text(encoding="utf-8"))
    assert committed["nft"] == card["nft"]
