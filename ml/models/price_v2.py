"""Phase 9 price candidates fitted per asset (D42): Ridge reference, LightGBM, Prophet. The pooled LSTM is in
ml/models/lstm.py. Target: fwd_return_{h}d (h-day log return), h = 30 or 7 (D41).

Prophet has two protocols. "prophet" (D48, corrected): fit on log close up to the refit origin (inputs known at
t), return = forecast(t + h) - forecast(t) from the same fit; runs through ml/evaluation/walkforward_history.py.
"prophet_9_2" (9.2 protocol, superseded): fit on the fold's train rows only, return = forecast(t + h) - log
close(t); kept so the 9.2 rows can be reproduced, never served.

Configs are declared here before any run (D25, at most 4 per model type). Each plugs into the walk-forward
harness as a Spec. Training libraries are imported inside the functions, so importing this module needs none.
"""

import logging
import time
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable

import numpy as np
import pandas as pd

from ml.evaluation.walkforward import Spec
from ml.features.features import FEATURE_COLUMNS
from ml.models import price

RIDGE_CONFIGS = ("ridge_all_a100", "ridge_all_a1000")          # same alphas at h = 30 and 7 (planner, 9.2)
LIGHTGBM_PARAMS = {"n_estimators": 200, "learning_rate": 0.03, "min_child_samples": 50,   # min_data_in_leaf
                   "random_state": 0, "n_jobs": 1, "deterministic": True, "force_row_wise": True, "verbose": -1}
LIGHTGBM_CONFIGS = {"lgbm_l7": {"num_leaves": 7}, "lgbm_l15": {"num_leaves": 15}}
PROPHET_PARAMS = {"yearly_seasonality": False, "weekly_seasonality": "auto", "daily_seasonality": False,
                  "uncertainty_samples": 0}
PROPHET_CONFIGS = {"prophet_cps005": {"changepoint_prior_scale": 0.05},
                   "prophet_cps05": {"changepoint_prior_scale": 0.5}}
PROPHET_REFIT_EVERY_ROWS_AT_7 = 28                              # D41: every 4th fold at h = 7, every fold at 30


def target(horizon: int) -> str:
    return f"fwd_return_{horizon}d"


class RefitEvery:
    """Fit on every `every`-th call, else return the last fitted model. The harness calls fit once per fold
    in time order, so the reused model was fitted on an earlier fold's (shorter) train rows: past data only."""

    def __init__(self, fit: Callable[[pd.DataFrame], Any], every: int):
        self.fit, self.every, self.calls, self.n_fits, self.fit_seconds, self.last = fit, every, 0, 0, 0.0, None

    def __call__(self, train: pd.DataFrame) -> Any:
        if self.calls % self.every == 0:
            t0 = time.perf_counter()
            self.last = self.fit(train)
            self.fit_seconds += time.perf_counter() - t0
            self.n_fits += 1
        self.calls += 1
        return self.last


# --- LightGBM ------------------------------------------------------------------------------------------------

@dataclass
class FittedTrees:
    model: Any


def lightgbm_fit(train: pd.DataFrame, config: str, horizon: int) -> FittedTrees:
    import lightgbm
    model = lightgbm.LGBMRegressor(**LIGHTGBM_PARAMS, **LIGHTGBM_CONFIGS[config])
    model.fit(train[FEATURE_COLUMNS].to_numpy(dtype=float), train[target(horizon)].to_numpy())
    return FittedTrees(model)


def trees_predict(fitted: FittedTrees, inputs: pd.DataFrame) -> pd.Series:
    return pd.Series(fitted.model.predict(inputs[FEATURE_COLUMNS].to_numpy(dtype=float)), index=inputs.index)


# --- Prophet -------------------------------------------------------------------------------------------------

def _quiet_prophet() -> None:
    for name in ("cmdstanpy", "prophet"):
        logging.getLogger(name).setLevel(logging.ERROR)


def prophet_fit(rows: pd.DataFrame, config: str) -> Any:
    """Prophet on the log close of `rows` (9.2 protocol: the fold's train rows; D48: inputs up to the origin)."""
    from prophet import Prophet
    _quiet_prophet()
    df = pd.DataFrame({"ds": rows.index.tz_localize(None), "y": np.log(rows["close"].to_numpy(dtype=float))})
    model = Prophet(**PROPHET_PARAMS, **PROPHET_CONFIGS[config])
    model.fit(df)
    return model


