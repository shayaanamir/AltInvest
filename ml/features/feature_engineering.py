"""
feature_engineering.py
─────────────────────────────────────────────────────────────────────────────
Computes all ML-ready features from the raw price DataFrame.

Input schema (matches Person A's MongoDB 'prices' collection exactly):
    asset     : str    — e.g. "btc", "eth", or "sol"
    price     : float  — asset price in USD
    volume    : float  — trading volume (asset units)
    timestamp : str    — ISO-8601 UTC  "2024-01-01T00:00:00Z"

Features computed
─────────────────
  Returns
    return_1h   — 1-hour log return
    return_1d   — 24-hour (1-day) log return
    return_7d   — 168-hour (7-day) log return
    return_30d  — 720-hour (30-day) log return

  Rolling Volatility  (std of log returns over window)
    volatility_14d  — 336-hour (14-day) rolling std of 1h log returns

  Moving Averages  (rolling mean of price)
    ma_7d   — 168-hour simple moving average
    ma_30d  — 720-hour simple moving average

  MA Crossover Signal
    ma_cross  — 1 if price > ma_7d > ma_30d (bullish), -1 if inverse, else 0

  Volume
    volume_change_pct — % change in volume vs. previous hour

Public API
──────────
    build_features(df)              -> pd.DataFrame   (main entry point)
    load_raw_csv(asset, data_dir)   -> pd.DataFrame   (convenience loader)
    run_pipeline(asset, data_dir)   -> pd.DataFrame   (load + build + save)

Usage
─────
    # From training script
    from features.feature_engineering import build_features, load_raw_csv
    raw = load_raw_csv("btc")
    features_df = build_features(raw)

    # From API (single-asset, in-memory)
    from features.feature_engineering import build_features
    features_df = build_features(raw_df)

    # Full CLI pipeline
    python -m features.feature_engineering --asset btc

Author : ML Engineer (Person C) — dev-shail branch
"""

import os
import sys
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("feature_engineering")

# ─── Window constants (all in HOURS — data is hourly) ─────────────────────────
HOURS_PER_DAY = 24

W_1H  = 1                       # 1 hour
W_1D  = 1  * HOURS_PER_DAY      # 24
W_7D  = 7  * HOURS_PER_DAY      # 168
W_14D = 14 * HOURS_PER_DAY      # 336
W_30D = 30 * HOURS_PER_DAY      # 720

# ─── Default filesystem paths ─────────────────────────────────────────────────
_ML_ROOT   = Path(__file__).resolve().parent.parent   # …/ml/
RAW_DIR    = _ML_ROOT / "data" / "raw"
PROC_DIR   = _ML_ROOT / "data" / "processed"


# ══════════════════════════════════════════════════════════════════════════════
#  Core feature builders  (each takes a *sorted* single-asset DataFrame)
# ══════════════════════════════════════════════════════════════════════════════

def _add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute log returns over multiple horizons.

    Log-return formula:  r(t, n) = ln(price_t / price_{t-n})

    Advantages over simple % returns:
      - Symmetric around zero
      - Additive across time horizons (r_7d = sum of 7 r_1d)
      - Better behaved statistically for ML models
    """
    price = df["price"]

    df["return_1h"]  = np.log(price / price.shift(W_1H))
    df["return_1d"]  = np.log(price / price.shift(W_1D))
    df["return_7d"]  = np.log(price / price.shift(W_7D))
    df["return_30d"] = np.log(price / price.shift(W_30D))

    return df


def _add_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling 14-day realised volatility = rolling std of 1-hour log returns.

    Annualised formula (for reference, not applied here):
        vol_annual = vol_14d * sqrt(365 * 24)

    min_periods=W_14D ensures no partial windows sneak through before dropna().
    """
    df["volatility_14d"] = (
        df["return_1h"]
        .rolling(window=W_14D, min_periods=W_14D)
        .std()
    )
    return df


