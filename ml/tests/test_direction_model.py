"""Leakage, probability and protocol tests for the direction model (Phase 4c, D31).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from ml import config
from ml.evaluation import baselines as bl
from ml.evaluation.prob_metrics import ece, log_loss_rows
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.run_walkforward_direction import HARD, HARD_NOTE, evaluate_hard, prob_columns, rank, results
from ml.evaluation.walkforward import INPUT_COLUMNS, SealedTestError, Spec, make_folds, run_folds
from ml.features.features import FEATURE_COLUMNS
from ml.labels.labels import DIRECTION_CLASSES, apply_thresholds, fit_thresholds
from ml.models import direction

H, W = config.HORIZON_DAYS, config.WARMUP_ROWS
N, B2, MIN_TRAIN, STEP = 300, 255, 100, 30      # fixture geometry: 4 folds, sealed test from row 255


def _raw():
    """Hand-made daily bars (not market data): a trend, two waves and a slowly changing wobble."""
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
    scale = np.linspace(1.5, 3.0, len(out) - first_raw_row)[:, None]
    out.loc[first_raw_row:, cols] = out.loc[first_raw_row:, cols] * scale
    return out


def _folds():
    return make_folds(N, B2, MIN_TRAIN, STEP, H)


def _fits(data, cfg):
    """Run one config through the harness and return (train frames, fitted models), one per fold."""
    cache, trains, fits = direction.FitCache(), [], []
    spy = Spec(fit=lambda train: (trains.append(train), fits.append(cache.get(cfg, train)), fits[-1])[2],
               predict=lambda fitted, x: direction.probabilities(fitted, x)["UP"])
    run_folds(data, _folds(), {"m": spy}, B2)
    return trains, fits


def _features(n):
    """Hand-made feature frame (not market data) with every feature column."""
    t = np.arange(n, dtype=float)
    return pd.DataFrame({c: np.sin(t * (k + 1) / 3) + 0.1 * k for k, c in enumerate(FEATURE_COLUMNS)})


def test_exactly_two_configs_declared():
    assert list(direction.CONFIGS) == ["logreg_c0.1", "logreg_c1"]
    assert direction.BASELINE == "prior" and direction.EPS == 1e-6
    for make in direction.CONFIGS.values():
        assert make().get_params()["solver"] == "lbfgs"


# scaling uses only train rows
@pytest.mark.parametrize("cfg", list(direction.CONFIGS))
def test_scaling_uses_only_train_rows(cfg):
    data = _data(_raw())
    trains, fits = _fits(data, cfg)
    for f, train, fitted in zip(_folds(), trains, fits):
        assert train.index.equals(data.index[f.train])
        x = data.iloc[list(f.train)][FEATURE_COLUMNS].to_numpy(dtype=float)
        assert np.array_equal(fitted.mean, x.mean(axis=0)) and np.array_equal(fitted.std, x.std(axis=0))


# (i) the model fitted for fold k is unchanged when raw rows at or after origin_k are altered
@pytest.mark.parametrize("cfg", list(direction.CONFIGS))
def test_fold_model_ignores_rows_from_origin(cfg):
    raw = _raw()
    orig = _data(raw)
    _, fits_orig = _fits(orig, cfg)
    for k, f in enumerate(_folds()):
        alt = _data(_alter_from(raw, W + f.origin))
        _, fits_alt = _fits(alt, cfg)
        inputs = orig.iloc[list(f.predict)][INPUT_COLUMNS]
        assert not inputs.equals(alt.iloc[list(f.predict)][INPUT_COLUMNS])       # the change is real
        pd.testing.assert_frame_equal(direction.probabilities(fits_orig[k], inputs),
                                      direction.probabilities(fits_alt[k], inputs), check_exact=True)


# (ii) the prediction at row r is unchanged when only rows after r are altered
@pytest.mark.parametrize("offset", [0, 13, 29])
def test_prediction_at_r_ignores_later_rows(offset):
    raw = _raw()
    folds = _folds()
    r = folds[1].origin + offset
    before, _ = run_folds(_data(raw), folds, direction.specs(direction.FitCache()), B2)
    after, _ = run_folds(_data(_alter_from(raw, W + r + 1)), folds, direction.specs(direction.FitCache()), B2)
    cols = [c for c in before.columns if c.startswith("pred:direction_model/")]
    at = before["row"] == r
    pd.testing.assert_frame_equal(before.loc[at, cols], after.loc[at, cols], check_exact=True)
    assert not before.loc[before["row"] == r + 1, cols].equals(after.loc[after["row"] == r + 1, cols])


# the model never sees an index >= b2
def test_model_never_sees_test_rows():
    data = _data(_raw())
    pos = {ts: i for i, ts in enumerate(data.index)}
    cache, fit_max, pred_max = direction.FitCache(), [], []
    spy = Spec(fit=lambda train: (fit_max.append(max(pos[t] for t in train.index)), cache.get("logreg_c1", train))[1],
               predict=lambda fitted, x: (pred_max.append(max(pos[t] for t in x.index)),
                                          direction.probabilities(fitted, x)["UP"])[1])
    run_folds(data, _folds(), {"m": spy}, B2)
    assert fit_max and max(fit_max) < B2 - 2 * H and max(pred_max) < B2 - H
    longer = dev_data(_raw().iloc[:W + B2 + 5].copy())          # a frame containing test rows is refused
    with pytest.raises(SealedTestError):
        run_folds(longer, _folds(), direction.specs(direction.FitCache()), B2)


# probabilities are non-negative and sum to 1 per row; prior equals train-fold class frequencies
def test_probabilities_sum_to_one_and_prior_is_train_frequency():
    data = _data(_raw())
    folds = _folds()
    pooled, _ = run_folds(data, folds, direction.specs(direction.FitCache()), B2)
    for name in (*direction.CONFIGS, direction.BASELINE):
        p = pooled[prob_columns(name)].to_numpy()
        assert (p >= 0).all() and np.allclose(p.sum(axis=1), 1.0, rtol=0, atol=1e-12)
    for f in folds:
        train = data.iloc[list(f.train)]
        cls = apply_thresholds(train, fit_thresholds(train))["direction"]
        freq = np.array([(cls == c).mean() for c in DIRECTION_CLASSES])
        assert (freq > 0).all()                                   # all classes present: no clipping here
        part = pooled.loc[pooled["origin"] == f.origin, prob_columns("prior")].to_numpy()
        assert np.allclose(part, freq, rtol=0, atol=1e-15)


def test_absent_class_gets_eps():
    x = _features(40)
    train = x.assign(direction=["DOWN", "UP"] * 20)                # FLAT never occurs in this train
    fitted = direction.fit(train, "logreg_c1", direction.CONFIGS["logreg_c1"])
    p = direction.probabilities(fitted, x)
    eps = direction.EPS
    assert np.allclose(p["FLAT"], eps / (1 + eps), rtol=1e-9)    # 0 -> EPS, then the row is renormalised
    assert np.allclose(p.sum(axis=1), 1.0)
    prior = direction.fit_prior(pd.DataFrame({"direction": ["UP", "UP", "DOWN", "DOWN"]}))
    assert prior == pytest.approx(np.array([0.5, eps, 0.5]) / (1 + eps))


def test_log_loss_rows_hand_values():
    uniform = np.full((4, 3), 1 / 3)
    assert log_loss_rows(uniform, ["UP", "DOWN", "FLAT", "UP"], DIRECTION_CLASSES) == pytest.approx([math.log(3)] * 4)
    p = np.array([[0.2, 0.3, 0.5], [0.7, 0.2, 0.1]])
    assert log_loss_rows(p, ["UP", "FLAT"], DIRECTION_CLASSES) == pytest.approx([-math.log(0.5), -math.log(0.2)])


def test_ece_hand_values():
    # perfectly calibrated: every row predicts [0.2, 0.3, 0.5] and the classes occur 2, 3, 5 times in 10
    p = np.tile([0.2, 0.3, 0.5], (10, 1))
    actual = ["DOWN"] * 2 + ["FLAT"] * 3 + ["UP"] * 5
    good = ece(p, actual, DIRECTION_CLASSES)                      # 3/10 vs 0.3 differ only by float rounding
    assert good["per_class"] == pytest.approx({"DOWN": 0.0, "FLAT": 0.0, "UP": 0.0}, abs=1e-12)
    assert good["macro"] == pytest.approx(0.0, abs=1e-12)
    # miscalibrated: predicts [0.8, 0.1, 0.1] but every row is FLAT -> DOWN 0.8, FLAT 0.9, UP 0.1, macro 0.6
    bad = ece(np.tile([0.8, 0.1, 0.1], (10, 1)), ["FLAT"] * 10, DIRECTION_CLASSES)
    assert bad["per_class"] == pytest.approx({"DOWN": 0.8, "FLAT": 0.9, "UP": 0.1})
    assert bad["macro"] == pytest.approx(0.6)


def test_hard_baselines_null_probabilistic_metrics_and_not_ranked():
    data = _data(_raw())
    base = bl.walkforward_specs()
    specs = {**direction.specs(direction.FitCache()), **{f"direction/{h}": base[f"direction/{h}"] for h in HARD}}
    pooled, _ = run_folds(data, _folds(), specs, B2)
    res = results(pooled)
    for h in HARD:
        r = evaluate_hard(pooled, h)
        assert r["log_loss"] is None and r["brier"] is None and r["roc_auc_ovr"] is None and r["ece"] is None
        assert HARD_NOTE in r["note"] and res[f"hard/{h}"]["log_loss"] is None
    assert rank(res) in (["logreg_c0.1", "logreg_c1"], ["logreg_c1", "logreg_c0.1"])


def test_convergence_warning_counted_once_per_fold():
    data = _data(_raw())
    folds = _folds()
    forced = direction.FitCache({"forced": lambda: LogisticRegression(C=1.0, max_iter=1)})   # test-only config
    run_folds(data, folds, direction.specs(forced), B2)
    assert forced.convergence_warnings() == {"forced": {"folds_with_warning": len(folds), "n_folds": len(folds)}}
    normal = direction.FitCache()
    run_folds(data, folds, direction.specs(normal), B2)
    assert all(v["n_folds"] == len(folds) for v in normal.convergence_warnings().values())   # one fit per fold
