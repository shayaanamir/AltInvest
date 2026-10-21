"""Tests for the serving layer (Phase 6a; D27, D33, D35, D36, D37).

All fixtures below are small HAND-MADE numbers, NOT market data. No network calls. Feature tables are built
by hand (only vol_30d and ret_1d are read); the loading tests write hand-made raw bars and matching
validation reports into temporary serving directories (config.ML_RAW_DIR, config.ML_VALIDATION_DIR; D40).
"""

import json
import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.service import app
from ml.evaluation.risk_mapping_check import historical_scores
from ml.features.features import build_features
from ml.labels import labels
from ml.serving import responses as rs
from ml.signal.signal_logic import NOTE_NOT_SERVED

DAY0 = pd.Timestamp("2026-10-15", tz="UTC")
HOUR = pd.Timedelta(hours=1)


def _feats(vols, rets=None, start=DAY0) -> pd.DataFrame:
    """Hand-made feature table: one row per day from `start`."""
    idx = start + pd.to_timedelta(np.arange(len(vols)), unit="D")
    return pd.DataFrame({"vol_30d": vols, "ret_1d": rets if rets is not None else np.zeros(len(vols))}, index=idx)


def _now(feats: pd.DataFrame, hours_after_close: float = 1) -> pd.Timestamp:
    return feats.index[-1] + pd.Timedelta(days=1) + hours_after_close * HOUR


def _two_assets():
    return {"aaa": _feats([0.01, 0.03, 0.02]), "bbb": _feats([0.02, 0.05, 0.04])}


@pytest.fixture
def served_fixture_assets(monkeypatch):
    for a in ("aaa", "bbb"):
        monkeypatch.setitem(config.DIRECTION_SERVED, a, False)


def test_d36_pooled_percentile_by_hand():
    feats = _two_assets()
    now = _now(feats["aaa"])
    # aaa today 0.02 in pool [0.01, 0.03, 0.02, 0.02, 0.05, 0.04]: 1 below, 2 equal -> p = (1 + 0.5 * 2) / 6 = 1/3
    a = rs.risk_inputs("aaa", now, feats)
    assert a["pool_size"] == 6
    assert a["p"] == pytest.approx(1 / 3) and a["risk_score"] == pytest.approx(200 / 3)
    assert rs.risk("aaa", now, feats)["risk_score"] == pytest.approx(66.666667, abs=1e-6)
    # bbb today 0.04: 4 below, 1 equal -> p = 4.5 / 6 = 0.75 -> 25
    assert rs.risk_inputs("bbb", now, feats)["risk_score"] == pytest.approx(25.0)


def test_d36_ties_count_half():
    assert rs.pooled_risk_score(0.02, [0.01, 0.02, 0.02, 0.03]) == pytest.approx((50.0, 0.5))
    assert rs.pooled_risk_score(0.03, [0.01, 0.03]) == pytest.approx((25.0, 0.75))
    feats = {"aaa": _feats([0.02] * 3), "bbb": _feats([0.02] * 3)}
    assert rs.risk_inputs("aaa", _now(feats["aaa"]), feats)["risk_score"] == pytest.approx(50.0)


def test_d36_pool_excludes_dates_after_today():
    """Leakage test: rows of other assets dated after today never change today's risk_score."""
    aaa = _feats([0.01, 0.03, 0.02])
    now = _now(aaa)
    base = rs.risk_inputs("aaa", now, {"aaa": aaa, "bbb": _feats([0.02, 0.05, 0.04, 0.001, 0.001])})
    future = rs.risk_inputs("aaa", now, {"aaa": aaa, "bbb": _feats([0.02, 0.05, 0.04, 9.0, 0.0])})
    assert base["pool_size"] == future["pool_size"] == 6
    assert future["risk_score"] == base["risk_score"]
    past = rs.risk_inputs("aaa", now, {"aaa": aaa, "bbb": _feats([0.02, 0.001, 0.04, 0.001, 0.001])})
    assert past["risk_score"] != base["risk_score"]          # the test is not vacuous: past rows do count


