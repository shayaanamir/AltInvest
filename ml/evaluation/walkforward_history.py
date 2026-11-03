"""Walk-forward for models that use INPUTS known at t (D48): Prophet (corrected protocol), later GARCH.

The embargo applies to labels, not inputs. At refit origin r a HistorySpec is fitted with
    train:  the fold's train rows [0, r - h), with labels (may be ignored)
    inputs: INPUT_COLUMNS of rows [0, r], no labels (closes known at r)
and predicts row s of a fold with predict(model, history, rows), history = INPUT_COLUMNS of rows [0, rows.stop).
A prediction for row s must use history rows <= s only (tested per model). Refit cadence (D41): fold k uses the
fit made at the origin of fold k - k % every. Test rows [b2, n) are never passed in.
"""

import time
from typing import Any, Callable, NamedTuple

import numpy as np
import pandas as pd

from ml.evaluation.walkforward import (INPUT_COLUMNS, Fold, SealedTestError, check_before_test,
                                       check_label_horizons)
from ml.features.features import FEATURE_COLUMNS


class HistorySpec(NamedTuple):
    fit: Callable[[pd.DataFrame, pd.DataFrame], Any]
    predict: Callable[[Any, pd.DataFrame, range], np.ndarray]


def run_history_folds(data: pd.DataFrame, folds: list[Fold], specs: dict[str, HistorySpec], b2: int,
                      horizon: int, every: int) -> tuple[pd.DataFrame, dict]:
    """Returns (pooled rows like run_folds with pred:<name>, run info with fit counts and seconds)."""
    if len(data) > b2:
        raise SealedTestError(f"data has {len(data)} rows; only rows before b2={b2} may be passed in")
    check_label_horizons(data, horizon)
    inputs = data[INPUT_COLUMNS]
    fitted, n_fits, fit_seconds, parts = {}, {k: 0 for k in specs}, {k: 0.0 for k in specs}, []
    for k, f in enumerate(folds):
        check_before_test(f.train, b2)
        check_before_test(f.predict, b2)
        r = folds[k - k % every]
        if len(r.train) and r.train.stop > r.origin - horizon:
            raise ValueError(f"fold at {r.origin}: train rows inside the {horizon}-row embargo")
        part = data.iloc[f.predict].drop(columns=FEATURE_COLUMNS).copy()
        part["origin"], part["row"] = f.origin, list(f.predict)
        history = inputs.iloc[:f.predict.stop]
        for name, spec in specs.items():
            if (name, r.origin) not in fitted:
                t0 = time.perf_counter()
                fitted[(name, r.origin)] = spec.fit(data.iloc[r.train], inputs.iloc[:r.origin + 1])
                fit_seconds[name] += time.perf_counter() - t0
                n_fits[name] += 1
            pred = np.asarray(spec.predict(fitted[(name, r.origin)], history, f.predict), dtype=float)
            if pred.shape != (len(f.predict),):
                raise ValueError(f"{name} returned {pred.shape} predictions for {len(f.predict)} rows")
            part[f"pred:{name}"] = pred
        parts.append(part)
    return pd.concat(parts), {"refit_every_folds": every, "refit_every_rows": every * horizon,
                              "n_fits": n_fits, "fit_seconds": fit_seconds}
