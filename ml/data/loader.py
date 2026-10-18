"""The ONE loader for raw daily bars (docs/DATA.md). Swap the body later for Mongo/live data."""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent / "raw"
COLUMNS = ["asset", "timestamp", "open", "high", "low", "close", "volume"]


def raw_csv_path(asset: str) -> Path:
    return RAW_DIR / f"{asset}_1d.csv"


def fetch_meta_path(asset: str) -> Path:
    return RAW_DIR / f"{asset}_1d.fetch.json"


def load_raw(asset: str) -> pd.DataFrame:
    """Daily bars for one asset, sorted by timestamp (tz-aware UTC). No filling of any kind."""
    df = pd.read_csv(raw_csv_path(asset))
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)