def test_d37_sharpe_by_hand_and_null_under_365_returns():
    # 365 returns cycling 0.001 x (-1, 0, 1, 2, 3): mean 0.001, sample var 0.001^2 x 730/364,
    # so sharpe = sqrt(365) / sqrt(730/364) = sqrt(182). Ten older returns of 0.5 must be ignored.
    cycle = [0.001 * ((i % 5) - 1) for i in range(365)]
    f = _feats([0.02] * 375, [0.5] * 10 + cycle)
    assert rs.sharpe_trailing(f["ret_1d"]) == pytest.approx(math.sqrt(182))
    assert rs.risk("aaa", _now(f), {"aaa": f})["sharpe_ratio"] == pytest.approx(math.sqrt(182), abs=1e-6)
    short = _feats([0.02] * 364, cycle[:364])
    assert rs.sharpe_trailing(short["ret_1d"]) is None
    assert rs.risk("aaa", _now(short), {"aaa": short})["sharpe_ratio"] is None


def test_volatility_is_annualised():
    f = _feats([0.05, 0.02])
    # 0.02 x sqrt(365) = 0.02 x 19.104973 = 0.382099
    assert rs.risk("aaa", _now(f), {"aaa": f})["volatility"] == pytest.approx(0.382099, abs=1e-6)


@pytest.mark.usefixtures("served_fixture_assets")
def test_staleness_note_47h_vs_49h():
    feats = _two_assets()                                   # last bar 2026-10-17, closed 2026-10-18T00:00Z
    fresh, stale = _now(feats["aaa"], 47), _now(feats["aaa"], 49)
    assert str(fresh) == "2026-10-19 23:00:00+00:00"
    for build in (rs.risk, rs.predict):
        assert "data stale" not in build("aaa", fresh, feats)["note"]
        assert build("aaa", stale, feats)["note"].endswith("data stale: last bar 2026-10-17")
    assert rs.risk_inputs("aaa", stale, feats)["age_hours"] == pytest.approx(49)


@pytest.mark.usefixtures("served_fixture_assets")
def test_predict_d35_fields_and_signal_from_generate_signal(monkeypatch):
    feats = _two_assets()
    now = _now(feats["aaa"])
    calls = []

    def stub(asset, *args, **kwargs):
        calls.append(asset)
        return {"signal": "UNCERTAIN", "confidence": None, "note": "STUB NOTE"}

    monkeypatch.setattr(rs, "generate_signal", stub)
    p = rs.predict("aaa", now, feats)
    assert calls == ["aaa"]
    assert p["prediction_30d"] == 0 and p["model_version"] == config.MODEL_VERSION_PRICE
    assert all(p[k] is None for k in ("predicted_price", "lower_bound", "upper_bound", "confidence", "trend",
                                      "agreement", "boosted_confidence", "ensemble_price"))
    assert p["note"].startswith(rs.NOTE_PRICE) and "STUB NOTE" in p["note"]
    assert p["risk_score"] == rs.risk("aaa", now, feats)["risk_score"]
    assert p["timestamp"] == "2026-10-18T01:00:00Z"
    monkeypatch.undo()
    monkeypatch.setitem(config.DIRECTION_SERVED, "aaa", False)
    real = rs.predict("aaa", now, feats)
    assert (real["signal"], real["confidence"]) == ("UNCERTAIN", None) and NOTE_NOT_SERVED in real["note"]


def _raw(asset: str, n: int = 400) -> pd.DataFrame:
    """Hand-made daily bars (not market data): a trend plus two waves."""
    i = np.arange(n, dtype=float)
    close = 100 + 0.1 * i + 8 * np.sin(i / 7) + 3 * np.cos(i * 1.3)
    return pd.DataFrame({
        "asset": asset, "timestamp": pd.Timestamp("2025-09-13", tz="UTC") + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close, "volume": 1000 + 50 * np.sin(i),
    })


