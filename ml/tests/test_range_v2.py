"""Phase 9 step 9.3 range: interval metrics, the band specs, quantile LightGBM, and no look-ahead (D48).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
The LightGBM test skips when lightgbm is not installed (the serving environment).
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import interval_metrics as im
from ml.evaluation.part_runner import high_vol_mask
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.walkforward import make_folds
from ml.evaluation.walkforward_history import run_history_folds
from ml.features.features import ewma_vol
from ml.models import range_v2

N, B2, MIN_TRAIN = 300, 255, 100


def _raw(n_feature_rows=N):
    """Hand-made daily bars (not market data): a wave on a slow trend plus a wobble."""
    i = np.arange(n_feature_rows + config.WARMUP_ROWS, dtype=float)
    close = 100 + 15 * np.sin(i / 9) + 0.2 * i + 3 * np.cos(i / 2.3)
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _data(h, raw=None):
    raw = _raw() if raw is None else raw
    return dev_data(raw.iloc[:config.WARMUP_ROWS + B2].copy(), h)


def test_winkler_by_hand():
    lo, hi = np.array([-1.0, -1.0, -1.0]), np.array([1.0, 1.0, 1.0])
    y = np.array([0.0, -2.0, 3.0])
    # alpha = 0.2 -> penalty 2 / 0.2 = 10 per unit outside
    np.testing.assert_allclose(im.winkler(lo, hi, y), [2.0, 2.0 + 10.0, 2.0 + 20.0])
    s = im.summary(lo, hi, y, np.array([True, False, True]))
    assert s["coverage"] == pytest.approx(1 / 3) and s["lower_tail_miss"] == pytest.approx(1 / 3)
    assert s["upper_tail_miss"] == pytest.approx(1 / 3) and s["coverage_high_vol"] == pytest.approx(0.5)
    assert s["mean_width"] == 2.0 and s["n_crossed"] == 0


def test_crossed_bounds_are_sorted_and_counted():
    lo, hi, n = im.ordered([0.5, -1.0], [-0.5, 1.0])
    np.testing.assert_array_equal(lo, [-0.5, -1.0])
    np.testing.assert_array_equal(hi, [0.5, 1.0])
    assert n == 1


def test_pass_conditions():
    ok = {"coverage": 0.80, "lower_tail_miss": 0.10, "upper_tail_miss": 0.10}
    assert im.passes(ok)["coverage_in_bounds"] and im.passes(ok)["tails_within_max"]
    assert not im.passes({**ok, "coverage": 0.86})["coverage_in_bounds"]
    assert not im.passes({**ok, "lower_tail_miss": 0.16})["tails_within_max"]


@pytest.mark.parametrize("h", [7, 30])
def test_bands_match_their_formula(h):
    data = _data(h)
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    specs = {k: v for k, v in range_v2.specs(h).items() if not k.startswith("qlgbm")}
    pooled, _ = run_history_folds(data, folds, specs, B2, h, 1)
    rows = pooled["row"].to_numpy()
    z = range_v2.Z["hi"]
    vol30 = data["vol_30d"].to_numpy()[rows]
    ew = ewma_vol(data["close"]).to_numpy()[rows]
    np.testing.assert_allclose(pooled["pred:vol30_band:hi"], z * vol30 * np.sqrt(h))
    np.testing.assert_allclose(pooled["pred:vol30_band:lo"], -z * vol30 * np.sqrt(h))
    np.testing.assert_allclose(pooled["pred:ewma_band:hi"], z * ew * np.sqrt(h))
    assert z == pytest.approx(1.2815515655446004)


@pytest.mark.parametrize("h", [7, 30])
def test_bands_at_t_ignore_closes_after_t(h):
    raw = _raw()
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    specs = {k: v for k, v in range_v2.specs(h).items() if not k.startswith("qlgbm")}
    base, _ = run_history_folds(_data(h, raw), folds, specs, B2, h, 1)
    t = folds[2].origin
    changed = raw.copy()
    changed.loc[config.WARMUP_ROWS + t + 1:, ["open", "high", "low", "close", "volume"]] *= 2.3
    after, _ = run_history_folds(_data(h, changed), folds, specs, B2, h, 1)
    cols = [c for c in base.columns if c.startswith("pred:")]
    upto = base["row"] <= t
    np.testing.assert_array_equal(base.loc[upto, cols].to_numpy(), after.loc[upto, cols].to_numpy())
    assert not np.array_equal(base.loc[~upto, cols].to_numpy(), after.loc[~upto, cols].to_numpy())


def test_quantile_lightgbm_runs_and_is_mostly_ordered():
    pytest.importorskip("lightgbm")
    h = 7
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    specs = {k: v for k, v in range_v2.specs(h).items() if k.startswith("qlgbm_l7")}
    pooled, _ = run_history_folds(_data(h), folds, specs, B2, h, 1)
    lo, hi = pooled["pred:qlgbm_l7:lo"].to_numpy(), pooled["pred:qlgbm_l7:hi"].to_numpy()
    assert np.isfinite(lo).all() and np.isfinite(hi).all() and np.mean(lo < hi) > 0.5


def test_high_vol_mask_uses_train_row_thresholds():
    h = 7
    data = _data(h)
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    pooled = pd.DataFrame({"origin": [f.origin for f in folds for _ in f.predict],
                           "row": [i for f in folds for i in f.predict]})
    mask = high_vol_mask(data, folds, pooled)
    f = folds[3]
    th = np.percentile(data["vol_30d"].iloc[f.train], config.RISK_PERCENTILES[1])
    rows = (pooled["origin"] == f.origin).to_numpy()
    np.testing.assert_array_equal(mask[rows], data["vol_30d"].to_numpy()[list(f.predict)] > th)
