"""Walk-forward with a horizon parameter (Phase 9 step 9.2a, D41): embargo = step = h, region [0, b2 - h),
n_effective = n_pooled / h. h = 30 must stay exactly as before.

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import baselines as bl
from ml.evaluation.run_walkforward import _pooled_counts, dev_data
from ml.evaluation.splits import make_splits
from ml.evaluation.walkforward import (Fold, SealedTestError, Spec, check_label_horizons, label_horizon, make_folds,
                                       run_folds)
from ml.labels.labels import build_labels

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


def _folds(h):
    return make_folds(N, B2, MIN_TRAIN, h, h)


def _zero_spec():
    return {"zero": Spec(lambda train: None, lambda _, inputs: pd.Series(0.0, index=inputs.index))}


# --- h = 30 is unchanged -------------------------------------------------------------------------------------

def test_h30_defaults_unchanged():
    assert make_folds(3319, 2821) == make_folds(3319, 2821, config.MIN_TRAIN_ROWS, 30, 30)
    raw = _raw().iloc[:config.WARMUP_ROWS + B2].copy()
    pd.testing.assert_frame_equal(dev_data(raw), dev_data(raw, 30), check_exact=True)
    assert list(dev_data(raw).columns[-4:]) == ["fwd_return_30d", "fwd_vol_30d", "close", "close_fwd_30d"]
    p1, t1 = run_folds(_data(30), _folds(30), bl.walkforward_specs(), B2)
    p2, t2 = run_folds(_data(30), _folds(30), bl.walkforward_specs(), B2, horizon=30)
    pd.testing.assert_frame_equal(p1, p2, check_exact=True)
    assert t1 == t2 and all("thresholds" in row for row in t1)
    assert {"direction", "risk"} <= set(p1.columns)


def test_sealed_test_start_is_the_same_for_every_horizon():
    for n in (2229, 3319, 500):
        assert make_splits(n, embargo=7)["test"] == make_splits(n)["test"]


# --- h = 7 geometry ------------------------------------------------------------------------------------------

def test_h7_folds_do_not_overlap_and_keep_a_7_row_gap():
    folds = _folds(7)
    rows = [i for f in folds for i in f.predict]
    assert rows == list(range(MIN_TRAIN + 7, B2 - 7))              # contiguous, no overlap, region [.., b2-7)
    assert [f.origin for f in folds] == list(range(MIN_TRAIN + 7, B2 - 7, 7))
    assert all(len(f.predict) == 7 for f in folds[:-1])
    for f in folds:
        assert f.train == range(0, f.origin - 7)                  # 7-row gap before the origin
        assert max(f.predict) < B2 - 7                            # labels of predicted rows end before b2


def test_h7_real_geometry():
    folds = make_folds(3319, 2821, config.MIN_TRAIN_ROWS, 7, 7)   # BTC/ETH snapshot: n = 3319, b2 = 2821
    assert folds[0].origin == config.MIN_TRAIN_ROWS + 7 and len(folds[0].train) == config.MIN_TRAIN_ROWS
    assert max(folds[-1].predict) == 2821 - 7 - 1
    assert len(folds) == -(-(2821 - 7 - (config.MIN_TRAIN_ROWS + 7)) // 7)


def test_h7_sealed_test_guard_still_raises():
    data = _data(7)
    bad = Fold(origin=B2 - 3, train=range(0, B2 - 10), predict=range(B2 - 3, B2 + 4))
    with pytest.raises(SealedTestError):
        run_folds(data, [bad], _zero_spec(), B2, horizon=7)
    longer = dev_data(_raw().iloc[:config.WARMUP_ROWS + B2 + 10].copy(), 7)
    with pytest.raises(SealedTestError):
        run_folds(longer, _folds(7), _zero_spec(), B2, horizon=7)


# --- training labels never reach into the predict window -----------------------------------------------------

@pytest.mark.parametrize("h", [7, 30])
def test_train_labels_end_before_origin(h):
    close = _raw().set_index("timestamp")["close"].iloc[config.WARMUP_ROWS:]   # feature-row positions
    full = build_labels(close, h)
    for f in _folds(h):
        assert all(i + h < f.origin for i in f.train)
        cut = build_labels(close.iloc[:f.origin], h)             # only closes before the origin
        assert cut.iloc[list(f.train)].notna().all().all()
        pd.testing.assert_frame_equal(cut.iloc[list(f.train)], full.iloc[list(f.train)])


def test_h7_train_rows_seen_by_the_model_ignore_the_future():
    """Changing every price from the origin on never changes what fit() sees for that fold."""
    seen = {}

    def fit(train):
        seen.setdefault(len(seen), train.copy())

    spec = {"spy": Spec(fit, lambda _, inputs: pd.Series(0.0, index=inputs.index))}
    raw = _raw()
    folds = _folds(7)
    k = 5
    run_folds(_data(7, raw), folds[:k + 1], spec, B2, horizon=7)
    before = seen[k]
    altered = raw.copy()
    cols = ["open", "high", "low", "close", "volume"]
    altered.loc[config.WARMUP_ROWS + folds[k].origin:, cols] *= 2.9
    seen.clear()
    run_folds(_data(7, altered), folds[:k + 1], spec, B2, horizon=7)
    pd.testing.assert_frame_equal(before, seen[k], check_exact=True)


def test_h7_refuses_longer_labels_and_a_short_embargo():
    data = _data(7)
    assert list(data.columns[-4:]) == ["fwd_return_7d", "fwd_vol_7d", "close", "close_fwd_7d"]
    assert [label_horizon(c) for c in ("fwd_return_7d", "close_fwd_30d", "vol_30d", "ret_7d")] == [7, 30, None, None]
    with_30 = data.join(_data(30)[["fwd_return_30d"]])
    with pytest.raises(ValueError, match="further ahead"):
        run_folds(with_30, _folds(7), _zero_spec(), B2, horizon=7)
    check_label_horizons(with_30, 30)                            # fine at h = 30
    short = Fold(origin=150, train=range(0, 145), predict=range(150, 157))
    with pytest.raises(ValueError, match="embargo"):
        run_folds(data, [short], _zero_spec(), B2, horizon=7)


def test_h7_has_no_classes_and_counts_use_h():
    pooled, table = run_folds(_data(7), _folds(7), _zero_spec(), B2, horizon=7)
    assert "direction" not in pooled.columns and "risk" not in pooled.columns
    assert all("thresholds" not in row for row in table)
    counts = _pooled_counts(pooled, 7)
    assert counts["n_effective"] == len(pooled) / 7 and counts["n_folds"] == len(_folds(7))