def _forecast(model: Any, dates: pd.DatetimeIndex) -> np.ndarray:
    return model.predict(pd.DataFrame({"ds": dates.tz_localize(None)}))["yhat"].to_numpy()


def prophet_predict(model: Any, inputs: pd.DataFrame, horizon: int) -> pd.Series:
    """9.2 protocol (superseded): forecast log price at t + h days minus the actual log close at t."""
    yhat = _forecast(model, inputs.index + pd.Timedelta(days=horizon))
    return pd.Series(yhat - np.log(inputs["close"].to_numpy(dtype=float)), index=inputs.index)


def prophet_fit_inputs(train: pd.DataFrame, inputs: pd.DataFrame, config: str) -> Any:
    """D48: fit on the log close of rows [0, r] (known at the refit origin r). `train` (labels) is unused."""
    return prophet_fit(inputs, config)


def prophet_predict_change(model: Any, history: pd.DataFrame, rows: range, horizon: int) -> np.ndarray:
    """D48: forecast(s + h days) - forecast(s), both from the same fit, for each row s. Uses only the dates."""
    dates = history.index[rows.start:rows.stop]
    return _forecast(model, dates + pd.Timedelta(days=horizon)) - _forecast(model, dates)


def history_specs(model: str, horizon: int) -> dict:
    """HistorySpecs for models that use inputs known at t (D48). Only the corrected Prophet so far."""
    from ml.evaluation.walkforward_history import HistorySpec
    if model != "prophet":
        raise ValueError(f"no history protocol for {model}")
    return {name: HistorySpec(fit=partial(prophet_fit_inputs, config=name),
                              predict=partial(prophet_predict_change, horizon=horizon))
            for name in PROPHET_CONFIGS}


# --- specs ---------------------------------------------------------------------------------------------------

MODEL_CONFIGS = {"ridge": list(RIDGE_CONFIGS), "lightgbm": list(LIGHTGBM_CONFIGS),
                 "prophet_9_2": list(PROPHET_CONFIGS), "prophet": list(PROPHET_CONFIGS)}
HISTORY_MODELS = ("prophet",)                                   # run through walkforward_history (D48)


def refit_every_folds(model: str, horizon: int) -> int:
    """D41 cadence in folds: Prophet (and the LSTM) every 28 rows at h = 7; everything else every fold."""
    return PROPHET_REFIT_EVERY_ROWS_AT_7 // horizon if model.startswith("prophet") and horizon == 7 else 1


def specs(model: str, horizon: int) -> dict[str, Spec]:
    """Fresh harness Specs (with fresh refit state) for one asset and horizon. Keys are the config names."""
    if model in HISTORY_MODELS:
        raise ValueError(f"{model} runs through walkforward_history; use history_specs")
    every = refit_every_folds(model, horizon)
    out = {}
    for name in MODEL_CONFIGS[model]:
        if model == "ridge":
            fit, pred = partial(price.fit, config=name, target=target(horizon)), price.predict
        elif model == "lightgbm":
            fit, pred = partial(lightgbm_fit, config=name, horizon=horizon), trees_predict
        else:
            fit, pred = partial(prophet_fit, config=name), partial(prophet_predict, horizon=horizon)
        out[name] = Spec(fit=RefitEvery(fit, every), predict=pred)
    return out


def declared(model: str) -> dict:
    """What the report records about the configs (declared before any run)."""
    if model == "ridge":
        return {name: repr(price.CONFIGS[name]()) for name in RIDGE_CONFIGS} | {
            "scaling": "standardised with the train fold's mean/std", "role": "reference (4b), ranked and counted"}
    if model == "lightgbm":
        return {name: {**LIGHTGBM_PARAMS, **p} for name, p in LIGHTGBM_CONFIGS.items()} | {"scaling": "none"}
    out = {name: {**PROPHET_PARAMS, **p} for name, p in PROPHET_CONFIGS.items()}
    out["algorithm"] = "Prophet default (MAP, L-BFGS)"
    if model == "prophet":
        out["protocol"] = ("D48 (corrected): fit on log close of rows [0, r] at refit origin r; return = "
                           "forecast(t + h) - forecast(t) from the same fit")
    else:
        out["protocol"] = ("9.2 protocol, superseded by D48: fit on log close of the fold's train rows only; "
                           "return = forecast(t + h) - log close(t). Reported, never served")
    return out
