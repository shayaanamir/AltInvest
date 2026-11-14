"""Phase 10 step 10.5 report: item-level data checks on the frozen snapshots (no model; nothing about the premium).

    python -m ml.nft.item_summary

Reads sales and floors from the base snapshot and traits and tokens from the D68 item snapshot, re-hashing
both against their manifests. Writes ml/reports/nft/item_data.json: per collection the sales before and after
the wash filter with each rule's count and date ranges, and the checks the plan asks for (no duplicate sales,
every sale has a floor and an ETH-USD price for its date, every sold token has metadata and traits). Monthly
counts of kept sales are given for the pre-test months only (fold sizes for 10.6); the sealed period gets a
single total.
"""

import json
from datetime import datetime, timezone

import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean
from ml.gitinfo import git_metadata
from ml.nft import item_snapshot, risk_data, sales as sl, snapshot

OUT = ML_ROOT / "reports" / "nft" / "item_data.json"


def with_usd(sales: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    """price_usd = price_eth x the frozen ETH-USD of the sale's UTC date (D56, D68)."""
    out = sales.merge(eth[["date", "eth_usd"]], on="date", how="left")
    out["price_usd"] = out["price_eth"] * out["eth_usd"]
    return out


def checks(raw: pd.DataFrame, kept: pd.DataFrame, floor: pd.DataFrame, eth: pd.DataFrame, tokens: pd.DataFrame,
           traits: pd.DataFrame) -> dict:
    """Counts that must be 0 for the data to pass, for one collection (or all)."""
    f = floor[["slug", "date"]].assign(has_floor=True)
    sold = kept[["slug", "token_id"]].drop_duplicates()
    known = sold.merge(tokens[["slug", "token_id", "traits_missing"]], on=["slug", "token_id"], how="left")
    usd = with_usd(raw, eth)
    return {
        "duplicate_sales": int(raw.duplicated(sl.KEY).sum()),
        "sales_without_floor_for_their_date": int(raw.merge(f, on=["slug", "date"], how="left")["has_floor"].isna().sum()),
        "sales_without_eth_usd_for_their_date": int(usd["price_usd"].isna().sum()),
        "sales_with_empty_buyer_or_seller": int(((raw["buyer"] == "") | (raw["seller"] == "")).sum()),
        "sold_tokens_without_metadata": int(known["traits_missing"].isna().sum()),
        "sold_tokens_without_traits": int(known["traits_missing"].fillna(False).astype(bool).sum()),
        "duplicate_trait_rows": int(traits.duplicated(["slug", "token_id", "trait_type"]).sum()),
    }


def collection(slug: str, raw, kept, floor, eth, tokens, traits, man: dict, test_start: str) -> dict:
    pre = kept[kept["date"] < test_start]
    months = pre["date"].str[:7].value_counts().sort_index()
    first_sale = pre.sort_values("timestamp").groupby("token_id").cumcount()
    tk = tokens[tokens["slug"] == slug]
    return {
        "sales_before_filter": len(raw), "removed_by_rule": {r: man["wash_filter"][slug][r] for r in sl.RULES},
        "sales_after_filter": len(kept), "date_range_before": [raw["date"].min(), raw["date"].max()],
        "date_range_after": [kept["date"].min(), kept["date"].max()],
        "dropped_events_before_parsing": man["dropped_events"].get(slug, {}),
        "marketplaces_after_filter": kept["marketplace"].value_counts().to_dict(),
        "usd_volume_after_filter": float(with_usd(kept, eth)["price_usd"].sum()),
        "pre_test_kept_sales": len(pre), "pre_test_monthly_kept_sales": months.to_dict(),
        "pre_test_min_month": int(months.min()), "sealed_period_kept_sales_total": int((kept["date"] >= test_start).sum()),
        "pre_test_share_with_an_earlier_sale_of_the_same_token": float((first_sale > 0).mean()),
        "tokens": len(tk), "supply_reported": man["collections"][slug]["total_supply"],
        "tokens_traits_missing": int(tk["traits_missing"].sum()),
        "trait_categories": int(traits[traits["slug"] == slug]["trait_type"].nunique()),
        "trait_values": int(traits[traits["slug"] == slug][["trait_type", "value"]].drop_duplicates().shape[0]),
        "checks": checks(raw, kept, floor, eth, tk, traits[traits["slug"] == slug]),
    }


def build() -> dict:
    base_sha = snapshot.require_snapshot("floor", "eth_usd", "sales_raw", "sales_filtered")
    item_sha = item_snapshot.require_item_snapshot()
    man = snapshot.manifest()
    raw, kept, floor, eth = (snapshot.load(t) for t in ("sales_raw", "sales_filtered", "floor", "eth_usd"))
    tokens = snapshot.load("tokens", config.NFT_ITEM_SNAPSHOT)
    traits = snapshot.load("traits", config.NFT_ITEM_SNAPSHOT)
    test_start = min(risk_data.test_start_date(g) for _, g in floor.groupby("slug"))
    cols = {s: collection(s, raw[raw["slug"] == s], kept[kept["slug"] == s], floor[floor["slug"] == s], eth,
                          tokens, traits, man, test_start) for s in sorted(raw["slug"].unique())}
    all_checks = checks(raw, kept, floor, eth, tokens, traits)
    return {"collections": cols, "checks_all": all_checks, "all_checks_pass": not any(all_checks.values()),
            "sealed_test_start": test_start,
            "metadata": {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata(),
                         "snapshot": config.NFT_SNAPSHOT_DATE, "snapshot_manifest_sha256": base_sha,
                         "item_snapshot": config.NFT_ITEM_SNAPSHOT, "item_snapshot_manifest_sha256": item_sha}}


def main() -> None:
    report = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(_clean(report), indent=2), encoding="utf-8")
    print(f"wrote {OUT}; all checks pass: {report['all_checks_pass']} {report['checks_all']}")


if __name__ == "__main__":
    main()
