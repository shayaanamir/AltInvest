"""Direction model (Phase 4c, D31): multinomial logistic regression for DOWN/FLAT/UP vs a class prior.

The configs and the baseline are declared here, before any run (D25: at most 4 configs, no search).
Labels are each fold's own classes (D19, D21). Features are standardised with the TRAIN fold's mean and
std only. Probabilities come in DIRECTION_CLASSES order; a class missing from a fold's train gets 0, then
every probability is clipped to [EPS, 1] and the row is renormalised.

The harness takes one Series per spec, so each predictor exposes one spec per class ("<prefix>/P_<cls>").
A FitCache makes the three class specs of a config share one fit per fold, and counts ConvergenceWarnings
once per (fold, config).
"""

import warnings
from collections import Counter
from dataclasses import dataclass
from functools import partial
from typing import Any

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from ml.evaluation.walkforward import Spec
from ml.features.features import FEATURE_COLUMNS
from ml.labels.labels import DIRECTION_CLASSES

EPS = 1e-6
CONFIGS = {
    "logreg_c0.1": lambda: LogisticRegression(C=0.1, max_iter=1000),     # lbfgs, multinomial (softmax)
    "logreg_c1": lambda: LogisticRegression(C=1.0, max_iter=1000),
}
BASELINE = "prior"


@dataclass
class FittedDirection:
    config: str
    mean: np.ndarray
    std: np.ndarray
    model: Any


def clip_renormalise(prob: np.ndarray) -> np.ndarray:
    p = np.clip(prob, EPS, 1.0)
    return p / p.sum(axis=1, keepdims=True)


def fit(train: pd.DataFrame, config: str, make_model) -> FittedDirection:
    x = train[FEATURE_COLUMNS].to_numpy(dtype=float)
    mean, std = x.mean(axis=0), x.std(axis=0)
    std = np.where(std == 0, 1.0, std)                 # a constant column stays 0 after scaling
    model = make_model()
    model.fit((x - mean) / std, train["direction"].to_numpy())
    return FittedDirection(config, mean, std, model)


def probabilities(fitted: FittedDirection, inputs: pd.DataFrame) -> pd.DataFrame:
    """P(class) per row in DIRECTION_CLASSES order, clipped to [EPS, 1] and renormalised."""
    x = (inputs[FEATURE_COLUMNS].to_numpy(dtype=float) - fitted.mean) / fitted.std
    raw = fitted.model.predict_proba(x)
    full = np.zeros((len(inputs), len(DIRECTION_CLASSES)))
    for j, cls in enumerate(fitted.model.classes_):
        full[:, DIRECTION_CLASSES.index(cls)] = raw[:, j]
    return pd.DataFrame(clip_renormalise(full), index=inputs.index, columns=list(DIRECTION_CLASSES))


def fit_prior(train: pd.DataFrame) -> np.ndarray:
    """Train-fold class frequencies (0 for an absent class), clipped and renormalised."""
    counts = train["direction"].value_counts()
    freq = np.array([[counts.get(c, 0) for c in DIRECTION_CLASSES]], dtype=float) / len(train)
    return clip_renormalise(freq)[0]


class FitCache:
    """One fit per (fold, config), shared by that config's class specs; counts ConvergenceWarnings."""

    def __init__(self, factories: dict | None = None):
        self.factories = dict(CONFIGS if factories is None else factories)
        self._last: dict[str, tuple[pd.DataFrame, FittedDirection]] = {}
        self.fits, self.warned = Counter(), Counter()

    def get(self, config: str, train: pd.DataFrame) -> FittedDirection:
        hit = self._last.get(config)
        if hit is not None and hit[0] is train:        # same fold: the harness passes one train frame per fold
            return hit[1]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted = fit(train, config, self.factories[config])
        self.fits[config] += 1
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            self.warned[config] += 1
        for w in caught:                               # re-raise anything that is not a ConvergenceWarning
            if not issubclass(w.category, ConvergenceWarning):
                warnings.warn_explicit(w.message, w.category, w.filename, w.lineno)
        self._last[config] = (train, fitted)
        return fitted

    def convergence_warnings(self) -> dict:
        return {c: {"folds_with_warning": self.warned[c], "n_folds": self.fits[c]} for c in self.factories}


def _model_column(cls: str, fitted: FittedDirection, inputs: pd.DataFrame) -> pd.Series:
    return probabilities(fitted, inputs)[cls]


def _prior_column(cls: str, prior: np.ndarray, inputs: pd.DataFrame) -> pd.Series:
    return pd.Series(prior[DIRECTION_CLASSES.index(cls)], index=inputs.index)


def specs(cache: FitCache) -> dict[str, Spec]:
    """direction_model/<cfg>/P_<cls> for every config and class, plus direction_prior/P_<cls>."""
    out = {}
    for cfg in cache.factories:
        for cls in DIRECTION_CLASSES:
            out[f"direction_model/{cfg}/P_{cls}"] = Spec(fit=partial(cache.get, cfg), predict=partial(_model_column, cls))
    for cls in DIRECTION_CLASSES:
        out[f"direction_prior/P_{cls}"] = Spec(fit=fit_prior, predict=partial(_prior_column, cls))
    return out
