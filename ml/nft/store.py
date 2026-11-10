"""Table files for NFT data (D62): CSV in the live/serving directory, parquet in a frozen snapshot.

One reader for both, so evaluation (snapshot) and serving (live) share every function above this layer.
Column types are kept simple so both formats round-trip: strings, ints and floats; dates are 'YYYY-MM-DD'
strings; times are unix seconds (UTC).
"""

import os
from pathlib import Path

import pandas as pd

STRING_COLUMNS = ("slug", "token_id", "date", "buyer", "seller", "tx", "protocol_address", "marketplace",
                  "payment_symbol", "wash_rule", "trait_type", "value", "name", "image_url", "floor_source",
                  "eth_usd_source", "reason")
PER_SLUG_TABLES = ("traits", "tokens")          # stored as <table>/<slug>.csv in the live directory


def read_csv(path: Path) -> pd.DataFrame:
    head = pd.read_csv(path, nrows=0).columns
    return pd.read_csv(path, dtype={c: str for c in head if c in STRING_COLUMNS}, keep_default_na=False,
                       na_values={c: [""] for c in head if c not in STRING_COLUMNS})


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Atomic: a reader never sees a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, lineterminator="\n")
    os.replace(tmp, path)


def has_table(directory: Path, name: str) -> bool:
    d = Path(directory)
    return ((d / f"{name}.parquet").exists() or (d / f"{name}.csv").exists()
            or (name in PER_SLUG_TABLES and any((d / name).glob("*.csv"))))


def read_table(directory: Path, name: str) -> pd.DataFrame:
    """<name>.parquet (snapshot), else <name>.csv, else every <name>/<slug>.csv (live traits and tokens)."""
    d = Path(directory)
    if (d / f"{name}.parquet").exists():
        return pd.read_parquet(d / f"{name}.parquet")
    if (d / f"{name}.csv").exists():
        return read_csv(d / f"{name}.csv")
    parts = sorted((d / name).glob("*.csv")) if name in PER_SLUG_TABLES else []
    if not parts:
        raise FileNotFoundError(f"no table '{name}' in {d}")
    return pd.concat([read_csv(p) for p in parts], ignore_index=True)
