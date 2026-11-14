"""Frozen NFT evaluation snapshot (D62, plan rule 4).

    python -m ml.nft.snapshot --date 2026-11-10        (writes ml/data/nft/snapshots/<date>/, once)
    python -m ml.nft.snapshot --verify

Parquet tables built by ml.nft.build from the live directory, plus manifest.json with each file's sha256,
row count and date range, the wash-filter and dropped-event counts, the floor gaps and the git commit.
Snapshot files are never rewritten: freezing refuses an existing directory. Every NFT report writer calls
require_snapshot(), which re-hashes every file against the manifest and returns the manifest's own sha256
to record in the report. Evaluation reads NFT data only through load().
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ml import config
from ml.gitinfo import git_metadata
from ml.nft import build, floor as fl, sales as sl, store

TABLES = ("floor", "floor_points", "eth_usd", "sales_raw", "sales_filtered", "traits", "tokens")
MANIFEST = "manifest.json"


def snapshot_dir(date: str | None = None) -> Path:
    return config.NFT_SNAPSHOT_ROOT / (date or config.NFT_SNAPSHOT_DATE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _range(df: pd.DataFrame) -> list | None:
    for col in ("date", "timestamp", "time"):
        if col in df.columns and len(df):
            lo, hi = df[col].min(), df[col].max()
            if col != "date":
                lo, hi = (pd.Timestamp(float(x), unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
                          for x in (lo, hi))
            return [lo, hi]
    return None


def tables_for_snapshot(live: Path, date: str) -> tuple[dict, dict]:
    """(tables, extra manifest facts) for a snapshot whose last floor date is `date`."""
    built = build.build(live, last_day=date)
    marked = built["sales_marked"]
    raw = marked[sl.SALE_COLUMNS]
    tables = {"floor": built["floor"], "floor_points": built["floor_points"], "eth_usd": built["eth_usd"],
              "sales_raw": raw, "sales_filtered": marked[marked["wash_rule"] == ""].reset_index(drop=True),
              "traits": built["traits"], "tokens": built["tokens"]}
    dropped = store.read_csv(live / "sales_dropped.csv") if (live / "sales_dropped.csv").exists() else None
    facts = {"last_floor_date": date,
             "wash_filter": sl.removal_counts(marked),
             "dropped_events": ({} if dropped is None else
                                {s: g["reason"].value_counts().to_dict() for s, g in dropped.groupby("slug")}),
             "floor_gaps": {s: fl.gaps(g) for s, g in built["floor"].groupby("slug")},
             "collections": json.loads((live / "collections.json").read_text(encoding="utf-8"))}
    return tables, facts


def freeze(date: str, live: Path | None = None) -> Path:
    out = snapshot_dir(date)
    if out.exists():
        sys.exit(f"snapshot {out} already exists; snapshot files are never rewritten (D62)")
    git = git_metadata()                       # before any snapshot file exists, or they make the tree look dirty
    tables, facts = tables_for_snapshot(Path(live or config.ML_NFT_DIR), date)
    out.mkdir(parents=True)
    files = {}
    for name in TABLES:
        path = out / f"{name}.parquet"
        tables[name].to_parquet(path, index=False, compression="zstd")
        files[path.name] = {"sha256": sha256(path), "rows": len(tables[name]), "bytes": path.stat().st_size,
                            "range": _range(tables[name]), "columns": list(tables[name].columns)}
    manifest = {"snapshot": date, "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                **git, "sources": "OpenSea API v2 (floor, sales), Alchemy NFT API v3 (traits), "
                "Binance ETHUSDT daily bars (D54)", "files": files, **facts}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return out


def manifest(date: str | None = None) -> dict:
    return json.loads((snapshot_dir(date) / MANIFEST).read_text(encoding="utf-8"))


def mismatches(date: str | None = None, tables: tuple = ()) -> list[str]:
    """Files whose current sha256 differs from the manifest, or that are missing. `tables` limits the check
    to those tables (default: every file in the manifest)."""
    d = snapshot_dir(date)
    if not (d / MANIFEST).exists():
        return [f"{d / MANIFEST} is missing"]
    wanted = {f"{t}.parquet" for t in tables}
    return [name for name, meta in manifest(date)["files"].items()
            if (not wanted or name in wanted) and (not (d / name).exists() or sha256(d / name) != meta["sha256"])]


def require_snapshot(*tables: str) -> str:
    """Exit 1 unless the snapshot files of `tables` (default: all) match the manifest. Returns the manifest's
    sha256 (D62, D64). The item-level files are not tracked in git, so a report writer names what it reads."""
    bad = mismatches(tables=tables)
    if bad:
        sys.exit(f"refusing to evaluate: NFT snapshot {snapshot_dir()} does not match its manifest (D62): {bad}")
    return sha256(snapshot_dir() / MANIFEST)


def load(name: str, date: str | None = None) -> pd.DataFrame:
    """One snapshot table. The only way evaluation code reads NFT data. `date` selects another frozen snapshot
    directory (the D68 item snapshot)."""
    return pd.read_parquet(snapshot_dir(date) / f"{name}.parquet")


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify the NFT evaluation snapshot")
    parser.add_argument("--date")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        bad = mismatches(args.date)
        print(f"{snapshot_dir(args.date)}: {'OK, all hashes match' if not bad else f'MISMATCH {bad}'}")
        sys.exit(1 if bad else 0)
    if not args.date:
        parser.error("--date is required to freeze")
    out = freeze(args.date)
    print(f"wrote {out}\n{json.dumps({k: (v['rows'], v['sha256'][:12]) for k, v in manifest(args.date)['files'].items()})}")


if __name__ == "__main__":
    main()
