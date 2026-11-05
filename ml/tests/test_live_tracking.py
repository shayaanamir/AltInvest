"""Tests for live tracking (Phase 6d): the prediction log and the forward scorecard.

All bars are HAND-MADE (test_refresh's fixture bars), NOT market data. fetch.fetch is monkeypatched, so there are
no network calls; every file goes to temporary serving directories, and the snapshot is a temporary stand-in.
"""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.service import app
from ml.data import fetch, refresh
from ml.evaluation import live_score
from ml.serving import prediction_log
from test_refresh import fake_fetch

DAY0 = pd.Timestamp("2026-01-01", tz="UTC")


@pytest.fixture
def dirs(monkeypatch, tmp_path):
    raw, val = tmp_path / "serving" / "raw", tmp_path / "serving" / "validation"
    monkeypatch.setattr(config, "ML_RAW_DIR", raw)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", val)
    monkeypatch.setattr(config, "EVALUATION_RAW_DIR", tmp_path / "snapshot" / "raw")
    monkeypatch.setattr(config, "EVALUATION_VALIDATION_DIR", tmp_path / "snapshot" / "reports")
    return raw, val


def _closes(values) -> pd.Series:
    return pd.Series(values, index=DAY0 + pd.to_timedelta(np.arange(len(values)), unit="D"), dtype=float)


def _row(day: int, asset="btc", signal="UNCERTAIN", vol=0.02, pred=0.0) -> dict:
    return {"asset": asset, "last_bar": (DAY0 + pd.Timedelta(days=day)).strftime("%Y-%m-%d"), "close": 0.0,
            "vol_30d": vol, "prediction_30d": pred, "signal": signal}


def test_realised_return_by_hand_and_pending_before_the_horizon():
    c = _closes(100 * 1.01 ** np.arange(40))                 # +1% a day: ln return over 30 days = 30 ln 1.01
    out = live_score.score_rows([_row(0), _row(9), _row(10)], {"btc": c})
    assert out[0]["status"] == "scored" and out[1]["status"] == "scored"
    assert out[0]["realised_log_return"] == pytest.approx(30 * np.log(1.01))
    assert out[0]["realised_vol_30d"] == pytest.approx(0.0, abs=1e-12)
    assert out[2]["status"] == "pending" and out[2]["scorable_from"] == "2026-02-10"   # needs bar 40, last is 39


def test_no_bar_after_t_plus_30_is_read():
    """Leakage test: bars after t+30 never change the score of t; bar t+30 itself does (not vacuous)."""
    base = 100 * np.exp(np.cumsum(0.01 * np.sin(np.arange(45))))
    later = base.copy()
    later[31:] *= 5
    a, b = (live_score.score_rows([_row(0)], {"btc": _closes(x)})[0] for x in (base, later))
    assert a["realised_log_return"] == b["realised_log_return"] and a["realised_vol_30d"] == b["realised_vol_30d"]
    moved = base.copy()
    moved[30] *= 1.1
    assert live_score.score_rows([_row(0)], {"btc": _closes(moved)})[0]["realised_log_return"] != \
        a["realised_log_return"]


def test_summary_nulls_when_there_is_nothing_to_measure():
    c = _closes(100 * 1.01 ** np.arange(40))
    s = live_score._summary([r for r in live_score.score_rows([_row(0), _row(1)], {"btc": c})])
    assert s["n_scored"] == 2 and s["risk_spearman_persistence"] is None       # fewer than 3 rows
    assert s["direction_calls"] == 0 and s["direction_hit_rate"] is None        # UNCERTAIN is never a call
    assert s["price_mae_log_return_served"] == s["price_mae_log_return_last_value"]   # served 0% = last value
    assert live_score._summary([]) == {"n_scored": 0}


def test_direction_hit_rate_counts_buy_and_sell_only():
    c = _closes(100 * 1.01 ** np.arange(40))                                    # every window rises
    rows = live_score.score_rows([_row(0, signal="BUY"), _row(1, signal="SELL"), _row(2)], {"btc": c})
    assert live_score._summary(rows)["direction_hit_rate"] == 0.5


