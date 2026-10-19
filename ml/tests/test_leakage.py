"""Leakage tests for features, labels, splits and thresholds (Phase 2).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import math

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.splits import make_splits
from ml.features.features import FEATURE_COLUMNS, build_features
from ml.labels.labels import apply_thresholds, build_labels, fit_thresholds, fwd_return_30d, fwd_vol_30d

N_RAW = 330          # -> 300 feature rows after the 30-row warm-up


def _bars(n=N_RAW):
    """Hand-made daily bars (not market data): a wave on a slow trend, so ma_cross takes all values."""
    i = np.arange(n, dtype=float)
    close = 100 + 15 * np.sin(i / 9) + 0.2 * i
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": np.r_[close[0], close[:-1]],
        "high": close * (1.02 + 0.01 * np.cos(i / 5)),
        "low": close * (0.98 - 0.01 * np.sin(i / 7)),
        "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _change_after(df, t):
    """Copy of df with every price and volume after row t changed."""
    out = df.copy()
    cols = ["open", "high", "low", "close", "volume"]
    out.loc[t + 1:, cols] = out.loc[t + 1:, cols] * 3.7
    return out


# a. full series vs series truncated at t
@pytest.mark.parametrize("t", [30, 31, 75, 200, N_RAW - 1])
def test_features_same_on_truncated_series(t):
    df = _bars()
    full = build_features(df)
    trunc = build_features(df.iloc[:t + 1])
    pd.testing.assert_frame_equal(full.loc[:trunc.index[-1]], trunc, check_exact=True)


# b. changing prices after t never changes features at or before t
@pytest.mark.parametrize("t", [30, 100, 250])
def test_future_prices_do_not_change_past_features(t):
    df = _bars()
    ts = df["timestamp"].iloc[t]
    before = build_features(df).loc[:ts]
    after = build_features(_change_after(df, t)).loc[:ts]
    pd.testing.assert_frame_equal(before, after, check_exact=True)
    # sanity: the change does reach rows after t, so the test is not vacuous
    assert not build_features(df).loc[ts:].iloc[1:].equals(build_features(_change_after(df, t)).loc[ts:].iloc[1:])


# c. forward return equals a hand computation; last 30 rows have no label
def test_fwd_return_manual_and_last_rows_nan():
    close = pd.Series(np.linspace(100, 160, 40) + np.r_[0, 5, -3, 2].repeat(10))
    r = fwd_return_30d(close)
    assert r.iloc[0] == pytest.approx(math.log(close.iloc[30] / close.iloc[0]))
    assert r.iloc[7] == pytest.approx(math.log(close.iloc[37] / close.iloc[7]))
    assert r.iloc[-30:].isna().all() and r.iloc[:-30].notna().all()

    v = fwd_vol_30d(close)
    daily = np.diff(np.log(close.to_numpy()[5:36]))          # returns t+1..t+30 for t=5
    assert v.iloc[5] == pytest.approx(np.std(daily, ddof=1))
    assert v.iloc[-30:].isna().all() and v.iloc[:-30].notna().all()


# d. boundaries follow D18 and labels never cross into the next split
@pytest.mark.parametrize("n", [250, 300, 1000, 1234, 2229, 3319])
def test_split_boundaries_d18(n):
    s = make_splits(n)
    b1, b2, e = n * 70 // 100, n * 85 // 100, 30
    assert s["train"] == range(0, b1 - e)
    assert s["validation"] == range(b1, b2 - e)
    assert s["test"] == range(b2, n)
    h = config.HORIZON_DAYS
    assert all(i + h < s["validation"].start for i in s["train"])
    assert all(i + h < s["test"].start for i in s["validation"])


@pytest.mark.parametrize("n", [50, 200])     # n=200: b2-30 = b1 = 140, so validation would be empty
def test_split_too_small_raises(n):
    with pytest.raises(ValueError):
        make_splits(n)


# e. thresholds fitted on train ignore validation/test values
def test_thresholds_ignore_validation_and_test():
    df = _bars()
    feats = build_features(df)
    splits = make_splits(len(feats))

    def fitted(frame):
        f = build_features(frame)
        labels = build_labels(frame.set_index("timestamp")["close"]).loc[f.index]
        return fit_thresholds(labels.iloc[splits["train"]])

    # change every raw price from the first validation row onward
    first_val_raw_row = config.WARMUP_ROWS + splits["validation"].start
    assert fitted(df) == fitted(_change_after(df, first_val_raw_row - 1))

    # and directly: altering validation/test label values does not move the train fit
    labels = build_labels(df.set_index("timestamp")["close"]).loc[feats.index]
    altered = labels.copy()
    rest = list(splits["validation"]) + list(splits["test"])
    altered.iloc[rest] = altered.iloc[rest] * 50
    assert fit_thresholds(labels.iloc[splits["train"]]) == fit_thresholds(altered.iloc[splits["train"]])


def test_apply_thresholds_classes():
    labels = pd.DataFrame({"fwd_return_30d": [0.2, -0.2, 0.01, np.nan],
                           "fwd_vol_30d": [0.01, 0.05, 0.03, np.nan]})
    th = {"direction_flat_abs_return": 0.05, "risk_low_max_vol": 0.02, "risk_high_min_vol": 0.04}
    c = apply_thresholds(labels, th)
    assert c["direction"].tolist()[:3] == ["UP", "DOWN", "FLAT"]
    assert c["risk"].tolist()[:3] == ["low", "high", "medium"]
    assert c.iloc[3].isna().all()


# f. no label columns in the features
def test_features_have_no_label_columns():
    feats = build_features(_bars())
    assert list(feats.columns) == FEATURE_COLUMNS
    assert not [c for c in feats.columns if c.startswith("fwd_") or "target" in c]


# g. ma_cross is only -1, 0 or 1 (and the fixture produces all three)
def test_ma_cross_values():
    feats = build_features(_bars())
    assert set(feats["ma_cross"].unique()) == {-1, 0, 1}


def test_warmup_dropped_and_no_nan():
    df = _bars()
    feats = build_features(df)
    assert len(feats) == len(df) - config.WARMUP_ROWS
    assert feats.index[0] == df["timestamp"].iloc[config.WARMUP_ROWS]
    assert not feats.isna().any().any()


def test_gaps_are_refused():
    df = _bars().drop(index=100)
    with pytest.raises(ValueError):
        build_features(df)
