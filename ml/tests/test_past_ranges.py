"""Phase 11 past ranges (D87, D88).

The leakage tests run on the real evaluation snapshot (ml/data/raw, read only); the API tests use the hand-made
serving fixture of test_serving.py (small made-up numbers, NOT market data). No network calls.
"""

import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.service import app
from ml.data.loader import load_raw
from ml.serving import past_ranges as pr
from ml.serving import responses as rs
from ml.tests.test_serving import write_serving_data

BAND_KEYS = ("centre", "volatility", "inner_lower", "inner_upper", "outer_lower", "outer_upper")


@pytest.fixture(scope="module")
def snapshot():
    raws = {a: load_raw(a) for a in config.ASSETS}
    return raws, {a: pr.series(r) for a, r in raws.items()}


def _cut(raw: pd.DataFrame, t0: pd.Timestamp) -> pd.DataFrame:
    return raw[raw["timestamp"] <= t0].reset_index(drop=True)


def _sample(points, every):
    """Every `every`-th point plus the first 40 (the warm-up edge) and the last 5."""
    idx = sorted(set(range(0, len(points), every)) | set(range(min(40, len(points)))) |
                 set(range(max(0, len(points) - 5), len(points))))
    return [points[i] for i in idx]


@pytest.mark.parametrize("asset", config.ASSETS)
def test_each_value_equals_the_result_from_data_cut_at_d_minus_30(snapshot, asset):
    """Leakage: the point for day d, from the full history, equals the cone computed from bars <= d - 30 only."""
    raws, series = snapshot
    pts = _sample(series[asset], 7)
    assert len(pts) > 300
    for p in pts:
        t0 = pd.Timestamp(p["made_on"], tz="UTC")
        assert t0 == pd.Timestamp(p["date"], tz="UTC") - pd.Timedelta(days=30)
        cut = _cut(raws[asset], t0)
        feats = rs.serving_table(cut)
        assert feats.index[-1] == t0
        ref = pr.range_made_on(float(cut["close"].iloc[-1]), float(feats[config.RISK_VOL_COLUMN].iloc[-1]))
        assert {k: p[k] for k in BAND_KEYS} == ref, p["date"]


@pytest.mark.parametrize("asset", config.ASSETS)
def test_volatility_equals_what_risk_served_on_made_on(snapshot, asset):
    """The width uses the volatility /risk would have served on made_on (the live code path, all pooled assets cut
    at made_on), so the past range is the cone the page would have drawn then."""
    raws, series = snapshot
    for p in series[asset][::90] + series[asset][-1:]:
        t0 = pd.Timestamp(p["made_on"], tz="UTC")
        feats = {a: rs.serving_table(_cut(r, t0)) for a, r in raws.items()
                 if (r["timestamp"] <= t0).sum() > config.WARMUP_ROWS}
        served = rs.risk(asset, t0 + pd.Timedelta(hours=25), feats)
        assert p["volatility"] == served["volatility"], p["date"]


def test_future_bars_do_not_change_a_past_range(snapshot):
    """Changing every bar after made_on changes only that point's close, never its range."""
    raws, series = snapshot
    raw = raws["btc"]
    p = series["btc"][-200]
    t0 = pd.Timestamp(p["made_on"], tz="UTC")
    poisoned = raw.copy()
    after = poisoned["timestamp"] > t0
    for c in ("open", "high", "low", "close"):
        poisoned.loc[after, c] = poisoned.loc[after, c] * 3.0
    poisoned.loc[after, "volume"] = poisoned.loc[after, "volume"] * 0.1
    q = next(x for x in pr.series(poisoned) if x["date"] == p["date"])
    assert {k: q[k] for k in BAND_KEYS} == {k: p[k] for k in BAND_KEYS}
    assert q["close"] == pytest.approx(3 * p["close"])


def test_points_are_daily_and_start_after_the_warm_up(snapshot):
    raws, series = snapshot
    for a, pts in series.items():
        dates = pd.to_datetime([p["date"] for p in pts])
        assert (dates.to_series().diff().dropna() == pd.Timedelta(days=1)).all()
        first_vol = rs.serving_table(raws[a])[config.RISK_VOL_COLUMN].first_valid_index()
        assert pts[0]["made_on"] == first_vol.strftime("%Y-%m-%d")
        assert pts[-1]["date"] == raws[a]["timestamp"].iloc[-1].strftime("%Y-%m-%d")


def test_band_is_the_frontend_cone_formula_by_hand():
    # coneBand(100, 0.73 / sqrt(365), 30, 1.2816) worked by hand: k = 1.2816 x 0.038210 x 5.477226 = 0.268219
    lo, hi = pr.band(100.0, 0.73, config.CONE_Z_OUTER)
    k = 1.2816 * (0.73 / math.sqrt(365)) * math.sqrt(30)
    assert k == pytest.approx(0.268219, abs=1e-6)
    assert (lo, hi) == pytest.approx((100 * math.exp(-k), 100 * math.exp(k)))
    assert lo * hi == pytest.approx(100 ** 2)           # centred in log price: no drift, no direction


def test_constants_match_the_cone():
    assert (config.PAST_RANGE_LAG_DAYS, config.CONE_Z_INNER, config.CONE_Z_OUTER) == (30, 0.6745, 1.2816)
    assert config.RISK_VOL_COLUMN == "vol_30d"           # D82: method unchanged


def test_range_is_none_without_a_usable_vol():
    assert pr.range_made_on(100.0, float("nan")) is None
    assert pr.range_made_on(100.0, 0.0) is None
    assert pr.range_made_on(0.0, 0.02) is None


def test_coverage_by_hand():
    def pt(close):
        return {"inner_lower": 90, "inner_upper": 110, "outer_lower": 80, "outer_upper": 120, "close": close}
    c = pr.coverage([pt(100), pt(110), pt(115), pt(79), pt(120)])
    assert c == {"days": 5, "inside_50": 2, "inside_80": 4, "share_50": 0.4, "share_80": 0.8}
    assert pr.coverage([])["share_80"] is None


@pytest.fixture
def served(monkeypatch, tmp_path):
    raw_dir, report_dir = tmp_path / "raw", tmp_path / "validation"
    monkeypatch.setattr(config, "ML_RAW_DIR", raw_dir)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", report_dir)
    write_serving_data(raw_dir, report_dir)
    return TestClient(app)


def test_api_validates_against_the_contract(served):
    body = served.get("/past-ranges/BTC").json()          # check() inside the route raises on any violation
    assert body["asset"] == "BTC" and body["lag_days"] == 30 and body["volatility_measure"] == "vol_30d"
    assert "Not a price prediction" in body["note"]
    assert len(body["points"]) == 400 - config.WARMUP_ROWS - 30
    last = served.get("/past-ranges/btc?days=10").json()["points"]
    assert last == body["points"][-10:]
    assert served.get("/past-ranges/btc?days=0").json()["points"] == []


def test_api_errors(served):
    assert served.get("/past-ranges/doge").status_code == 404
    assert served.get("/past-ranges/btc?days=-1").status_code == 422


def test_api_503_when_the_serving_gate_fails(served, monkeypatch, tmp_path):
    (config.ML_VALIDATION_DIR / "btc_validation.json").write_text('{"passed": false}', encoding="utf-8")
    assert served.get("/past-ranges/btc").status_code == 503
