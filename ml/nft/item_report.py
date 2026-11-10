"""Phase 10 step 10.5b report on the v2 item snapshot (D66, D70, D71, D72). No model; nothing about the premium.

    python -m ml.nft.item_report               writes ml/reports/nft/item_data_v2.json
    python -m ml.nft.item_report --d68-check    reads ~200 tokens' traits from OpenSea, writes d68_check.json

Every statistic is computed on DEVELOPMENT dates only (before T - 7 days, D71); for the sealed rows only row
counts are reported (they come from the v2 manifest).
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean
from ml.gitinfo import git_metadata
from ml.nft import item_data as idt, item_snapshot, snapshot, traits as tr

OUT = ML_ROOT / "reports" / "nft" / "item_data_v2.json"
D68_OUT = ML_ROOT / "reports" / "nft" / "d68_check.json"
D68_SAMPLE = 200


def _runs(flags: np.ndarray) -> int:
    """Longest run of consecutive True values."""
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def floor_gaps(floor: pd.DataFrame, points: pd.DataFrame, before: str) -> dict:
    """Daily series (dates before `before`): days with no new floor point in the 24 h before midnight
    (forward-filled), the longest run of such days, and the longest gap between consecutive points."""
    out = {}
    for slug, g in floor[floor["date"] < before].groupby("slug"):
        p = points[(points["slug"] == slug)].sort_values("time")
        p = p[p["time"] < pd.Timestamp(before, tz="UTC").timestamp()]
        ff = (g.sort_values("date")["floor_age_hours"] > 24).to_numpy()
        out[slug] = {"days": len(g), "forward_filled_days": int(ff.sum()), "longest_forward_filled_run_days": _runs(ff),
                     "longest_point_gap_days": float(np.diff(p["time"].to_numpy()).max() / 86400),
                     "days_with_point_older_than_3_days": int((g["floor_age_hours"] > 72).sum())}
    return out


def sale_join_gaps(dev: pd.DataFrame) -> dict:
    return {slug: {"sales": len(g), "floor_point_older_than_24h": int((g["floor_point_age_hours"] > 24).sum()),
                   "floor_point_older_than_3_days": int((g["floor_point_age_hours"] > 72).sum()),
                   "max_floor_point_age_days": float(g["floor_point_age_hours"].max() / 24)}
            for slug, g in dev.groupby("slug")}


def floor_changes(dev: pd.DataFrame, floor: pd.DataFrame) -> dict:
    """How many dev sales got a different floor than the old same-day join (D57 R3 used floor_eth_model)."""
    m = dev.merge(floor[["slug", "date", "floor_eth_asof", "floor_eth_model"]], on=["slug", "date"], how="left")
    out = {}
    for slug, g in m.groupby("slug"):
        out[slug] = {"sales": len(g),
                     "changed_vs_same_day_asof": int((~np.isclose(g["floor_point_eth"], g["floor_eth_asof"])).sum()),
                     "changed_vs_same_day_guarded": int((~np.isclose(g["floor_point_eth"], g["floor_eth_model"])).sum())}
    return out


def d66_sales_check(floor: pd.DataFrame, clean_dev: pd.DataFrame, before: str) -> dict:
    """D72, as fixed by the user before it was run."""
    days = floor[(floor["date"] < before) & ~np.isclose(floor["floor_eth_model"], floor["floor_eth_asof"])]
    per, examples = {}, []
    for _, d in days.iterrows():
        sales = clean_dev[(clean_dev["slug"] == d["slug"]) & (clean_dev["date"] == d["date"])]
        rec = per.setdefault(d["slug"], {"guarded_days": 0, "no_evidence": 0, "supports_raw": 0, "supports_guarded": 0})
        rec["guarded_days"] += 1
        if sales.empty:
            rec["no_evidence"] += 1
            verdict, p_min = "no evidence", None
        else:
            p_min = float(sales["price_eth"].min())
            raw, guarded = float(d["floor_eth_asof"]), float(d["floor_eth_model"])
            verdict = "supports raw" if abs(np.log(p_min / raw)) < abs(np.log(p_min / guarded)) else "supports guarded"
            rec["supports_raw" if verdict == "supports raw" else "supports_guarded"] += 1
        examples.append({"slug": d["slug"], "date": d["date"], "raw": float(d["floor_eth_asof"]),
                         "guarded": float(d["floor_eth_model"]), "clean_sales": len(sales), "p_min": p_min,
                         "verdict": verdict})
    for slug in sorted(floor["slug"].unique()):
        per.setdefault(slug, {"guarded_days": 0, "no_evidence": 0, "supports_raw": 0, "supports_guarded": 0})
    raw_n = sum(r["supports_raw"] for r in per.values())
    ev = raw_n + sum(r["supports_guarded"] for r in per.values())
    withdraw = ev > 0 and raw_n > ev / 3
    return {"rule": "D72", "per_collection": per, "evidence_days": ev, "supports_raw": raw_n,
            "share_supporting_raw": raw_n / ev if ev else None, "threshold": "more than 1/3 of evidence days",
            "ewma_approval_withdrawn": bool(withdraw), "d66_stands": not withdraw, "days": examples}


def build() -> dict:
    t = config.NFT_FV_SEALED_START
    before = idt.embargo_start(t)
    v2_sha = idt.require_v2()
    base_sha = snapshot.require_snapshot("floor", "floor_points")
    man = snapshot.manifest(config.NFT_ITEM_SNAPSHOT_V2)
    floor, points = snapshot.load("floor"), snapshot.load("floor_points")
    sales = snapshot.load("sales", config.NFT_ITEM_SNAPSHOT_V2)
    dev_all = sales[sales["date"] < before]                       # dev dates, flagged rows included
    dev = dev_all[dev_all["clean"]]
    return {
        "sealed_start_T": t, "embargo": man["embargo"], "clean_rows_by_split": man["clean_rows_by_split"],
        "cleaning_counts_all_dates": man["cleaning_counts"], "id_like_categories": man["id_like_categories"],
        "floor_changes_dev": floor_changes(dev_all, floor),
        "gaps_daily_series_dev": floor_gaps(floor, points, before), "gaps_sale_to_floor_joins_dev": sale_join_gaps(dev),
        "sale_type_dev_clean": {s: g["sale_type"].value_counts().to_dict() for s, g in dev.groupby("slug")},
        "d66_sales_check": d66_sales_check(floor, dev, before),
        "metadata": {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata(),
                     "item_snapshot_v2_manifest_sha256": v2_sha, "snapshot_manifest_sha256": base_sha,
                     "scope": f"statistics on dates before {before} only; sealed rows: counts only (D71)"},
    }


def d68_check(client=None) -> dict:
    """D70: on a fixed sample of tokens Alchemy read with traits, the share whose OpenSea trait set differs."""
    from ml.nft.opensea import Client
    client = client or Client()
    item_snapshot.require_item_snapshot()
    base = snapshot.load("tokens")
    traits = snapshot.load("traits")
    meta = json.loads((config.ML_NFT_DIR / "collections.json").read_text(encoding="utf-8"))
    sample = base[base["n_traits"] > 0].sample(D68_SAMPLE, random_state=0)
    rows = []
    for _, r in sample.iterrows():
        nft = client.nft(meta[r["slug"]]["contract"], r["token_id"])
        _, os_rows = tr.parse_token(tr.from_opensea(nft), r["slug"]) if nft else (None, [])
        a = {(x.trait_type, x.value) for x in traits[(traits["slug"] == r["slug"]) &
                                                       (traits["token_id"] == r["token_id"])].itertuples()}
        o = {(x["trait_type"], x["value"]) for x in os_rows}
        rows.append({"slug": r["slug"], "token_id": r["token_id"], "answered": nft is not None, "same": a == o,
                     "alchemy_only": sorted(map(list, a - o)), "opensea_only": sorted(map(list, o - a))})
    answered = [x for x in rows if x["answered"]]
    pairs = sum(len(x["alchemy_only"]) + len(x["opensea_only"]) for x in answered)
    return {"sample": len(rows), "answered": len(answered),
            "tokens_disagreeing": sum(not x["same"] for x in answered),
            "token_disagreement_rate": sum(not x["same"] for x in answered) / max(1, len(answered)),
            "differing_trait_entries": pairs, "examples": [x for x in answered if not x["same"]][:10],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata()}


def main() -> None:
    parser = argparse.ArgumentParser(description="10.5b item data report")
    parser.add_argument("--d68-check", action="store_true")
    args = parser.parse_args()
    out, body = (D68_OUT, d68_check()) if args.d68_check else (OUT, build())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_clean(body), indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
