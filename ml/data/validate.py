"""Validate raw daily bars and write the evidence report (docs/DATA.md, D15).

    python -m ml.data.validate --asset btc

Writes ml/reports/data/{asset}_validation.json. Exit code 1 if any check fails.
Real crypto shows heavy tails (excess kurtosis > 1) and volatility clustering (|r| lag-1 autocorr > 0).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml import config
from ml.data.loader import fetch_meta_path, load_raw, raw_csv_path

ML_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ML_ROOT / "reports" / "data"
DAY = pd.Timedelta(days=1)
PRICE_COLS = ["open", "high", "low", "close"]


def _iso(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _rounded(x: float) -> float | None:
    """Round for the report; NaN (too few returns) becomes null so the JSON stays valid."""
    return round(x, 4) if np.isfinite(x) else None


def missing_days(timestamps: pd.Series) -> list[str]:
    """Calendar days between the first and last bar that have no bar."""
    ts = pd.DatetimeIndex(timestamps.drop_duplicates())
    full = pd.date_range(ts.min(), ts.max(), freq="D")
    return [_iso(t) for t in full.difference(ts)]


def duplicate_timestamps(timestamps: pd.Series) -> list[str]:
    return [_iso(t) for t in timestamps[timestamps.duplicated()].unique()]


def daily_log_returns(df: pd.DataFrame) -> pd.Series:
    """ln(close_t / close_{t-1}) only where the previous bar is exactly one day earlier.

    Returns that span a gap are dropped, so a missing day never becomes a fake 2-day return.
    """
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    r = np.log(df["close"] / df["close"].shift(1))
    consecutive = df["timestamp"].diff() == DAY
    return r[consecutive].reset_index(drop=True)


def excess_kurtosis(r: pd.Series) -> float:
    """Sample excess kurtosis (Fisher, bias-adjusted; pandas .kurt()). A normal distribution gives 0."""
    return float(r.kurt())


def abs_return_autocorr(r: pd.Series, lag: int = 1) -> float:
    """Autocorrelation of |r| at `lag`. Positive means volatility clustering."""
    return float(r.abs().autocorr(lag))


def non_positive_rows(df: pd.DataFrame) -> int:
    return int((df[PRICE_COLS] <= 0).any(axis=1).sum())


def ohlc_inconsistent_rows(df: pd.DataFrame) -> int:
    """Rows where high < max(open, close) or low > min(open, close)."""
    hi_bad = df["high"] < df[["open", "close"]].max(axis=1)
    lo_bad = df["low"] > df[["open", "close"]].min(axis=1)
    return int((hi_bad | lo_bad).sum())


def validate(df: pd.DataFrame) -> dict:
    """Validation metrics and pass/fail checks for one asset's daily bars (no I/O)."""
    r = daily_log_returns(df)
    gaps = missing_days(df["timestamp"])
    dups = duplicate_timestamps(df["timestamp"])
    kurt = excess_kurtosis(r)
    acf1 = abs_return_autocorr(r, 1)
    i_min, i_max = df["close"].idxmin(), df["close"].idxmax()
    report = {
        "rows": int(len(df)),
        "first_timestamp": _iso(df["timestamp"].min()),
        "last_timestamp": _iso(df["timestamp"].max()),
        "expected_days": int((df["timestamp"].max() - df["timestamp"].min()) / DAY) + 1,
        "missing_days_count": len(gaps),
        "missing_days": gaps,
        "duplicate_count": len(dups),
        "duplicates": dups,
        "close_min": float(df["close"].min()),
        "close_min_timestamp": _iso(df.loc[i_min, "timestamp"]),
        "close_max": float(df["close"].max()),
        "close_max_timestamp": _iso(df.loc[i_max, "timestamp"]),
        "non_positive_price_rows": non_positive_rows(df),
        "ohlc_inconsistent_rows": ohlc_inconsistent_rows(df),
        "n_returns": int(len(r)),
        "excess_kurtosis": _rounded(kurt),
        "abs_return_lag1_autocorr": _rounded(acf1),
    }
    report["checks"] = {
        "excess_kurtosis_gt_1": bool(np.isfinite(kurt) and kurt > 1),
        "abs_return_lag1_autocorr_gt_0": bool(np.isfinite(acf1) and acf1 > 0),
        "no_non_positive_prices": report["non_positive_price_rows"] == 0,
        "no_duplicates": report["duplicate_count"] == 0,
        "ohlc_consistent": report["ohlc_inconsistent_rows"] == 0,
    }
    report["passed"] = all(report["checks"].values())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate raw daily bars")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    args = parser.parse_args()
    asset = args.asset

    meta_path = fetch_meta_path(asset)
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    report = {
        "asset": asset,
        "symbol": config.ASSET_SYMBOLS[asset],
        "source": meta.get("source"),
        "fetched_at": meta.get("fetched_at"),
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_file": raw_csv_path(asset).relative_to(ML_ROOT.parent).as_posix(),
        **validate(load_raw(asset)),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{asset}_validation.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote {out}")
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