def test_refresh_logs_one_row_per_asset_per_bar_and_is_idempotent(dirs, monkeypatch):
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    rows = prediction_log.read_log()
    assert sorted(r["asset"] for r in rows) == sorted(config.ASSETS)
    assert {r["prediction_30d"] for r in rows} == {0.0} and {r["signal"] for r in rows} == {"UNCERTAIN"}
    assert refresh.run_once() == 0                                              # same bars again: nothing added
    assert len(prediction_log.read_log()) == len(config.ASSETS)
    monkeypatch.setattr(fetch, "fetch", fake_fetch(401))                       # one more day
    assert refresh.run_once() == 0
    assert len(prediction_log.read_log()) == 2 * len(config.ASSETS)


def test_live_scorecard_endpoint_scores_nothing_until_the_horizon(dirs, monkeypatch):
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    refresh.run_once()
    body = TestClient(app).get("/debug/live-scorecard").json()
    assert body["n_logged"] == len(config.ASSETS) and body["n_scored"] == 0
    assert body["n_pending"] == len(config.ASSETS) and "nothing is scored" in body["note"]


def test_logged_rows_are_scored_once_the_bars_arrive(dirs, monkeypatch):
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    refresh.run_once()
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400 + config.HORIZON_DAYS))
    refresh.run_once()
    card = live_score.build()
    assert card["n_scored"] == len(config.ASSETS)                              # the first day's rows
    assert card["all_assets"]["n_scored"] == len(config.ASSETS)


def test_log_and_live_score_refuse_the_evaluation_snapshot(dirs, monkeypatch):
    monkeypatch.setattr(config, "ML_RAW_DIR", config.EVALUATION_RAW_DIR)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", config.EVALUATION_VALIDATION_DIR)
    with pytest.raises(refresh.SnapshotProtected):
        prediction_log.append_served(DAY0.to_pydatetime())
    with pytest.raises(SystemExit, match="evaluation snapshot"):
        live_score.main()
    assert not (config.EVALUATION_VALIDATION_DIR / config.PREDICTION_LOG_FILE).exists()


def test_log_rows_are_json_lines(dirs, monkeypatch):
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    refresh.run_once()
    lines = prediction_log.log_path().read_text(encoding="utf-8").splitlines()
    assert all(json.loads(x)["model_version"] == config.MODEL_VERSION_PRICE for x in lines)


def _scored(asset, days, ewma, persistence, realised):
    """Hand-made scored rows (not market data), one per day offset in `days`."""
    return [{"asset": asset, "last_bar": (DAY0 + pd.Timedelta(days=d)).strftime("%Y-%m-%d"), "ewma_vol": ewma,
             "vol_30d": persistence, "realised_vol_30d": realised, "status": "scored"} for d in days]


def test_risk_monitor_needs_6_non_overlapping_windows_then_alerts():
    daily = _scored("btc", range(0, 151), 0.02, 0.03, 0.02)           # 151 daily rows -> windows at 0, 30, ..., 150
    assert len(live_score.non_overlapping(daily)) == 6
    few = live_score.risk_monitor(daily[:150])                          # windows at 0..120: only 5
    assert few["per_asset"]["btc"]["status"] == "insufficient data" and "qlike_ewma" not in few["per_asset"]["btc"]
    ok = live_score.risk_monitor(daily)["per_asset"]["btc"]
    assert ok["status"] == "ok" and ok["qlike_ewma"] < ok["qlike_persistence"]     # EWMA = realised here
    worse = live_score.risk_monitor(_scored("btc", range(0, 151), 0.05, 0.02, 0.02))["per_asset"]["btc"]
    assert worse["status"] == "ALERT" and worse["n_non_overlapping_windows"] == 6
    assert live_score.risk_monitor(daily)["per_asset"]["eth"]["status"] == "insufficient data"   # no rows


def test_risk_monitor_ignores_rows_logged_before_ewma():
    old = [{k: v for k, v in r.items() if k != "ewma_vol"} for r in _scored("sol", range(0, 400), 0.02, 0.03, 0.02)]
    res = live_score.risk_monitor(old)["per_asset"]["sol"]
    assert res["n_scored"] == 0 and res["status"] == "insufficient data"
