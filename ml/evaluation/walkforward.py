"""Expanding-window walk-forward harness (D21). The test split [b2, n) is sealed.

At origin t a fold trains on rows [0, t-h) (embargo = horizon h, so every train label ends before t)
and predicts rows [t, t+step). Origins start at min_train + h and stop before b2 - h. Default h = step = 30;
Phase 9 also runs h = step = 7 (D41).

Any model plugs in as a Spec:
    fit(train_df) -> predictor          train_df: features, close, labels and fold classes of the train rows
    predict(predictor, inputs) -> Series  inputs: features and close of the predict rows only (no labels)
"""

import re
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


_LABEL_COLUMN = re.compile(r"^(?:fwd_[a-z]+|close_fwd)_(\d+)d$")


def label_horizon(column: str) -> int | None:
    """Horizon in rows of a label column (fwd_return_7d -> 7, close_fwd_30d -> 30); None for other columns."""
    match = _LABEL_COLUMN.match(column)
    return int(match.group(1)) if match else None


def check_label_horizons(data: pd.DataFrame, horizon: int) -> None:
    """A fold's train rows end `horizon` rows before its origin, so a label looking further ahead would
    reach into the predict window. Refuse any such column."""
    longer = [c for c in data.columns if (label_horizon(c) or 0) > horizon]
    if longer:
        raise ValueError(f"label columns {longer} look further ahead than the horizon {horizon} (D41)")


def run_folds(data: pd.DataFrame, folds: list[Fold], specs: dict[str, Spec], b2: int,
              horizon: int = config.HORIZON_DAYS):
    """Fit and predict every spec on every fold.

    `data` holds only rows before b2: INPUT_COLUMNS plus the label columns of `horizon` (fwd_return_30d and
    fwd_vol_30d by default). Returns (pooled, fold_table): pooled has one row per predicted row with the actual
    labels, the origin, and a `pred:<name>` column per spec. At h = 30 the fold's D19 classes are added; class
    thresholds exist for the 30-day labels only (D42), so other horizons get no classes.
    """
    if len(data) > b2:
        raise SealedTestError(f"data has {len(data)} rows; only rows before b2={b2} may be passed in")
    check_label_horizons(data, horizon)
    with_classes = horizon == config.HORIZON_DAYS
    parts, table = [], []
    for f in folds:
        check_before_test(f.train, b2)
        check_before_test(f.predict, b2)
        if len(f.train) and f.train.stop > f.origin - horizon:
            raise ValueError(f"fold at {f.origin}: train rows end at {f.train.stop - 1}, inside the {horizon}-row "
                             "embargo")
        train = data.iloc[f.train].copy()
        actual = data.iloc[f.predict]
        inputs = actual[INPUT_COLUMNS]
        out = actual.drop(columns=FEATURE_COLUMNS).copy()
        th = None
        if with_classes:
            th = fit_thresholds(train)                          # D19 per fold, train rows only
            train[["direction", "risk"]] = apply_thresholds(train, th)
            out[["direction", "risk"]] = apply_thresholds(actual, th)
        out["origin"] = f.origin
        out["row"] = list(f.predict)
        for name, spec in specs.items():
            pred = spec.predict(spec.fit(train), inputs)
            if not pred.index.equals(inputs.index):
                raise ValueError(f"spec {name} returned predictions for the wrong rows")
            out[f"pred:{name}"] = pred.to_numpy()
        parts.append(out)
        row = {"origin": f.origin, "origin_date": data.index[f.origin].strftime("%Y-%m-%d"),
               "train_rows": len(f.train), "predict_rows": len(f.predict)}
        if with_classes:
            row["thresholds"] = th
        table.append(row)
    return pd.concat(parts), table
