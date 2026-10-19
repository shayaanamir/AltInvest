"""Model inputs built only from data at or before each row (docs/DATA.md, D18).

Every column is a trailing (backward-looking) window, so the value at row t never uses rows after t.
Windows count rows, which equal days only because the raw data has no gaps; build_features refuses gaps.
No scaling, no filling.
"""

import numpy as np
import pandas as pd

from ml import config

FEATURE_COLUMNS = [
    "ret_1d", "ret_7d", "ret_30d",
    "vol_7d", "vol_30d",
    "price_over_ma7", "price_over_ma30", "ma_cross",
    "volume_ratio_30d", "hl_range_7d",
]
DAY = pd.Timedelta(days=1)


def _require_daily(timestamps: pd.Series) -> None:
    """Row windows are only day windows if bars are consecutive calendar days."""
    steps = timestamps.diff().dropna()
    if not (steps == DAY).all():
        raise ValueError("bars must be consecutive calendar days with no gaps or duplicates")


def ma_cross(close: pd.Series, ma7: pd.Series, ma30: pd.Series) -> pd.Series:
    """+1 if close > MA7 > MA30, -1 if close < MA7 < MA30, else 0."""
    up = (close > ma7) & (ma7 > ma30)
    down = (close < ma7) & (ma7 < ma30)
    return pd.Series(np.select([up, down], [1, -1], 0), index=close.index)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature table indexed by timestamp, first WARMUP_ROWS rows dropped. No label columns."""
    df = df.sort_values("timestamp")
    _require_daily(df["timestamp"])
    df = df.set_index("timestamp")
    close, log_close = df["close"], np.log(df["close"])
    r = log_close.diff()
    ma7, ma30 = close.rolling(7).mean(), close.rolling(30).mean()

    feats = pd.DataFrame({
        "ret_1d": r,
        "ret_7d": log_close.diff(7),
        "ret_30d": log_close.diff(30),
        "vol_7d": r.rolling(7).std(),
        "vol_30d": r.rolling(30).std(),
        "price_over_ma7": close / ma7,
        "price_over_ma30": close / ma30,
        "ma_cross": ma_cross(close, ma7, ma30),
        "volume_ratio_30d": np.log(df["volume"] / df["volume"].rolling(30).mean()),
        "hl_range_7d": np.log(df["high"] / df["low"]).rolling(7).mean(),
    }, index=df.index)
    return feats[FEATURE_COLUMNS].iloc[config.WARMUP_ROWS:]
