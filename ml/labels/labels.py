"""Forward-looking targets and their class thresholds (D3, D9, D19, D41).

Labels look `horizon` rows ahead (default HORIZON_DAYS = 30), so the last `horizon` rows are NaN.
They live only in memory and reports; they are never written to the raw CSVs.
Class thresholds and classes are defined for the 30-day labels only (direction runs at h = 30 only, D42).
"""

import numpy as np
import pandas as pd

from ml import config

H = config.HORIZON_DAYS
DIRECTION_CLASSES = ("DOWN", "FLAT", "UP")
RISK_CLASSES = ("low", "medium", "high")


def _check_horizon(horizon: int) -> int:
    if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 1:
        raise ValueError(f"horizon must be a positive whole number of rows, got {horizon!r}")
    return int(horizon)


def fwd_return(close: pd.Series, horizon: int = H) -> pd.Series:
    """ln(close[t+h] / close[t])."""
    h = _check_horizon(horizon)
    return np.log(close.shift(-h) / close)


def fwd_vol(close: pd.Series, horizon: int = H) -> pd.Series:
    """Std (ddof=1) of the daily log returns t+1..t+h (the h returns after t)."""
    h = _check_horizon(horizon)
    r = np.log(close / close.shift(1))
    return r.rolling(h).std().shift(-h)


def fwd_return_30d(close: pd.Series) -> pd.Series:
    """ln(close[t+30] / close[t])."""
    return fwd_return(close, H)


def fwd_vol_30d(close: pd.Series) -> pd.Series:
    """Std of the daily log returns t+1..t+30 (the 30 returns after t)."""
    return fwd_vol(close, H)


def build_labels(close: pd.Series, horizon: int = H) -> pd.DataFrame:
    """Columns fwd_return_{h}d and fwd_vol_{h}d (fwd_return_30d, fwd_vol_30d by default)."""
    h = _check_horizon(horizon)
    return pd.DataFrame({f"fwd_return_{h}d": fwd_return(close, h), f"fwd_vol_{h}d": fwd_vol(close, h)})


def fit_thresholds(train_labels: pd.DataFrame) -> dict:
    """D19: percentiles of the TRAIN labels only. Rows without a label are ignored."""
    ret = train_labels["fwd_return_30d"].dropna()
    vol = train_labels["fwd_vol_30d"].dropna()
    lo, hi = config.RISK_PERCENTILES
    return {
        "direction_flat_abs_return": float(np.percentile(ret.abs(), config.DIRECTION_FLAT_PERCENTILE)),
        "risk_low_max_vol": float(np.percentile(vol, lo)),
        "risk_high_min_vol": float(np.percentile(vol, hi)),
    }


def direction_class(ret: pd.Series, thresholds: dict) -> pd.Series:
    """UP if r > t, DOWN if r < -t, else FLAT. NaN stays NaN."""
    t = thresholds["direction_flat_abs_return"]
    out = pd.Series(np.select([ret > t, ret < -t], ["UP", "DOWN"], "FLAT"), index=ret.index)
    return out.where(ret.notna())


def risk_class(vol: pd.Series, thresholds: dict) -> pd.Series:
    """low if vol <= p33, high if vol > p67, else medium. NaN stays NaN."""
    out = pd.Series(
        np.select([vol <= thresholds["risk_low_max_vol"], vol > thresholds["risk_high_min_vol"]],
                  ["low", "high"], "medium"),
        index=vol.index)
    return out.where(vol.notna())


def apply_thresholds(labels: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """Class labels for the forward targets. Unlabelled rows stay NaN."""
    return pd.DataFrame({
        "direction": direction_class(labels["fwd_return_30d"], thresholds),
        "risk": risk_class(labels["fwd_vol_30d"], thresholds),
    })
