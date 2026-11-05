"""Walk-forward for models pooled over assets (Phase 9, D41/D42). Scored and approved per asset.

Each asset keeps its own folds (make_folds, embargo = step = h). A pooled fit for a fold with origin date D
trains on every asset's rows dated before D - h days that have a label. Those labels end before D, and each
asset's frame holds only its rows before its own b2, so no asset's sealed test rows are ever used (BTC/ETH
test starts before SOL's). Fits are cached by (config, D): BTC and ETH share dates and so share fits. Refit
cadence: a fold reuses the fit of the latest fold k - k % every (past data only).

A PooledSpec has fit(train_sets: {asset: train rows}) -> model and
predict(model, asset, history: INPUT_COLUMNS rows [0, stop), rows: range) -> array.
"""

import time
from typing import Any, Callable, NamedTuple

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation.walkforward import (INPUT_COLUMNS, SealedTestError, check_before_test, check_label_horizons,
                                       make_folds)
from ml.features.features import FEATURE_COLUMNS


class PooledSpec(NamedTuple):
    fit: Callable[[dict[str, pd.DataFrame]], Any]
    predict: Callable[[Any, str, pd.DataFrame, range], np.ndarray]


def pooled_train_sets(datas: dict[str, tuple[pd.DataFrame, int]], cutoff: pd.Timestamp,
                      horizon: int) -> dict[str, pd.DataFrame]:
    """Every asset's rows dated before cutoff - h days with a label, in time order."""
    label = f"fwd_return_{horizon}d"
    limit = cutoff - pd.Timedelta(days=horizon)
    out = {}
    for asset, (data, b2) in datas.items():
        rows = data[(data.index < limit) & data[label].notna()]
        if len(rows):
            check_before_test(range(0, data.index.get_loc(rows.index[-1]) + 1), b2)
            out[asset] = rows
    return out


def asset_folds(data: pd.DataFrame, b2: int, horizon: int):
    return make_folds(len(data), b2, config.MIN_TRAIN_ROWS, horizon, horizon)


def run_pooled(datas: dict[str, tuple[pd.DataFrame, int]], specs: dict[str, PooledSpec], horizon: int,
               every: int) -> tuple[dict[str, pd.DataFrame], dict]:
    """Returns ({asset: pooled rows like run_folds, with pred:<config>}, run info with fit counts and times)."""
    for asset, (data, b2) in datas.items():
        if len(data) > b2:
            raise SealedTestError(f"{asset}: data has {len(data)} rows; only rows before b2={b2} may be passed in")
        check_label_horizons(data, horizon)
    cache, fit_seconds, n_fits, out = {}, {name: 0.0 for name in specs}, {name: 0 for name in specs}, {}
    for asset, (data, b2) in datas.items():
        folds = asset_folds(data, b2, horizon)
        parts = []
        for k, f in enumerate(folds):
            cutoff = data.index[folds[k - k % every].origin]
            part = data.iloc[f.predict].drop(columns=FEATURE_COLUMNS).copy()
            part["origin"], part["row"] = f.origin, list(f.predict)
            history = data.iloc[:f.predict.stop][INPUT_COLUMNS]
            for name, spec in specs.items():
                key = (name, cutoff)
                if key not in cache:
                    t0 = time.perf_counter()
                    cache[key] = spec.fit(pooled_train_sets(datas, cutoff, horizon))
                    fit_seconds[name] += time.perf_counter() - t0
                    n_fits[name] += 1
                pred = np.asarray(spec.predict(cache[key], asset, history, f.predict), dtype=float)
                if pred.shape != (len(f.predict),):
                    raise ValueError(f"{name} returned {pred.shape} predictions for {len(f.predict)} rows")
                part[f"pred:{name}"] = pred
            parts.append(part)
        out[asset] = pd.concat(parts)
    info = {"refit_every_folds": every, "refit_every_rows": every * horizon, "n_fits": n_fits,
            "fit_seconds": fit_seconds,
            "fit_cache": "fits keyed by (config, cutoff date); assets with the same fold dates share fits"}
    return out, info
