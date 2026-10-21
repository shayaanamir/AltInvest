"""The ONE loader for raw daily bars (docs/DATA.md). Swap the body later for Mongo/live data.

Files live in config.ML_RAW_DIR (D40): the evaluation snapshot ml/data/raw unless the ML_RAW_DIR env var is set.
`raw_dir` overrides it for one call (the refresh validates a staged download before it replaces anything).
"""

from pathlib import Path

import pandas as pd

from ml import config

COLUMNS = ["asset", "timestamp", "open", "high", "low", "close", "volume"]


def raw_csv_path(asset: str, raw_dir: Path | None = None) -> Path:
    return Path(raw_dir or config.ML_RAW_DIR) / f"{asset}_1d.csv"


def fetch_meta_path(asset: str, raw_dir: Path | None = None) -> Path:
    return Path(raw_dir or config.ML_RAW_DIR) / f"{asset}_1d.fetch.json"


def load_raw(asset: str, raw_dir: Path | None = None) -> pd.DataFrame:
    """Daily bars for one asset, sorted by timestamp (tz-aware UTC). No filling of any kind."""
    df = pd.read_csv(raw_csv_path(asset, raw_dir))
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)
