"""Walk-forward with inputs known at t (D48): the history harness and the corrected Prophet protocol.

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
The Prophet test skips when prophet is not installed (the serving environment).
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.walkforward import Fold, SealedTestError, make_folds
from ml.evaluation.walkforward_history import HistorySpec, run_history_folds
from ml.models import price_v2

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


def _changed_after(raw, feature_row):
    """Copy of the bars with every price after feature row `feature_row` multiplied by 2.3."""
    out = raw.copy()
    out.loc[config.WARMUP_ROWS + feature_row + 1:, ["open", "high", "low", "close", "volume"]] *= 2.3
    return out


def test_history_harness_passes_inputs_up_to_the_refit_origin_and_no_labels():
    h, seen = 7, []

    def fit(train, inputs):
        seen.append((train.index[-1], inputs.index[-1], list(inputs.columns)))
        return len(inputs)

    spec = {"spy": HistorySpec(fit, lambda model, history, rows: np.full(len(rows), float(model)))}
    data = _data(h)
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    pooled, info = run_history_folds(data, folds, spec, B2, h, every=4)
    assert info["n_fits"]["spy"] == len(range(0, len(folds), 4)) == len(seen)
    for k, (train_end, inputs_end, cols) in enumerate(seen):
        r = folds[4 * k]
        assert inputs_end == data.index[r.origin]                    # inputs end at the refit origin
        assert train_end == data.index[r.origin - h - 1]             # labelled rows still end before the embargo
        assert not any(c.startswith("fwd_") or c.startswith("close_fwd") for c in cols)
    for k, f in enumerate(folds):                                    # every fold uses its refit fold's fit
        part = pooled[pooled["origin"] == f.origin]
        assert (part["pred:spy"] == folds[k - k % 4].origin + 1).all()


def test_history_harness_keeps_the_seal_and_the_embargo():
    h = 7
    spec = {"zero": HistorySpec(lambda train, inputs: None, lambda m, history, rows: np.zeros(len(rows)))}
    longer = dev_data(_raw().iloc[:config.WARMUP_ROWS + B2 + 5].copy(), h)
    with pytest.raises(SealedTestError):
        run_history_folds(longer, make_folds(N, B2, MIN_TRAIN, h, h), spec, B2, h, 1)
    bad = Fold(origin=B2 - 3, train=range(0, B2 - 10), predict=range(B2 - 3, B2 + 4))
    with pytest.raises(SealedTestError):
        run_history_folds(_data(h), [bad], spec, B2, h, 1)
    short = Fold(origin=150, train=range(0, 147), predict=range(150, 157))
    with pytest.raises(ValueError, match="embargo"):
        run_history_folds(_data(h), [short], spec, B2, h, 1)


def test_prophet_specs_are_split_by_protocol():
    with pytest.raises(ValueError):
        price_v2.specs("prophet", 7)                                # corrected protocol needs the history harness
    with pytest.raises(ValueError):
        price_v2.history_specs("lightgbm", 7)
    assert price_v2.refit_every_folds("prophet", 7) == price_v2.refit_every_folds("prophet_9_2", 7) == 4


@pytest.mark.parametrize("h", [7, 30])
def test_corrected_prophet_forecast_for_origin_t_ignores_closes_after_t(h):
    pytest.importorskip("prophet")
    every = price_v2.refit_every_folds("prophet", h)
    folds = make_folds(N, B2, MIN_TRAIN, h, h)[:every + 1]
    raw = _raw()
    base, _ = run_history_folds(_data(h, raw), folds, price_v2.history_specs("prophet", h), B2, h, every)
    for f in (folds[0], folds[-1]):                                 # a refit origin, and (h = 7) a reused fit
        changed, _ = run_history_folds(_data(h, _changed_after(raw, f.origin)), folds,
                                       price_v2.history_specs("prophet", h), B2, h, every)
        cols = ["pred:prophet_cps005", "pred:prophet_cps05"]
        upto = base["row"] <= f.origin
        np.testing.assert_array_equal(base.loc[upto, cols].to_numpy(), changed.loc[upto, cols].to_numpy())
    # not vacuous: closes up to the origin do reach the fit
    moved, _ = run_history_folds(_data(h, _changed_after(raw, folds[0].origin - 5)), folds,
                                 price_v2.history_specs("prophet", h), B2, h, every)
    assert not np.array_equal(base["pred:prophet_cps005"].to_numpy(), moved["pred:prophet_cps005"].to_numpy())
