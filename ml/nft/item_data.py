"""Fair-value item data (D70, D71): the frozen v2 item snapshot and its ONLY loaders.

    python -m ml.nft.item_data --freeze        (writes ml/data/nft/snapshots/<NFT_ITEM_SNAPSHOT_V2>/, once)
    python -m ml.nft.item_data --verify

v2 = base snapshot sales (sales_raw) cleaned by ml.nft.item_clean with the floor point strictly before each sale,
plus the D68 traits with ID-like categories marked, and rarity recomputed without them (known traits only).
Sealed cutoff T (D71) is config.NFT_FV_SEALED_START; freezing refuses if the data gives another T.
  load_dev()      clean sales dated before T - 7 days (the only loader for development, tested)
  load_sealed()   clean sales dated on or after T, ONLY for step 10.8 (refuses otherwise)
The embargo [T - 7, T) is in neither.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import pandas as pd

from ml import config
from ml.gitinfo import git_metadata
from ml.nft import item_clean as ic, item_snapshot, snapshot, traits as tr

EMBARGO_DAYS = 7
SEALED_SHARE = 0.20


def sealed_cutoff(dates: pd.Series, share: float = SEALED_SHARE) -> str:
    """D71: the first day of the latest month such that dates on or after it are at least `share` of all."""
    months = sorted(dates.str[:7].unique(), reverse=True)
    n = len(dates)
    for m in months:
        start = f"{m}-01"
        if (dates >= start).sum() >= share * n:
            return start
    raise ValueError("no month reaches the sealed share")


def embargo_start(t: str) -> str:
    return (pd.Timestamp(t) - pd.Timedelta(days=EMBARGO_DAYS)).strftime("%Y-%m-%d")


def split(sales: pd.DataFrame, t: str) -> dict[str, pd.DataFrame]:
    """{dev, embargo, sealed} by sale date: dev < T - 7 <= embargo < T <= sealed."""
    e = embargo_start(t)
    return {"dev": sales[sales["date"] < e], "embargo": sales[(sales["date"] >= e) & (sales["date"] < t)],
            "sealed": sales[sales["date"] >= t]}


def tables_v2() -> tuple[dict, dict]:
    """(tables, facts) for the v2 item snapshot, from the base and D68 item snapshots."""
    snapshot.require_snapshot("sales_raw", "floor_points", "eth_usd")
    item_snapshot.require_item_snapshot()
    sales, counts = ic.clean(snapshot.load("sales_raw"), snapshot.load("floor_points"))
    tokens = snapshot.load("tokens", config.NFT_ITEM_SNAPSHOT)
    traits = snapshot.load("traits", config.NFT_ITEM_SNAPSHOT)
    id_like = ic.id_like_categories(tokens, traits)
    traits = traits.assign(id_like=[c in id_like.get(s, []) for s, c in zip(traits["slug"], traits["trait_type"])])
    base_tokens = tokens[tr.TOKEN_COLUMNS + ["traits_missing"]]
    tokens = base_tokens.merge(tr.rarity_all(base_tokens, traits[~traits["id_like"]], known_only=True),
                               on=["slug", "token_id"], how="left")
    t = sealed_cutoff(sales.loc[sales["clean"], "date"])
    parts = split(sales[sales["clean"]], t)
    rows = {k: {s: int(n) for s, n in v.groupby("slug").size().items()} | {"all": len(v)} for k, v in parts.items()}
    return ({"sales": sales, "traits": traits, "tokens": tokens},
            {"cleaning_counts": counts, "id_like_categories": id_like, "sealed_start_T": t,
             "embargo": [embargo_start(t), t], "clean_rows_by_split": rows})


def freeze() -> str:
    out = snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V2)
    if out.exists():
        sys.exit(f"snapshot {out} already exists; snapshot files are never rewritten (D62)")
    git = git_metadata()
    tables, facts = tables_v2()
    if facts["sealed_start_T"] != config.NFT_FV_SEALED_START:
        sys.exit(f"the data gives T = {facts['sealed_start_T']}, config says {config.NFT_FV_SEALED_START} (D71)")
    out.mkdir(parents=True)
    files = {}
    for name, df in tables.items():
        path = out / f"{name}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        files[path.name] = {"sha256": snapshot.sha256(path), "rows": len(df), "bytes": path.stat().st_size,
                            "range": [df["date"].min(), df["date"].max()] if "date" in df else None,
                            "columns": list(df.columns)}
    manifest = {"snapshot": config.NFT_ITEM_SNAPSHOT_V2,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git,
                "parents": {config.NFT_SNAPSHOT_DATE: snapshot.sha256(snapshot.snapshot_dir() / snapshot.MANIFEST),
                            config.NFT_ITEM_SNAPSHOT: item_snapshot.require_item_snapshot()},
                "rules": "D70 (cleaning, floor point strictly before the sale, sale_type not a feature, ID-like "
                         "categories), D71 (sealed cutoff)", "not_model_features": list(ic.NOT_FEATURES),
                **facts, "files": files}
    (out / snapshot.MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return str(out)


def require_v2() -> str:
    bad = snapshot.mismatches(config.NFT_ITEM_SNAPSHOT_V2)
    if bad:
        sys.exit(f"refusing to evaluate: NFT item snapshot v2 does not match its manifest (D62, D70): {bad}")
    return snapshot.sha256(snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V2) / snapshot.MANIFEST)


def _load(part: str) -> dict:
    require_v2()
    snapshot.require_snapshot("eth_usd")
    sales = snapshot.load("sales", config.NFT_ITEM_SNAPSHOT_V2)
    sales = split(sales[sales["clean"]], config.NFT_FV_SEALED_START)[part]
    eth = snapshot.load("eth_usd")
    sales = sales.merge(eth[["date", "eth_usd"]], on="date", how="left")
    sales["price_usd"] = sales["price_eth"] * sales["eth_usd"]
    return {"sales": sales.reset_index(drop=True),
            "tokens": snapshot.load("tokens", config.NFT_ITEM_SNAPSHOT_V2),
            "traits": snapshot.load("traits", config.NFT_ITEM_SNAPSHOT_V2),
            "not_model_features": ic.NOT_FEATURES}


def load_dev() -> dict:
    """Development data for 10.6: clean sales dated before T - 7 days, tokens and traits (id_like marked)."""
    out = _load("dev")
    assert out["sales"].empty or out["sales"]["date"].max() < embargo_start(config.NFT_FV_SEALED_START)
    return out


def load_sealed(step: str) -> dict:
    """The sealed fair-value rows (dated >= T). Only the one-time sealed test may call it (plan rule 3)."""
    if step != "10.8":
        raise PermissionError("the sealed fair-value rows are read only in step 10.8 (plan rule 3, D71)")
    return _load("sealed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify the v2 NFT item snapshot (D70, D71)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--dry-run", action="store_true", help="compute T and the counts without writing")
    args = parser.parse_args()
    if args.dry_run:
        _, facts = tables_v2()
        print(json.dumps({k: facts[k] for k in ("sealed_start_T", "embargo", "clean_rows_by_split",
                                                 "id_like_categories")}, indent=1))
    elif args.freeze:
        print(f"wrote {freeze()}")
    else:
        bad = snapshot.mismatches(config.NFT_ITEM_SNAPSHOT_V2)
        print(f"{snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V2)}: {'OK, all hashes match' if not bad else f'MISMATCH {bad}'}")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
