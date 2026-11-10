"""Frozen ITEM snapshot (D68): the base snapshot's traits and tokens with the missing metadata filled.

    python -m ml.nft.item_snapshot --fill       (reads the missing tokens from OpenSea into ML_NFT_DIR)
    python -m ml.nft.item_snapshot --freeze     (writes ml/data/nft/snapshots/<NFT_ITEM_SNAPSHOT>/, once)
    python -m ml.nft.item_snapshot --verify

The base snapshot (config.NFT_SNAPSHOT_DATE) is never changed. The item snapshot holds traits.parquet and
tokens.parquet (with traits_missing and rarity over the tokens with known traits only) and a manifest with
the parent manifest's sha256. Fair value (10.6) reads traits and tokens only from here.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import pandas as pd

from ml import config
from ml.gitinfo import git_metadata
from ml.nft import snapshot, store, traits as tr

FILL_TRAITS, FILL_TOKENS = "traits_fill.csv", "tokens_fill.csv"
TABLES = ("traits", "tokens")


def missing_tokens(tokens: pd.DataFrame) -> pd.DataFrame:
    return tokens.loc[tokens["n_traits"] == 0, ["slug", "token_id"]]


def fill(client=None) -> dict:
    """Reads each base-snapshot token without traits from OpenSea once; writes the fill files. Returns counts."""
    from ml.nft.opensea import Client
    client = client or Client()
    meta = json.loads((config.ML_NFT_DIR / "collections.json").read_text(encoding="utf-8"))
    todo = missing_tokens(snapshot.load("tokens"))
    tokens, rows = [], []
    for _, r in todo.iterrows():
        nft = client.nft(meta[r["slug"]]["contract"], r["token_id"])
        if nft is None:
            continue
        token, trait_rows = tr.parse_token(tr.from_opensea(nft), r["slug"])
        tokens.append(token)
        rows.extend(trait_rows)
    store.write_csv(pd.DataFrame(rows, columns=tr.TRAIT_COLUMNS), config.ML_NFT_DIR / FILL_TRAITS)
    store.write_csv(pd.DataFrame(tokens, columns=tr.TOKEN_COLUMNS), config.ML_NFT_DIR / FILL_TOKENS)
    got = pd.DataFrame(tokens, columns=tr.TOKEN_COLUMNS)
    return {"asked": len(todo), "answered": len(got), "with_traits": int((got["n_traits"] > 0).sum())}


def merge(base_tokens: pd.DataFrame, base_traits: pd.DataFrame, fill_tokens: pd.DataFrame,
          fill_traits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(traits, tokens): base traits plus fill traits of tokens the base had none for; tokens with name, image
    and n_traits updated from the fill, traits_missing, and rarity over known tokens only (D68)."""
    key = ["slug", "token_id"]
    had = base_traits[key].drop_duplicates()
    new = fill_traits.merge(had, on=key, how="left", indicator=True)
    new = new[new["_merge"] == "left_only"].drop(columns="_merge")
    traits = pd.concat([base_traits, new], ignore_index=True).sort_values(key + ["trait_type"]).reset_index(drop=True)
    tokens = base_tokens[tr.TOKEN_COLUMNS].copy()
    upd = fill_tokens[fill_tokens["n_traits"] > 0].set_index(key)
    idx = tokens.set_index(key).index
    hit = idx.isin(upd.index)
    for col in ("name", "image_url", "n_traits"):
        tokens.loc[hit, col] = upd.loc[idx[hit], col].to_numpy()
    tokens["n_traits"] = tokens["n_traits"].astype(int)
    tokens["traits_missing"] = tokens["n_traits"] == 0
    tokens = tokens.merge(tr.rarity_all(tokens, traits, known_only=True), on=key, how="left")
    return traits, tokens


def freeze() -> str:
    out = snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT)
    if out.exists():
        sys.exit(f"snapshot {out} already exists; snapshot files are never rewritten (D62)")
    parent_sha = snapshot.require_snapshot("tokens", "traits")
    git = git_metadata()
    fill_tokens = store.read_csv(config.ML_NFT_DIR / FILL_TOKENS)
    fill_traits = store.read_csv(config.ML_NFT_DIR / FILL_TRAITS)
    base_tokens = snapshot.load("tokens")
    traits, tokens = merge(base_tokens, snapshot.load("traits"), fill_tokens, fill_traits)
    out.mkdir(parents=True)
    files = {}
    for name, df in (("traits", traits), ("tokens", tokens)):
        path = out / f"{name}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        files[path.name] = {"sha256": snapshot.sha256(path), "rows": len(df), "bytes": path.stat().st_size,
                            "range": None, "columns": list(df.columns)}
    before = missing_tokens(base_tokens).groupby("slug").size()
    after = tokens[tokens["traits_missing"]].groupby("slug").size()
    manifest = {"snapshot": config.NFT_ITEM_SNAPSHOT,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git,
                "parent_snapshot": config.NFT_SNAPSHOT_DATE, "parent_manifest_sha256": parent_sha,
                "fill_source": "OpenSea GET /chain/ethereum/contract/{contract}/nfts/{id} (D68)",
                "tokens_without_traits_before": {k: int(v) for k, v in before.items()},
                "tokens_without_traits_after": {k: int(after.get(k, 0)) for k in before.index},
                "rarity": "over tokens with known traits only; traits_missing tokens have null rarity (D68)",
                "files": files}
    (out / snapshot.MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return str(out)


def require_item_snapshot() -> str:
    """Exit 1 unless the item snapshot matches its manifest; returns the manifest's sha256."""
    bad = snapshot.mismatches(config.NFT_ITEM_SNAPSHOT)
    if bad:
        sys.exit(f"refusing to evaluate: NFT item snapshot does not match its manifest (D62, D68): {bad}")
    return snapshot.sha256(snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT) / snapshot.MANIFEST)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill missing item metadata and freeze the item snapshot")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fill", action="store_true")
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.fill:
        print(json.dumps(fill()))
    elif args.freeze:
        print(f"wrote {freeze()}")
    else:
        bad = snapshot.mismatches(config.NFT_ITEM_SNAPSHOT)
        print(f"{snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT)}: {'OK, all hashes match' if not bad else f'MISMATCH {bad}'}")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
