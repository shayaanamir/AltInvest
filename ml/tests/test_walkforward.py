"""Tests for the walk-forward harness (Phase 4.0, D21).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import math

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import baselines as bl
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.walkforward import Fold, SealedTestError, check_before_test, make_folds, run_folds
from ml.labels.labels import build_labels, direction_class, fit_thresholds

H = config.HORIZON_DAYS
# fixture geometry: 300 feature rows, sealed test from row 255, small min_train so several folds fit
N, B2, MIN_TRAIN, STEP = 300, 255, 100, 30


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


def _data(raw=None):
    """Pre-test frame exactly as run_walkforward builds it: raw rows for feature rows [0, B2) only."""
    raw = _raw() if raw is None else raw
    return dev_data(raw.iloc[:config.WARMUP_ROWS + B2].copy())


def _folds():
    return make_folds(N, B2, MIN_TRAIN, STEP, H)


# a. train rows end more than one horizon before the origin; their labels need only closes before it
def test_train_ends_before_origin_minus_horizon():
    raw = _raw()
    close = raw.set_index("timestamp")["close"].iloc[config.WARMUP_ROWS:]   # feature-row positions
    for f in _folds():
        assert max(f.train) < f.origin - H
        assert all(i + H < f.origin for i in f.train)
        # labels built from closes strictly before the origin exist for every train row and match
        cut = build_labels(close.iloc[:f.origin])
        full = build_labels(close)
        assert cut.iloc[list(f.train)].notna().all().all()
        pd.testing.assert_frame_equal(cut.iloc[list(f.train)], full.iloc[list(f.train)])


# b. predict ranges are contiguous, non-overlapping, step 30
def test_predict_ranges_contiguous_step_30():
    folds = _folds()
    rows = [i for f in folds for i in f.predict]
    assert rows == list(range(folds[0].origin, B2 - H))          # contiguous, no overlap, no gap
    assert [f.origin for f in folds] == list(range(MIN_TRAIN + H, B2 - H, STEP))
    assert all(len(f.predict) == STEP for f in folds[:-1])
    assert 0 < len(folds[-1].predict) <= STEP


# c. nothing at or after b2, and asking for it raises
def test_test_rows_are_sealed():
    folds = _folds()
    assert max(max(f.train, default=-1) for f in folds) < B2
    assert max(max(f.predict) for f in folds) < B2 - H           # labels of predicted rows end before b2
    with pytest.raises(SealedTestError):
        check_before_test(range(B2 - 5, B2 + 1), B2)
    data = _data()
    bad = Fold(origin=B2 - 10, train=range(0, B2 - 40), predict=range(B2 - 10, B2 + 5))
    with pytest.raises(SealedTestError):
        run_folds(data, [bad], bl.walkforward_specs(), B2)
    longer = dev_data(_raw().iloc[:config.WARMUP_ROWS + B2 + 10].copy())   # frame containing test rows
    with pytest.raises(SealedTestError):
        run_folds(longer, folds, bl.walkforward_specs(), B2)
    with pytest.raises(ValueError):
        make_folds(N, N + 1, MIN_TRAIN, STEP, H)


# d. fold thresholds ignore rows at or after the origin
def test_fold_thresholds_ignore_rows_from_origin():
    raw = _raw()
    folds = _folds()
    _, table = run_folds(_data(raw), folds, bl.walkforward_specs(), B2)
    k = 1
    altered = raw.copy()
    first_raw = config.WARMUP_ROWS + folds[k].origin
    cols = ["open", "high", "low", "close", "volume"]
    altered.loc[first_raw:, cols] = altered.loc[first_raw:, cols] * 2.9
    _, table2 = run_folds(_data(altered), folds, bl.walkforward_specs(), B2)
    for j in range(k + 1):                                      # every fold whose origin <= the change
        assert table[j]["thresholds"] == table2[j]["thresholds"]
    assert table[k + 1]["thresholds"] != table2[k + 1]["thresholds"]   # the change is visible later


# e. fold count for known geometries
def test_fold_count():
    assert len(_folds()) == math.ceil((B2 - H - (MIN_TRAIN + H)) / STEP) == 4
    # D21 geometry for the current BTC/ETH data: n=3319 -> b2=2821, origins 760..2790
    assert len(make_folds(3319, 2821)) == 68
    with pytest.raises(ValueError):
        make_folds(800, 780)                                    # first origin 760 >= end 750


# f. a baseline through the harness equals a manual computation
def test_baselines_through_harness_match_manual():
    data = _data()
    folds = _folds()
    pooled, table = run_folds(data, folds, bl.walkforward_specs(), B2)
    for f, row in zip(folds, table):
        train = data.iloc[list(f.train)]
        part = pooled[pooled["origin"] == f.origin]
        drift = train["fwd_return_30d"].mean()                  # manual drift: train mean forward return
        assert np.allclose(part["pred:price/drift"], drift, rtol=0, atol=1e-15)
        assert (part["pred:price/last_value"] == 0).all()
        th = fit_thresholds(train)                              # manual momentum with this fold's threshold
        assert row["thresholds"] == th
        expected = direction_class(data["ret_30d"].iloc[list(f.predict)], th)
        assert part["pred:direction/momentum"].tolist() == expected.tolist()
        assert part["pred:risk_ranking/persistence"].tolist() == data["vol_30d"].iloc[list(f.predict)].tolist()
    assert pooled["row"].tolist() == [i for f in folds for i in f.predict]


def test_predict_inputs_have_no_labels():
    seen = []
    spy = {"spy": bl.Spec(lambda train: None, lambda _, inputs: (seen.append(list(inputs.columns)),
                                                                  pd.Series(0.0, index=inputs.index))[1])}
    run_folds(_data(), _folds(), spy, B2)
    assert seen and all(not any(c.startswith("fwd_") or c == "close_fwd_30d" for c in cols) for cols in seen)
