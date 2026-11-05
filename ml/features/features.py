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


def ewma_vol(close: pd.Series, lam: float = config.EWMA_LAMBDA) -> pd.Series:
    """EWMA (RiskMetrics) daily volatility (D41), same index as `close`, same daily units as vol_30d.

    sigma2[t] = lam x sigma2[t-1] + (1 - lam) x r[t]^2, r = daily log return. Seeded at row WARMUP_ROWS with
    vol_30d^2 of that row; NaN before it. Uses only returns at or before t. Not a model input (FEATURE_COLUMNS
    is unchanged); Phase 9 uses it as a baseline and in range bands.
    """
    if not 0.0 < lam < 1.0:
        raise ValueError(f"lam must be in (0, 1), got {lam!r}")
    r = np.log(close).diff()
    r2 = (r * r).to_numpy(dtype=float)
    out = np.full(len(r2), np.nan)
    start = config.WARMUP_ROWS
    if len(r2) > start:
        out[start] = r.rolling(30).std().iloc[start] ** 2
        for t in range(start + 1, len(r2)):
            out[t] = lam * out[t - 1] + (1.0 - lam) * r2[t]
    return pd.Series(np.sqrt(out), index=close.index, name="ewma_vol")
