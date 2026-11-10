"""Floor-volatility rows for one collection (D59), built like the crypto feature table (D18, D24).

close = floor_eth_asof (D63: the as-of floor with no age limit, so the series has a value every day).
ret_1d = daily log return, vol_30d = std of the last 30 returns; the first WARMUP_ROWS rows are dropped.
Labels come from ml.labels.labels.build_labels (fwd_vol_30d = std of the 30 returns after t).
dev_frame cuts the series before the first sealed test row BEFORE anything is computed, so no test floor
ever enters a feature, a label or a fit (plan rule 3). test_frame is for the one-time sealed test (10.8).
"""

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation.splits import make_splits
from ml.labels.labels import build_labels

FEATURES = ["ret_1d", "vol_30d"]
H = config.HORIZON_DAYS


def floor_series(floor_one: pd.DataFrame) -> pd.Series:
    """floor_eth_asof indexed by UTC date. Refuses gaps or duplicates in the dates and non-positive floors."""
    f = floor_one.sort_values("date")
    idx = pd.to_datetime(f["date"], utc=True)
    if not (idx.diff().dropna() == pd.Timedelta(days=1)).all():
        raise ValueError("floor dates must be consecutive calendar days with no gaps or duplicates")
    close = pd.Series(f["floor_eth_asof"].to_numpy(dtype=float), index=pd.DatetimeIndex(idx, name="timestamp"),
                      name="close")
    if close.isna().any() or (close <= 0).any():
        raise ValueError("floor_eth_asof must be a positive number on every date")
    return close


def features(close: pd.Series) -> pd.DataFrame:
    """ret_1d, vol_30d and close, first WARMUP_ROWS rows dropped. Trailing windows only."""
    r = np.log(close).diff()
    out = pd.DataFrame({"ret_1d": r, "vol_30d": r.rolling(30).std(), "close": close})
    return out.iloc[config.WARMUP_ROWS:]


def split_point(n_days: int, horizon: int = H) -> tuple[int, int]:
    """(b2, n): n = feature rows, b2 = first sealed test row (D16, D18 with config.SPLIT_FRACTIONS)."""
    n = n_days - config.WARMUP_ROWS
    return make_splits(n, embargo=horizon)["test"].start, n


def with_labels(close: pd.Series, horizon: int = H) -> pd.DataFrame:
    feats = features(close)
    return feats.join(build_labels(close, horizon).loc[feats.index])


def dev_frame(floor_one: pd.DataFrame, horizon: int = H) -> tuple[pd.DataFrame, int, int]:
    """(feature and label rows [0, b2), b2, n). Test rows are cut off first."""
    close = floor_series(floor_one)
    b2, n = split_point(len(close), horizon)
    data = with_labels(close.iloc[:config.WARMUP_ROWS + b2], horizon)
    assert len(data) == b2
    return data, b2, n


def test_frame(floor_one: pd.DataFrame, horizon: int = H) -> tuple[pd.DataFrame, int, int]:
    """(labelled test rows [b2, n - h), b2, n). ONLY for the one-time sealed test (step 10.8)."""
    close = floor_series(floor_one)
    b2, n = split_point(len(close), horizon)
    data = with_labels(close, horizon).iloc[b2:]
    return data[data[f"fwd_vol_{horizon}d"].notna()], b2, n


def test_start_date(floor_one: pd.DataFrame) -> str:
    """Date of the first sealed test row (also the start of the fair-value sealed test, D60)."""
    f = floor_one.sort_values("date")
    b2, _ = split_point(len(f))
    return f["date"].iloc[config.WARMUP_ROWS + b2]
