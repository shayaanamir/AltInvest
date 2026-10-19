"""Forward-looking targets and their class thresholds (D3, D9, D19).

Labels look HORIZON_DAYS rows ahead, so the last HORIZON_DAYS rows are NaN.
They live only in memory and reports; they are never written to the raw CSVs.
"""

import numpy as np
import pandas as pd

from ml import config

H = config.HORIZON_DAYS
DIRECTION_CLASSES = ("DOWN", "FLAT", "UP")
RISK_CLASSES = ("low", "medium", "high")


def fwd_return_30d(close: pd.Series) -> pd.Series:
    """ln(close[t+30] / close[t])."""
    return np.log(close.shift(-H) / close)


def fwd_vol_30d(close: pd.Series) -> pd.Series:
    """Std of the daily log returns t+1..t+30 (the 30 returns after t)."""
    r = np.log(close / close.shift(1))
    return r.rolling(H).std().shift(-H)


def build_labels(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"fwd_return_30d": fwd_return_30d(close), "fwd_vol_30d": fwd_vol_30d(close)})


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


def apply_thresholds(labels: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """Class labels. Direction: UP if r > t, DOWN if r < -t, else FLAT.
    Risk: low if vol <= p33, high if vol > p67, else medium. Unlabelled rows stay NaN."""
    ret, vol = labels["fwd_return_30d"], labels["fwd_vol_30d"]
    t = thresholds["direction_flat_abs_return"]
    direction = pd.Series(np.select([ret > t, ret < -t], ["UP", "DOWN"], "FLAT"), index=labels.index)
    risk = pd.Series(
        np.select([vol <= thresholds["risk_low_max_vol"], vol > thresholds["risk_high_min_vol"]],
                  ["low", "high"], "medium"),
        index=labels.index)
    return pd.DataFrame({
        "direction": direction.where(ret.notna()),
        "risk": risk.where(vol.notna()),
    })
