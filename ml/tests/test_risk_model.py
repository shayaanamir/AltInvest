"""Leakage and protocol tests for the risk model (Phase 4a, D24, D25).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.run_walkforward_risk import classes_from_vol, split_folds
from ml.evaluation.walkforward import INPUT_COLUMNS, SealedTestError, Spec, make_folds, run_folds
from ml.models import risk

H, W = config.HORIZON_DAYS, config.WARMUP_ROWS
N, B2, MIN_TRAIN, STEP = 300, 255, 100, 30      # fixture geometry: 4 folds, sealed test from row 255


def _raw():
    """Hand-made daily bars (not market data): a trend, two waves and a volatility that changes slowly."""
    i = np.arange(N + W, dtype=float)
    close = 100 + 0.2 * i + 15 * np.sin(i / 9) + (2 + 1.5 * np.sin(i / 40)) * np.cos(i * 1.7)
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * (1.02 + 0.005 * np.sin(i / 6)), "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _data(raw):
    return dev_data(raw.iloc[:W + B2].copy())


def _alter_from(raw, first_raw_row):
    out = raw.copy()
    cols = ["open", "high", "low", "close", "volume"]
    out.loc[first_raw_row:, cols] = out.loc[first_raw_row:, cols] * np.linspace(1.5, 3.0, len(out) - first_raw_row)[:, None]
    return out


def _folds():
    return make_folds(N, B2, MIN_TRAIN, STEP, H)


def test_exactly_four_configs_declared():
    assert list(risk.CONFIGS) == ["har_ridge_a1", "ridge_all_a1", "ridge_all_a10", "hgb_d3"]


# scaling uses only train rows
@pytest.mark.parametrize("cfg", list(risk.CONFIGS))
def test_scaling_uses_only_train_rows(cfg):
    data = _data(_raw())
    seen = []
    base = risk.spec(cfg)
    spy = Spec(fit=lambda train: (seen.append(train), base.fit(train))[1], predict=base.predict)
    run_folds(data, _folds(), {"m": spy}, B2)
    for f, train in zip(_folds(), seen):
        assert train.index.equals(data.index[f.train])            # the harness passed exactly the train rows
        fitted = base.fit(train)
        x, _ = risk.design(data.iloc[list(f.train)], cfg)
        assert np.array_equal(fitted.mean, x.mean(axis=0)) and np.array_equal(fitted.std, x.std(axis=0))


# (i) the model fitted for fold k is unchanged when raw rows at or after origin_k are altered
@pytest.mark.parametrize("cfg", list(risk.CONFIGS))
def test_fold_model_ignores_rows_from_origin(cfg):
    raw = _raw()
    for f in _folds():
        orig, alt = _data(raw), _data(_alter_from(raw, W + f.origin))
        inputs = orig.iloc[list(f.predict)][INPUT_COLUMNS]
        assert not inputs.equals(alt.iloc[list(f.predict)][INPUT_COLUMNS])   # the change is real
        p_orig = risk.predict(risk.fit(orig.iloc[list(f.train)], cfg), inputs)
        p_alt = risk.predict(risk.fit(alt.iloc[list(f.train)], cfg), inputs)  # fit on altered data
        pd.testing.assert_series_equal(p_orig, p_alt, check_exact=True)


# (ii) the prediction at row r is unchanged when only rows after r are altered
@pytest.mark.parametrize("offset", [0, 13, 29])
def test_prediction_at_r_ignores_later_rows(offset):
    raw = _raw()
    folds = _folds()
    r = folds[1].origin + offset
    specs = risk.specs()
    before, _ = run_folds(_data(raw), folds, specs, B2)
    after, _ = run_folds(_data(_alter_from(raw, W + r + 1)), folds, specs, B2)
    cols = [c for c in before.columns if c.startswith("pred:")]
    at = before["row"] == r
    pd.testing.assert_frame_equal(before.loc[at, cols], after.loc[at, cols], check_exact=True)
    assert not before.loc[before["row"] == r + 1, cols].equals(after.loc[after["row"] == r + 1, cols])


# the model never sees an index >= b2
def test_model_never_sees_test_rows():
    data = _data(_raw())
    pos = {ts: i for i, ts in enumerate(data.index)}
    fit_max, pred_max = [], []
    base = risk.spec("hgb_d3")
    spy = Spec(fit=lambda train: (fit_max.append(max(pos[t] for t in train.index)), base.fit(train))[1],
               predict=lambda fitted, x: (pred_max.append(max(pos[t] for t in x.index)), base.predict(fitted, x))[1])
    run_folds(data, _folds(), {"m": spy}, B2)
    assert fit_max and max(fit_max) < B2 - 2 * H and max(pred_max) < B2 - H
    longer = dev_data(_raw().iloc[:W + B2 + 5].copy())          # a frame containing test rows is refused
    with pytest.raises(SealedTestError):
        run_folds(longer, _folds(), risk.specs(), B2)


# the 60/40 fold split is chronological and contiguous
@pytest.mark.parametrize("n,b2,first,second", [(3319, 2821, 40, 28), (2229, 1894, 22, 15)])
def test_fold_split_chronological_contiguous(n, b2, first, second):
    folds = make_folds(n, b2)
    rank, conf = split_folds(folds)
    assert (len(rank), len(conf)) == (first, second)
    assert rank + conf == folds
    assert rank[-1].predict.stop == conf[0].predict.start           # no gap between the two sets
    assert max(f.origin for f in rank) < min(f.origin for f in conf)
    with pytest.raises(ValueError):
        split_folds(folds[:1])


def test_classes_use_each_folds_thresholds():
    vol = pd.Series([0.01, 0.03, 0.05, 0.01, 0.03, 0.05])
    origins = pd.Series([1, 1, 1, 2, 2, 2])
    th = {1: {"risk_low_max_vol": 0.02, "risk_high_min_vol": 0.04},
          2: {"risk_low_max_vol": 0.005, "risk_high_min_vol": 0.02}}
    assert classes_from_vol(vol, origins, th).tolist() == ["low", "medium", "high", "medium", "high", "high"]
