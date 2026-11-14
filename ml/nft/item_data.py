"""Fair-value item data (D70, D71, D74, D75): the frozen v3 item snapshot and its ONLY loaders.

    python -m ml.nft.item_data --freeze        (writes ml/data/nft/snapshots/<NFT_ITEM_SNAPSHOT_V3>/, once)
    python -m ml.nft.item_data --verify        (v2 and v3)

v3 = base snapshot sales (sales_raw) cleaned by ml.nft.item_clean with the floor point strictly before each sale and
the D74 multi-token rule (transaction payments frozen as tx_payments.parquet), payment_currency (D75), plus the D68
traits with ID-like categories marked and rarity recomputed without them (known traits only). v2 (D70) stays frozen.
Sealed cutoff T (D71) is config.NFT_FV_SEALED_START, computed once on v2 and NOT recomputed for v3 (D75).
  load_dev()      clean sales dated before T - 7 days (the only loader for development, tested)
  load_sealed()   clean sales dated on or after T; was ONLY for step 10.8, refuses every caller since 10.9b
The embargo [T - 7, T) is in neither.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import pandas as pd

from ml import config
from ml.gitinfo import git_metadata
from ml.nft import item_clean as ic, item_snapshot, snapshot, store, traits as tr, tx_payments

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


def _items(tokens: pd.DataFrame, traits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    id_like = ic.id_like_categories(tokens, traits)
    traits = traits.assign(id_like=[c in id_like.get(s, []) for s, c in zip(traits["slug"], traits["trait_type"])])
    base_tokens = tokens[tr.TOKEN_COLUMNS + ["traits_missing"]]
    tokens = base_tokens.merge(tr.rarity_all(base_tokens, traits[~traits["id_like"]], known_only=True),
                               on=["slug", "token_id"], how="left")
    return traits, tokens, id_like


def rows_by_split(sales: pd.DataFrame, t: str) -> dict:
    parts = split(sales[sales["clean"]], t)
    out = {k: {s: int(n) for s, n in v.groupby("slug").size().items()} | {"all": len(v)} for k, v in parts.items()}
    total = sum(out[k]["all"] for k in ("dev", "embargo", "sealed"))
    return {**out, "sealed_share_of_clean": out["sealed"]["all"] / total if total else None}


def payments() -> pd.DataFrame:
    """The D74 transaction payments read by ml.nft.tx_payments; refuses if any multi-token transaction is missing."""
    path = config.ML_NFT_DIR / tx_payments.OUT
    pay = store.read_csv(path) if path.exists() else pd.DataFrame(columns=tx_payments.COLUMNS)
    pay = pay.drop_duplicates("tx", keep="last").copy()
    pay["ok"] = pay["ok"].astype(str).str.lower().isin(("true", "1"))
    need = set(tx_payments.multi_token_txs(snapshot.load("sales_raw")))
    missing = need - set(pay["tx"])
    if missing:
        sys.exit(f"payments missing for {len(missing)} multi-token transactions; run python -m ml.nft.tx_payments")
    return pay[pay["tx"].isin(need)].reset_index(drop=True)


def tables_v3() -> tuple[dict, dict]:
    """(tables, facts) for the v3 item snapshot. T comes from config (not recomputed, D75)."""
    snapshot.require_snapshot("sales_raw", "floor_points", "eth_usd")
    item_snapshot.require_item_snapshot()
    pay = payments()
    sales, counts = ic.clean(snapshot.load("sales_raw"), snapshot.load("floor_points"), pay)
    traits, tokens, id_like = _items(snapshot.load("tokens", config.NFT_ITEM_SNAPSHOT),
                                     snapshot.load("traits", config.NFT_ITEM_SNAPSHOT))
    t = config.NFT_FV_SEALED_START
    return ({"sales": sales, "traits": traits, "tokens": tokens, "tx_payments": pay},
            {"cleaning_counts": counts, "id_like_categories": id_like, "sealed_start_T": t,
             "sealed_start_T_source": "config.NFT_FV_SEALED_START, computed on v2 (D71); not recomputed (D75)",
             "embargo": [embargo_start(t), t], "clean_rows_by_split": rows_by_split(sales, t)})


def freeze() -> str:
    out = snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V3)
    if out.exists():
        sys.exit(f"snapshot {out} already exists; snapshot files are never rewritten (D62)")
    git = git_metadata()
    tables, facts = tables_v3()
    out.mkdir(parents=True)
    files = {}
    for name, df in tables.items():
        path = out / f"{name}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        files[path.name] = {"sha256": snapshot.sha256(path), "rows": len(df), "bytes": path.stat().st_size,
                            "range": [df["date"].min(), df["date"].max()] if "date" in df else None,
                            "columns": list(df.columns)}
    manifest = {"snapshot": config.NFT_ITEM_SNAPSHOT_V3,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git,
                "parents": {config.NFT_SNAPSHOT_DATE: snapshot.sha256(snapshot.snapshot_dir() / snapshot.MANIFEST),
                            config.NFT_ITEM_SNAPSHOT: item_snapshot.require_item_snapshot()},
                "rules": "D70 (cleaning, floor point strictly before the sale, ID-like categories) with C2 replaced by "
                         "D74 (transaction payments), D75 (currency), D71 (sealed cutoff, not recomputed)",
                "not_model_features": list(ic.NOT_FEATURES), **facts, "files": files}
    (out / snapshot.MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return str(out)


def require(version: str = config.NFT_ITEM_SNAPSHOT_V3) -> str:
    bad = snapshot.mismatches(version)
    if bad:
        sys.exit(f"refusing to evaluate: NFT item snapshot {version} does not match its manifest (D62): {bad}")
    return snapshot.sha256(snapshot.snapshot_dir(version) / snapshot.MANIFEST)


def require_v2() -> str:
    return require(config.NFT_ITEM_SNAPSHOT_V2)


def dev_end_timestamp() -> int:
    """Unix seconds of T - 7 days 00:00 UTC (2026-01-25): every development row and floor point is before it."""
    return int(pd.Timestamp(embargo_start(config.NFT_FV_SEALED_START), tz="UTC").timestamp())


def _load(part: str, include_flagged: bool = False) -> dict:
    v = config.NFT_ITEM_SNAPSHOT_V3
    require(v)
    snapshot.require_snapshot("eth_usd")
    sales = snapshot.load("sales", v)
    sales = split(sales if include_flagged else sales[sales["clean"]], config.NFT_FV_SEALED_START)[part]
    eth = snapshot.load("eth_usd")
    sales = sales.merge(eth[["date", "eth_usd"]], on="date", how="left")
    sales["price_usd"] = sales["price_eth"] * sales["eth_usd"]
    return {"sales": sales.reset_index(drop=True), "tokens": snapshot.load("tokens", v),
            "traits": snapshot.load("traits", v), "not_model_features": ic.NOT_FEATURES}


def load_dev(include_flagged: bool = False) -> dict:
    """Development data for 10.6: v3 sales dated before T - 7 days (clean only, or with the W1/W2-flagged rows
    when include_flagged; the fair-value feature history needs them, D76), tokens, traits (id_like marked) and
    the base snapshot's OpenSea floor points with time before T - 7 days 00:00 UTC (later points are dropped
    here, before anything else sees them)."""
    out = _load("dev", include_flagged)
    cut = dev_end_timestamp()
    assert out["sales"].empty or out["sales"]["date"].max() < embargo_start(config.NFT_FV_SEALED_START)
    assert out["sales"].empty or int(out["sales"]["timestamp"].max()) < cut
    snapshot.require_snapshot("floor_points")
    points = snapshot.load("floor_points")
    out["floor_points"] = points[points["time"] < cut].reset_index(drop=True)
    assert out["floor_points"].empty or out["floor_points"]["time"].max() < cut
    return out


def load_history(step: str) -> dict:
    """The as-of feature history for the one-time sealed test (D79): EVERY v3 row after C1-C3 (clean and flagged,
    development, embargo and sealed dates up to the snapshot), all floor points, tokens and traits. Features of a
    sealed sale use only rows strictly before it (fv_features). Only step 10.8 could call it (plan rule 3); that run
    is done (ml/reports/nft/sealed_fair_value.json), so since 10.9b it refuses every caller."""
    raise PermissionError(f"the full item history was read once, in step 10.8 (plan rule 3, D79); the sealed test is "
                          f"spent and the loader refuses every step (asked for {step!r}, 10.9b)")


def load_sealed(step: str) -> dict:
    """The sealed fair-value rows (dated >= T). Only the one-time sealed test could call it (plan rule 3); that run is
    done, so since 10.9b it refuses every caller."""
    raise PermissionError(f"the sealed fair-value rows were for step 10.8 only (plan rule 3, D71); the sealed test is "
                          f"spent and the loader refuses every step (asked for {step!r}, 10.9b)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze or verify the v3 NFT item snapshot (D74, D75)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--dry-run", action="store_true", help="the v3 counts without writing")
    args = parser.parse_args()
    if args.dry_run:
        _, facts = tables_v3()
        print(json.dumps({k: facts[k] for k in ("cleaning_counts", "clean_rows_by_split")}, indent=1))
    elif args.freeze:
        print(f"wrote {freeze()}")
    else:
        bad = {v: snapshot.mismatches(v) for v in (config.NFT_ITEM_SNAPSHOT_V2, config.NFT_ITEM_SNAPSHOT_V3)}
        for v, b in bad.items():
            print(f"{snapshot.snapshot_dir(v)}: {'OK, all hashes match' if not b else f'MISMATCH {b}'}")
        sys.exit(1 if any(bad.values()) else 0)


if __name__ == "__main__":
    main()
