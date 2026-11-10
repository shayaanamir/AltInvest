"""Phase 10 report writers that only DESCRIBE the frozen snapshot (no model, no metric on any split).

    python -m ml.nft.data_summary

Writes ml/reports/nft/data_summary.json (step 10.2: rows per collection, date ranges, gaps, the ETH/USD
consistency check, wash-filter counts, snapshot hashes) and ml/reports/nft/liquidity.json (step 10.3: the
D58 liquidity of every collection on the last snapshot date, and how many days each was below N).
"""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean
from ml.gitinfo import git_metadata
from ml.nft import risk_data, snapshot

OUT_DIR = ML_ROOT / "reports" / "nft"
USD_TOLERANCE = 0.05            # D55: abs(floor_usd / floor_usd_source - 1) <= 5%


def usd_consistency(f: pd.DataFrame) -> dict:
    """Our floor_usd (floor_eth x Binance ETH-USD at 00:00) against OpenSea's own usd_price of the same point."""
    both = f[f["floor_usd"].notna() & f["floor_usd_source"].notna()]
    dev = (both["floor_usd"] / both["floor_usd_source"] - 1).abs()
    return {"days_compared": len(both), "days_source_usd_missing_or_zero": int(f["floor_usd_source"].isna().sum()
                                                                               - f["floor_eth"].isna().sum()),
            "median_abs_deviation": float(dev.median()), "max_abs_deviation": float(dev.max()),
            "days_over_tolerance": int((dev > USD_TOLERANCE).sum()), "tolerance": USD_TOLERANCE}


def collection_summary(slug: str, f: pd.DataFrame, raw: pd.DataFrame, kept: pd.DataFrame, tokens: pd.DataFrame,
                       man: dict) -> dict:
    f = f.sort_values("date")
    age = f["floor_age_hours"]
    return {
        "floor_days": len(f), "floor_first_date": f["date"].iloc[0], "floor_last_date": f["date"].iloc[-1],
        "duplicate_days": int(f["date"].duplicated().sum()),
        "gap_days_floor_null": int(f["floor_eth"].isna().sum()), "gap_dates": man["floor_gaps"][slug],
        "floor_age_hours": {"median": float(age.median()), "max": float(age.max())},
        "floor_eth_first_last": [float(f["floor_eth_asof"].iloc[0]), float(f["floor_eth_asof"].iloc[-1])],
        "zero_return_days": int((np.log(f["floor_eth_asof"]).diff() == 0).sum()),
        "usd_consistency": usd_consistency(f),
        "sealed_test_first_date": risk_data.test_start_date(f),
        "sales_raw": len(raw), "sales_after_wash_filter": len(kept),
        "sales_first": raw["date"].min() if len(raw) else None, "sales_last": raw["date"].max() if len(raw) else None,
        "sales_per_month_after_filter": float(len(kept) / max(1, kept["date"].str[:7].nunique())),
        "marketplaces": raw["marketplace"].value_counts().to_dict(),
        "payment_symbols": raw["payment_symbol"].value_counts().to_dict(),
        "wash_filter": man["wash_filter"].get(slug), "dropped_events": man["dropped_events"].get(slug, {}),
        "tokens": len(tokens), "tokens_without_traits": int((tokens["n_traits"] == 0).sum()),
        "supply_reported": man["collections"][slug]["total_supply"],
    }


def data_summary(man: dict) -> dict:
    floor, raw, kept, tokens = (snapshot.load(t) for t in ("floor", "sales_raw", "sales_filtered", "tokens"))
    eth = snapshot.load("eth_usd")
    return {
        "snapshot": man["snapshot"], "snapshot_created_at": man["created_at"],
        "files": {k: {"sha256": v["sha256"], "rows": v["rows"], "bytes": v["bytes"], "range": v["range"]}
                  for k, v in man["files"].items()},
        "eth_usd": {"rows": len(eth), "range": [eth["date"].iloc[0], eth["date"].iloc[-1]],
                    "sources": eth["eth_usd_source"].value_counts().to_dict()},
        "future_dates": int((floor["date"] > man["snapshot"]).sum() + (raw["date"] > man["snapshot"]).sum()),
        "collections": {slug: collection_summary(slug, f, raw[raw["slug"] == slug], kept[kept["slug"] == slug],
                                                 tokens[tokens["slug"] == slug], man)
                        for slug, f in floor.groupby("slug", sort=True)},
    }


def liquidity_report(man: dict) -> dict:
    floor = snapshot.load("floor")
    cols = ["sales_7d", "sales_30d", "volume_7d_eth", "volume_30d_eth", "volume_7d_usd", "volume_30d_usd",
            "liquidity_score", "is_illiquid", "liquidity_label"]
    out = {}
    for slug, f in floor.groupby("slug", sort=True):
        f = f.sort_values("date")
        scored = f[f["liquidity_score"].notna()]
        last = f.iloc[-1]
        out[slug] = {"as_of": last["date"], **{c: last[c] for c in cols},
                     "days_scored": len(scored), "first_scored_date": scored["date"].iloc[0],
                     "days_illiquid": int(scored["is_illiquid"].sum()),
                     "label_days": scored["liquidity_label"].value_counts().to_dict()}
    return {"rule": f"D58: illiquid if sales_7d < {config.NFT_ILLIQUID_MIN_SALES_7D}; liquidity_score = 100 x mean "
                    "pooled percentile of sales_7d, sales_30d, volume_7d_usd, volume_30d_usd among all collections "
                    "on all dates <= D; wash-filtered sales (D57) in the 7 / 30 days ending at D 00:00 UTC",
            "marketplaces_counted": config.NFT_MARKETPLACES_LABEL, "model": "none (rule-based)",
            "collections": out}


def main() -> None:
    manifest_sha = snapshot.require_snapshot()
    man = snapshot.manifest()
    stamp = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata(),
             "snapshot_manifest_sha256": manifest_sha}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, body in (("data_summary.json", data_summary(man)), ("liquidity.json", liquidity_report(man))):
        (OUT_DIR / name).write_text(json.dumps(_clean({**body, "metadata": stamp}), indent=2), encoding="utf-8")
        print(f"wrote {OUT_DIR / name}")


if __name__ == "__main__":
    main()
