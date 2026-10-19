"""Risk model (Phase 4a, D24): regression of log(fwd_vol_30d) on the existing features.

The candidate configs are declared here, before any run (D25: at most 4, no search). Each plugs into
the walk-forward harness as a Spec: fit(train_df) -> FittedRisk, predict(fitted, inputs) -> log-vol.
Features are standardised with the TRAIN fold's mean and std only.
"""

from dataclasses import dataclass
from functools import partial
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from ml.evaluation.walkforward import Spec
from ml.features.features import FEATURE_COLUMNS

HAR_COLUMNS = ["log_vol_7d", "log_vol_30d"]

CONFIGS = {
    "har_ridge_a1": {"features": "har", "model": lambda: Ridge(alpha=1.0)},
    "ridge_all_a1": {"features": "all", "model": lambda: Ridge(alpha=1.0)},
    "ridge_all_a10": {"features": "all", "model": lambda: Ridge(alpha=10.0)},
    "hgb_d3": {"features": "all", "model": lambda: HistGradientBoostingRegressor(
        max_depth=3, max_iter=100, learning_rate=0.05, random_state=0)},
}


@dataclass
class FittedRisk:
    config: str
    columns: list[str]
    mean: np.ndarray
    std: np.ndarray
    model: Any


def design(inputs: pd.DataFrame, config: str) -> tuple[np.ndarray, list[str]]:
    """Model inputs for a config. HAR uses log of the two existing vol features; others use all features."""
    if CONFIGS[config]["features"] == "har":
        x = np.column_stack([np.log(inputs["vol_7d"]), np.log(inputs["vol_30d"])])
        return x, HAR_COLUMNS
    return inputs[FEATURE_COLUMNS].to_numpy(dtype=float), list(FEATURE_COLUMNS)


def fit(train: pd.DataFrame, config: str) -> FittedRisk:
    x, cols = design(train, config)
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std == 0, 1.0, std)                 # a constant column stays 0 after scaling
    model = CONFIGS[config]["model"]()
    model.fit((x - mean) / std, np.log(train["fwd_vol_30d"].to_numpy()))
    return FittedRisk(config, cols, mean, std, model)


def predict(fitted: FittedRisk, inputs: pd.DataFrame) -> pd.Series:
    """Predicted log(fwd_vol_30d), one per input row."""
    x, _ = design(inputs, fitted.config)
    return pd.Series(fitted.model.predict((x - fitted.mean) / fitted.std), index=inputs.index)


def spec(config: str) -> Spec:
    return Spec(fit=partial(fit, config=config), predict=predict)


def specs() -> dict[str, Spec]:
    return {f"risk_model/{name}": spec(name) for name in CONFIGS}
