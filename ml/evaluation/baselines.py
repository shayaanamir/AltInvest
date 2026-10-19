"""Baselines: fixed rules a model must beat (docs/EVALUATION.md, D20).

Anything a baseline learns (a mean, a majority class, thresholds) comes from TRAIN only.
Nothing here is tuned on validation or test.
"""

import numpy as np
import pandas as pd

from ml import config
from ml.labels.labels import DIRECTION_CLASSES, RISK_CLASSES, direction_class, risk_class


def majority_class(train_classes: pd.Series, classes: tuple) -> str:
    """Most common class in train; ties go to the earlier class in `classes`."""
    counts = train_classes.dropna().value_counts()
    return max(classes, key=lambda c: (counts.get(c, 0), -classes.index(c)))


# ---------- price (target: fwd_return_30d) ----------

def price_baselines(train_labels: pd.DataFrame) -> dict[str, float]:
    """Predicted 30-day log return. last_value = no change; drift = train mean forward return."""
    return {"last_value": 0.0, "drift": float(train_labels["fwd_return_30d"].dropna().mean())}


def to_price(close: pd.Series, log_return) -> pd.Series:
    """Predicted price 30 days ahead: close[t] * exp(r)."""
    return close * np.exp(log_return)


# ---------- direction ----------

def direction_baselines(feats: pd.DataFrame, train_classes: pd.Series, thresholds: dict) -> dict[str, pd.Series]:
    """Predicted class per row. momentum = class of the trailing ret_30d with the D19 threshold."""
    idx = feats.index
    return {
        "train_majority": pd.Series(majority_class(train_classes, DIRECTION_CLASSES), index=idx),
        "always_up": pd.Series("UP", index=idx),
        "momentum": direction_class(feats["ret_30d"], thresholds),
    }


# ---------- risk ----------

def risk_baselines(feats: pd.DataFrame, train_classes: pd.Series, thresholds: dict) -> dict[str, pd.Series]:
    """Predicted class per row. persistence = class of the trailing vol_30d with the train thresholds."""
    return {
        "train_majority": pd.Series(majority_class(train_classes, RISK_CLASSES), index=feats.index),
        "persistence": risk_class(feats["vol_30d"], thresholds),
    }


def risk_ranking_score(feats: pd.DataFrame) -> pd.Series:
    """Persistence ranking: today's trailing 30-day vol as the score for forward vol."""
    return feats["vol_30d"]


# ---------- strategy ----------

def window_starts(rows: range, labelled: pd.Series) -> list[int]:
    """Non-overlapping window starts: rows.start, +30, +60, ... while the start row has a label."""
    return [i for i in range(rows.start, rows.stop, config.HORIZON_DAYS) if labelled.iloc[i]]


def strategy_window_returns(fwd_return: pd.Series, starts: list[int]) -> dict[str, np.ndarray]:
    """Simple return per 30-day window. buy_and_hold holds the asset; always_hold stays in cash."""
    bh = np.exp(fwd_return.iloc[starts].to_numpy()) - 1
    return {"buy_and_hold": bh, "always_hold": np.zeros(len(starts))}
