"""Price model (Phase 4b-1, D28): regression of fwd_return_30d (log return) on the existing features.

The candidate configs and baselines are declared here, before any run (D25: at most 4 configs, no search).
Each plugs into the walk-forward harness as a Spec: fit(train_df) -> fitted, predict(fitted, inputs) -> log return.
Features are standardised with the TRAIN fold's mean and std only.
"""

from dataclasses import dataclass
from functools import partial
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from ml.evaluation.baselines import _constant, price_baselines
from ml.evaluation.walkforward import Spec
from ml.features.features import FEATURE_COLUMNS

CONFIGS = {
    "ridge_all_a100": lambda: Ridge(alpha=100.0),
    "ridge_all_a1000": lambda: Ridge(alpha=1000.0),
    "hgb_d2": lambda: HistGradientBoostingRegressor(max_depth=2, max_iter=50, learning_rate=0.03,
                                                    min_samples_leaf=50, random_state=0),
}
BASELINES = ("last_value", "drift")


@dataclass
class FittedPrice:
    config: str
    mean: np.ndarray
    std: np.ndarray
    model: Any


def fit(train: pd.DataFrame, config: str) -> FittedPrice:
    x = train[FEATURE_COLUMNS].to_numpy(dtype=float)
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std == 0, 1.0, std)                 # a constant column stays 0 after scaling
    model = CONFIGS[config]()
    model.fit((x - mean) / std, train["fwd_return_30d"].to_numpy())
    return FittedPrice(config, mean, std, model)


def predict(fitted: FittedPrice, inputs: pd.DataFrame) -> pd.Series:
    """Predicted fwd_return_30d (30-day log return), one per input row."""
    x = inputs[FEATURE_COLUMNS].to_numpy(dtype=float)
    return pd.Series(fitted.model.predict((x - fitted.mean) / fitted.std), index=inputs.index)


def spec(config: str) -> Spec:
    return Spec(fit=partial(fit, config=config), predict=predict)


def baseline_spec(name: str) -> Spec:
    """last_value predicts exactly 0; drift predicts the train-fold mean forward return (Phase 3 rules)."""
    return Spec(fit=lambda train: price_baselines(train)[name], predict=_constant)


def specs() -> dict[str, Spec]:
    out = {f"price_model/{name}": spec(name) for name in CONFIGS}
    out.update({f"price_baseline/{name}": baseline_spec(name) for name in BASELINES})
    return out
