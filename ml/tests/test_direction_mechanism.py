"""Tests for ml.evaluation.direction_mechanism (Phase 5a).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.direction_mechanism import mechanism_checks, pooled_predictions
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.walkforward import SealedTestError

H, W = config.HORIZON_DAYS, config.WARMUP_ROWS


def test_three_correlations_have_the_expected_sign():
    # hand-made: P(FLAT) falls as vol and |return| rise; P(UP) - P(DOWN) rises with the return
    t = np.arange(120, dtype=float)
    fwd = 0.2 * np.sin(t / 5)                                   # forward returns, both signs
    vol = 0.02 + 0.01 * np.abs(np.sin(t / 5)) + 0.001 * np.cos(t)
    p_flat = 0.6 - 2.0 * np.abs(fwd) * 0.9 - 0.5 * (vol - 0.02)
    tilt = 0.5 * fwd                                            # P(UP) - P(DOWN)
    rest = 1 - p_flat
    prob = np.c_[(rest - tilt) / 2, p_flat, (rest + tilt) / 2]   # DOWN, FLAT, UP
    assert np.allclose(prob.sum(axis=1), 1) and (prob > 0).all()
    actual = np.where(np.abs(fwd) < 0.08, "FLAT", np.where(fwd > 0, "UP", "DOWN"))
    res = mechanism_checks(prob, vol, fwd, actual)
    assert res["check_1_pflat_vs_vol30d"]["spearman"] < 0
    assert res["check_2_pflat_vs_abs_fwd_return"]["spearman"] < 0
    assert res["check_3_up_minus_down_vs_fwd_return"]["spearman"] > 0
    assert res["mean_predicted_p_flat"] == pytest.approx(p_flat.mean())
    assert res["observed_flat_share"] == pytest.approx((actual == "FLAT").mean())


def _raw(n_feature_rows):
    """Hand-made daily bars (not market data)."""
    i = np.arange(n_feature_rows + W, dtype=float)
    close = 100 + 0.2 * i + 15 * np.sin(i / 9) + (2 + 1.5 * np.sin(i / 40)) * np.cos(i * 1.7)
    return pd.DataFrame({
        "asset": "test", "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def test_module_never_reaches_test_rows():
    b2 = 255                                                    # min_train 100 so several folds fit the fixture
    data = dev_data(_raw(300).iloc[:W + b2].copy())
    pooled, folds = pooled_predictions(data, b2, min_train=100)
    assert len(folds) == 4
    assert pooled["row"].max() < b2 - H                         # labels of predicted rows end before b2
    assert pooled["vol_30d"].tolist() == data["vol_30d"].iloc[pooled["row"]].tolist()
    longer = dev_data(_raw(300).iloc[:W + b2 + 5].copy())        # a frame containing test rows is refused
    with pytest.raises(SealedTestError):
        pooled_predictions(longer, b2, min_train=100)