def write_serving_data(raw_dir, validation_dir, assets=config.ASSETS, n: int = 400) -> None:
    """Hand-made CSVs and matching passed validation reports (rows and last timestamp, D40)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    for a in assets:
        df = _raw(a, n)
        df.assign(timestamp=df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_csv(
            raw_dir / f"{a}_1d.csv", index=False)
        last = df["timestamp"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ")
        report = {"passed": True, "rows": n, "last_timestamp": last}
        (validation_dir / f"{a}_validation.json").write_text(json.dumps(report), encoding="utf-8")


@pytest.fixture
def reports(monkeypatch, tmp_path):
    """Temporary serving directories holding hand-made bars and passed reports, instead of the snapshot."""
    raw_dir, report_dir = tmp_path / "raw", tmp_path / "validation"
    monkeypatch.setattr(config, "ML_RAW_DIR", raw_dir)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", report_dir)
    write_serving_data(raw_dir, report_dir)
    return report_dir


def test_refuses_when_any_pooled_asset_failed_validation(reports):
    now = pd.Timestamp("2026-10-20", tz="UTC")
    assert set(rs.feature_tables()) == set(config.ASSETS)
    (reports / "sol_validation.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    with pytest.raises(rs.NotServable, match="sol_validation.json did not pass"):
        rs.risk("btc", now)
    (reports / "sol_validation.json").unlink()
    with pytest.raises(rs.NotServable, match="sol_validation.json is missing"):
        rs.predict("btc", now)


@pytest.mark.usefixtures("reports")
def test_no_label_is_built_when_serving(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("serving must never build labels")

    for name in ("build_labels", "fwd_return_30d", "fwd_vol_30d"):
        monkeypatch.setattr(labels, name, forbidden)
        assert not hasattr(rs, name)
    now = pd.Timestamp("2026-10-20", tz="UTC")
    for build in (rs.risk, rs.predict, rs.debug):
        assert "fwd_" not in json.dumps(build("btc", now))


def test_check_scores_match_serving_on_that_date():
    """The read-only check (ml.evaluation.risk_mapping_check) uses the served D36 mapping, cut at each row's date."""
    fa, fb = build_features(_raw("aaa")), build_features(_raw("bbb", 380))
    fb = fb * 1.3
    pool = {"aaa": fa["vol_30d"], "bbb": fb["vol_30d"]}
    for r in (5, 200, len(fb) - 1, len(fa) - 1):
        served = rs.risk_inputs("aaa", _now(fa.iloc[:r + 1]), {"aaa": fa.iloc[:r + 1], "bbb": fb})
        assert historical_scores(fa["vol_30d"], pool, range(r, r + 1))[0] == pytest.approx(served["risk_score"])


def _set_report(path, **changes):
    path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), **changes}), encoding="utf-8")


def _gap_in_bars(raw, rep):
    """Drop one middle day from the btc CSV and update its report to match, so only the gap is wrong."""
    path = raw / "btc_1d.csv"
    df = pd.read_csv(path).drop(index=100)
    df.to_csv(path, index=False)
    _set_report(rep / "btc_validation.json", rows=len(df))


GATE_BREAKS = {     # (how the btc data is broken, the asset the 503 must name)
    "missing_csv": (lambda raw, rep: (raw / "btc_1d.csv").unlink(), "btc"),
    "missing_report": (lambda raw, rep: (rep / "btc_validation.json").unlink(), "btc"),
    "row_mismatch": (lambda raw, rep: _set_report(rep / "btc_validation.json", rows=401), "btc"),
    "last_timestamp_mismatch": (lambda raw, rep: _set_report(rep / "btc_validation.json",
                                                             last_timestamp="2026-10-16T00:00:00Z"), "btc"),
    "unreadable_report": (lambda raw, rep: (rep / "btc_validation.json").write_text("{not json"), "btc"),
    "report_not_passed": (lambda raw, rep: _set_report(rep / "btc_validation.json", passed=False), "btc"),
    "other_asset_missing_csv": (lambda raw, rep: (raw / "sol_1d.csv").unlink(), "sol"),
    "gap_in_bars": (_gap_in_bars, "btc"),                   # Phase 6c: build_features refuses gaps -> 503
}


@pytest.mark.parametrize("broken", list(GATE_BREAKS))
def test_serving_gate_failures_are_503_through_the_api(reports, broken):
    """D40: every data problem is a 503 naming the asset, never a 500 (TestClient re-raises server errors)."""
    client = TestClient(app)
    assert client.get("/risk/btc").status_code == 200          # control: the hand-made data is servable
    breaker, named = GATE_BREAKS[broken]
    breaker(config.ML_RAW_DIR, reports)
    for route in ("predict", "risk", "debug"):
        r = client.get(f"/{route}/btc")
        assert r.status_code == 503, (route, r.text)
        assert r.json()["detail"].startswith(f"{named}: ")