def _add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple Moving Averages of price over 7-day and 30-day windows.

    min_periods set to full window — consistent with Prophet's expectation
    of a clean, non-partial feature series.
    """
    df["ma_7d"]  = df["price"].rolling(window=W_7D,  min_periods=W_7D).mean()
    df["ma_30d"] = df["price"].rolling(window=W_30D, min_periods=W_30D).mean()

    # MA Crossover signal: compact trend indicator
    #   +1 → price above both MAs, short-MA above long-MA  (bullish)
    #   -1 → price below both MAs, short-MA below long-MA  (bearish)
    #    0 → mixed / indeterminate
    conditions = [
        (df["price"] > df["ma_7d"]) & (df["ma_7d"] > df["ma_30d"]),
        (df["price"] < df["ma_7d"]) & (df["ma_7d"] < df["ma_30d"]),
    ]
    choices = [1, -1]
    df["ma_cross"] = np.select(conditions, choices, default=0)

    return df


def _add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volume change % vs. previous hour.

    volume_change_pct = (volume_t - volume_{t-1}) / volume_{t-1} * 100

    Uses simple % (not log) because volume spikes are directionally meaningful
    and don't require the symmetry property that log-returns provide.
    """
    df["volume_change_pct"] = df["volume"].pct_change(periods=1) * 100
    return df


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point.  Accepts a raw price DataFrame (any asset) and returns
    a feature-rich DataFrame with NO NaN rows.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: asset, price, volume, timestamp
        Can contain multiple assets — each is processed independently.

    Returns
    -------
    pd.DataFrame
        Original columns + all feature columns.
        NaN rows dropped (result of rolling window warm-up period).
        Sorted by asset, then timestamp ascending.
        Index reset to 0-based integer.

    Raises
    ------
    ValueError  — if required columns are missing or DataFrame is empty.
    """
    _validate_input(df)

    log.info(
        "Building features for %d assets, %d rows total ...",
        df["asset"].nunique(), len(df),
    )

    processed_chunks = []

    for asset, group in df.groupby("asset", sort=True):
        log.info("  Processing asset: %s  (%d rows)", asset, len(group))

        chunk = group.copy()

        # 1. Parse & sort by timestamp (critical for rolling windows)
        chunk["timestamp"] = pd.to_datetime(chunk["timestamp"], utc=True)
        chunk = chunk.sort_values("timestamp").reset_index(drop=True)

        # 2. Apply feature builders
        chunk = _add_returns(chunk)
        chunk = _add_volatility(chunk)
        chunk = _add_moving_averages(chunk)
        chunk = _add_volume_features(chunk)

        # 3. Drop NaN rows (rolling window warm-up) — largest window governs
        rows_before = len(chunk)
        chunk = chunk.dropna().reset_index(drop=True)
        rows_dropped = rows_before - len(chunk)

        log.info(
            "  [%s] Dropped %d warm-up rows (30d window) -> %d clean rows remain",
            asset.upper(), rows_dropped, len(chunk),
        )

        processed_chunks.append(chunk)

    result = pd.concat(processed_chunks, ignore_index=True)

    # 4. Final column order: metadata | price | volume | features
    ordered_cols = _get_column_order(result)
    result = result[ordered_cols]

    log.info(
        "Feature engineering complete. Output: %d rows x %d columns",
        len(result), len(result.columns),
    )
    return result


def load_raw_csv(asset: str, data_dir: Path = RAW_DIR) -> pd.DataFrame:
    """
    Load a raw price CSV from ml/data/raw/<asset>_prices.csv.

    This is the ONLY place that knows about the CSV source.
    When Person A's MongoDB is ready, swap this function with a Mongo reader
    — build_features() and everything downstream stays unchanged.

    Parameters
    ----------
    asset    : "btc", "eth", or "sol" (case-insensitive)
    data_dir : override for testing or CI; defaults to ml/data/raw/

    Returns
    -------
    pd.DataFrame  with columns: asset, price, volume, timestamp
    """
    asset = asset.lower()
    filepath = Path(data_dir) / f"{asset}_prices.csv"

    if not filepath.exists():
        raise FileNotFoundError(
            f"Raw data not found: {filepath}\n"
            "  -> Run ml/data/generate_mock_data.py first, or check Person A's data."
        )

    df = pd.read_csv(filepath)
    log.info("Loaded %s: %d rows from %s", asset.upper(), len(df), filepath)
    return df


def run_pipeline(
    asset: str,
    data_dir: Path = RAW_DIR,
    output_dir: Path = PROC_DIR,
    save: bool = True,
) -> pd.DataFrame:
    """
    Convenience function: load raw -> build features -> optionally save.

    Parameters
    ----------
    asset      : "btc", "eth", or "sol"
    data_dir   : directory of raw CSVs
    output_dir : directory to write processed CSV
    save       : if True, write to output_dir/<asset>_features.csv

    Returns
    -------
    pd.DataFrame  — processed feature DataFrame
    """
    raw = load_raw_csv(asset, data_dir)
    features = build_features(raw)

    if save:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{asset.lower()}_features.csv"
        features.to_csv(out_path, index=False)
        size_kb = out_path.stat().st_size / 1024
        log.info("[SAVED] %s -> %s  (%.1f KB)", asset.upper(), out_path, size_kb)

    return features


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

_REQUIRED_COLS = {"asset", "price", "volume", "timestamp"}

_FEATURE_COLS = [
    "return_1h", "return_1d", "return_7d", "return_30d",
    "volatility_14d",
    "ma_7d", "ma_30d", "ma_cross",
    "volume_change_pct",
]


def _validate_input(df: pd.DataFrame) -> None:
    """Raise early with a clear message if the DataFrame doesn't meet contract."""
    if df is None or df.empty:
        raise ValueError("Input DataFrame is None or empty.")

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input DataFrame is missing required columns: {missing}\n"
            f"  Expected: {_REQUIRED_COLS}\n"
            f"  Got:      {set(df.columns)}"
        )

    if df["price"].le(0).any():
        raise ValueError("Input contains non-positive prices — check raw data.")


