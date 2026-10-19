"""Expanding-window walk-forward harness (D21). The test split [b2, n) is sealed.

At origin t a fold trains on rows [0, t-30) (embargo = horizon, so every train label ends before t)
and predicts rows [t, t+step). Origins start at min_train + horizon and stop before b2 - horizon.

Any model plugs in as a Spec:
    fit(train_df) -> predictor          train_df: features, close, labels and fold classes of the train rows
    predict(predictor, inputs) -> Series  inputs: features and close of the predict rows only (no labels)
"""

from dataclasses import dataclass
from typing import Any, Callable, NamedTuple

import pandas as pd

from ml import config
from ml.features.features import FEATURE_COLUMNS
from ml.labels.labels import apply_thresholds, fit_thresholds

INPUT_COLUMNS = FEATURE_COLUMNS + ["close"]


class SealedTestError(ValueError):
    """Raised when anything asks for a row at or after b2 (the sealed test split)."""


class Spec(NamedTuple):
    fit: Callable[[pd.DataFrame], Any]
    predict: Callable[[Any, pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class Fold:
    origin: int
    train: range
    predict: range


def check_before_test(rows: range, b2: int) -> None:
    if len(rows) and (rows.start < 0 or rows.stop > b2):
        raise SealedTestError(f"rows {rows.start}..{rows.stop - 1} reach the sealed test split (b2={b2})")


def make_folds(n_rows: int, b2: int, min_train: int = config.MIN_TRAIN_ROWS,
               step: int = config.WALKFORWARD_STEP, horizon: int = config.HORIZON_DAYS) -> list[Fold]:
    """Folds over [0, b2 - horizon). The last predict range is cut at b2 - horizon and may be shorter."""
    if b2 > n_rows:
        raise ValueError(f"b2={b2} is beyond n_rows={n_rows}")
    end, first = b2 - horizon, min_train + horizon
    if first >= end:
        raise ValueError(f"no folds: first origin {first} >= end {end}")
    folds = [Fold(t, range(0, t - horizon), range(t, min(t + step, end))) for t in range(first, end, step)]
    for f in folds:
        check_before_test(f.train, b2)
        check_before_test(f.predict, b2)
    return folds


def run_folds(data: pd.DataFrame, folds: list[Fold], specs: dict[str, Spec], b2: int):
    """Fit and predict every spec on every fold.

    `data` holds only rows before b2: INPUT_COLUMNS plus fwd_return_30d and fwd_vol_30d (and any other
    label columns). Returns (pooled, fold_table): pooled has one row per predicted row with the actual
    labels, the fold's classes, the origin, and a `pred:<name>` column per spec.
    """
    if len(data) > b2:
        raise SealedTestError(f"data has {len(data)} rows; only rows before b2={b2} may be passed in")
    parts, table = [], []
    for f in folds:
        check_before_test(f.train, b2)
        check_before_test(f.predict, b2)
        train = data.iloc[f.train].copy()
        th = fit_thresholds(train)                              # D19 per fold, train rows only
        train[["direction", "risk"]] = apply_thresholds(train, th)
        actual = data.iloc[f.predict]
        inputs = actual[INPUT_COLUMNS]
        out = actual.drop(columns=FEATURE_COLUMNS).copy()
        out[["direction", "risk"]] = apply_thresholds(actual, th)
        out["origin"] = f.origin
        out["row"] = list(f.predict)
        for name, spec in specs.items():
            pred = spec.predict(spec.fit(train), inputs)
            if not pred.index.equals(inputs.index):
                raise ValueError(f"spec {name} returned predictions for the wrong rows")
            out[f"pred:{name}"] = pred.to_numpy()
        parts.append(out)
        table.append({"origin": f.origin, "origin_date": data.index[f.origin].strftime("%Y-%m-%d"),
                      "train_rows": len(f.train), "predict_rows": len(f.predict), "thresholds": th})
    return pd.concat(parts), table
