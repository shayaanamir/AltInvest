"""Chronological train/validation/test splits with an embargo (D16, D17, D18).

n = rows of the feature table (after the warm-up drop).
b1 = floor(0.70n), b2 = floor(0.85n)
train = [0, b1-30), validation = [b1, b2-30), test = [b2, n)
The embargo is cut from the END of the earlier split, so labels in one split never reach the next.
"""

import math
from fractions import Fraction

import pandas as pd

from ml import config


def make_splits(n: int) -> dict[str, range]:
    """Row index ranges for each split. Fractions are made exact so 0.70*n has no float error."""
    f_train = Fraction(str(config.SPLIT_FRACTIONS["train"]))
    f_val = Fraction(str(config.SPLIT_FRACTIONS["validation"]))
    b1 = math.floor(f_train * n)
    b2 = math.floor((f_train + f_val) * n)
    e = config.EMBARGO_DAYS
    if b1 - e <= 0 or b2 - e <= b1 or b2 >= n:
        raise ValueError(f"n={n} is too small for the splits with a {e}-row embargo")
    return {"train": range(0, b1 - e), "validation": range(b1, b2 - e), "test": range(b2, n)}


def split_dates(index: pd.DatetimeIndex, splits: dict[str, range]) -> dict[str, dict[str, str]]:
    """First and last timestamp of each split for one asset's feature table."""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return {name: {"first": index[r.start].strftime(fmt), "last": index[r.stop - 1].strftime(fmt)}
            for name, r in splits.items()}