def _get_column_order(df: pd.DataFrame) -> list:
    """Return a deterministic column order: metadata + raw + features."""
    base = ["asset", "timestamp", "price", "volume"]
    features = [c for c in _FEATURE_COLS if c in df.columns]
    extras = [c for c in df.columns if c not in base + features]
    return base + features + extras


def get_feature_names() -> list:
    """
    Return the list of feature column names produced by build_features().
    Useful for model training scripts to select only feature columns.

    Example
    -------
        from features.feature_engineering import get_feature_names
        X = features_df[get_feature_names()]
    """
    return _FEATURE_COLS.copy()


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  —  python -m features.feature_engineering --asset btc
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AltInvest Feature Engineering Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m features.feature_engineering --asset btc\n"
            "  python -m features.feature_engineering --asset eth\n"
            "  python -m features.feature_engineering --asset sol\n"
            "  python -m features.feature_engineering --asset btc --no-save\n"
        ),
    )
    parser.add_argument(
        "--asset", choices=["btc", "eth", "sol"], required=True,
        help="Asset to process (btc, eth, or sol)"
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Do not save processed CSV (dry-run mode)"
    )
    return parser.parse_args()


def _print_summary(df: pd.DataFrame, asset: str) -> None:
    """Print a human-readable feature summary to stdout."""
    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  Feature Summary — {asset.upper()}")
    print(sep)
    print(f"  Rows        : {len(df):,}")
    print(f"  Columns     : {list(df.columns)}")
    print(f"  Date range  : {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"\n  Price stats:")
    print(f"    min  : ${df['price'].min():>12,.2f}")
    print(f"    max  : ${df['price'].max():>12,.2f}")
    print(f"    mean : ${df['price'].mean():>12,.2f}")
    print(f"\n  Sample feature values (last row):")
    last = df.iloc[-1]
    for col in get_feature_names():
        print(f"    {col:<22} : {last[col]:>12.6f}")
    print(sep)


if __name__ == "__main__":
    args = _parse_args()

    features_df = run_pipeline(
        asset=args.asset,
        save=not args.no_save,
    )

    _print_summary(features_df, args.asset)
