"""Phase 9 price candidates fitted per asset (D42): Ridge reference, LightGBM, Prophet. The pooled LSTM is in
ml/models/lstm.py. Target: fwd_return_{h}d (h-day log return), h = 30 or 7 (D41).

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


def prophet_fit(train: pd.DataFrame, config: str) -> Any:
    """Prophet on the log close of the fold's TRAIN rows only (planner, 9.2c)."""
    from prophet import Prophet
    _quiet_prophet()
    df = pd.DataFrame({"ds": train.index.tz_localize(None), "y": np.log(train["close"].to_numpy(dtype=float))})
    model = Prophet(**PROPHET_PARAMS, **PROPHET_CONFIGS[config])
    model.fit(df)
    return model


def prophet_predict(model: Any, inputs: pd.DataFrame, horizon: int) -> pd.Series:
    """Predicted h-day log return at row t = forecast log price at t + h days minus log close at t."""
    future = pd.DataFrame({"ds": (inputs.index + pd.Timedelta(days=horizon)).tz_localize(None)})
    yhat = model.predict(future)["yhat"].to_numpy()
    return pd.Series(yhat - np.log(inputs["close"].to_numpy(dtype=float)), index=inputs.index)


# --- specs ---------------------------------------------------------------------------------------------------

MODEL_CONFIGS = {"ridge": list(RIDGE_CONFIGS), "lightgbm": list(LIGHTGBM_CONFIGS),
                 "prophet": list(PROPHET_CONFIGS)}


def refit_every_folds(model: str, horizon: int) -> int:
    """D41 cadence in folds: Prophet (and the LSTM) every 28 rows at h = 7; everything else every fold."""
    return PROPHET_REFIT_EVERY_ROWS_AT_7 // horizon if model == "prophet" and horizon == 7 else 1


def specs(model: str, horizon: int) -> dict[str, Spec]:
    """Fresh Specs (with fresh refit state) for one asset and horizon. Keys are the config names."""
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
    return {name: {**PROPHET_PARAMS, **p} for name, p in PROPHET_CONFIGS.items()} | {
        "input": "log close of the fold's train rows only", "algorithm": "Prophet default (MAP, L-BFGS)"}
