"""Phase 10 step 10.8: the ONE-TIME sealed test of the served fair-value configuration (D79), declared before any
sealed access.

    python -m ml.evaluation.run_nft_sealed_fv --dry-run     (development data; mock window = 2025-10 .. 2026-01-24)
    python -m ml.evaluation.run_nft_sealed_fv --sealed      (step 10.8 ONLY: one invocation, logged, output final)

PROTOCOL (D79). Window: sales dated 2026-02-01 to 2026-11-10. Monthly expanding refits, as the walk-forward: for
each month M of the window, train on all clean sales with timestamp < start(M) - 7 days, with W1/W2 of training
rows decided from sales before that cutoff; fit config.NFT_FV_CANDIDATE (fv_pooled_l1_nl15, exactly as declared)
and B0 / B1 / B2 the same way. Features of every sale come from the as-of history (item_data.load_history('10.8'):
all rows, including earlier sealed sales; every feature uses only rows strictly before the sale) through the same
feature code as development. Test rows: the clean sales of month M, with W2 decided from sales up to 2026-11-10.
EVALUATED: the SERVED configuration (config.NFT_FV_SERVE: the model for 6 collections, B2 for lilpudgys).
PASS RULE: the paired 95% CI of MdAPE(best of B0/B1/B2 on the window) - MdAPE(served), moving blocks of 7
calendar dates, 1,000 resamples, seed 0, pooled across collections, excludes 0 above zero (low > 0 and estimate
> 0). OUTCOME: PASS -> keep the serving rule; FAIL -> every collection serves B2. Either way no range is served.
DESCRIPTIVE ONLY (changes nothing): MdAPE by collection, by rarity decile and by month; B2's 80% range coverage.
The --sealed run refuses on a dirty tree or if its report already exists; its stdout is also written to a log.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation import nft_fv_protocol as proto
from ml.models import nft_fair_value as fvm
from ml.nft import fv_features as fv

SEALED = {"first": config.NFT_FV_SEALED_START, "last": "2026-11-10"}          # D71, D79
DRY_RUN = {"first": "2025-10-01", "last": "2026-01-24"}                       # the 10.6 confirmation months
EMBARGO_DAYS = proto.EMBARGO_DAYS
REPORTS = {"sealed": ML_ROOT / "reports" / "nft" / "sealed_fair_value.json",
           "dry_run": ML_ROOT / "reports" / "nft" / "sealed_fair_value_dry_run.json"}
LOG = ML_ROOT / "docs" / "phase10" / "logs" / "10.8_sealed_run.log"
BASELINES = proto.BASELINES
_LINES: list[str] = []


def say(msg: str) -> None:
    """print, and keep the line for the --sealed log."""
    _LINES.append(msg)
    print(msg, flush=True)


def months(window: dict) -> list[dict]:
    """Monthly test windows inside [first, last] (dates inclusive), each with its training cutoff."""
    end = pd.Timestamp(window["last"], tz="UTC") + pd.Timedelta(days=1)
    start, out = pd.Timestamp(window["first"], tz="UTC"), []
    while start < end:
        nxt = min(start + pd.offsets.MonthBegin(1), end)
        out.append({"month": start.strftime("%Y-%m"), "train_end": start - pd.Timedelta(days=EMBARGO_DAYS),
                    "test_start": start, "test_end": nxt})
        start = nxt
    return out


def served_ape(rows: pd.DataFrame, serve: dict) -> np.ndarray:
    """Per-row APE of the served configuration: the model where config says 'model', else B2."""
    use_model = rows["slug"].map(lambda s: serve[s] == "model").to_numpy(bool)
    return np.where(use_model, rows[f"ape:{config.NFT_FV_CANDIDATE}"], rows["ape:B2_decile_90d"])


def decide(rows: pd.DataFrame, serve: dict) -> dict:
    """The D79 pass rule on the window's rows (ape:<name> columns, date, slug)."""
    rows = rows.assign(**{"ape:served": served_ape(rows, serve)})
    md = {n: float(np.median(rows[f"ape:{n}"])) for n in ["served", config.NFT_FV_CANDIDATE, *BASELINES]}
    best = min(BASELINES, key=lambda b: md[b])
    ci = proto.date_block_stat_ci(rows["date"], rows[f"ape:{best}"], rows["ape:served"])
    passed = bool(ci is not None and ci["estimate"] > 0 and ci["low"] > 0)
    n_dates = int(rows["date"].nunique())
    return {"mdape": md, "best_baseline": best, "paired_diff_best_baseline_minus_served": ci, "pass": passed,
            "outcome": ("PASS: keep the serving rule " + json.dumps(serve)) if passed
            else "FAIL: every collection serves B2", "range_served": None, "n_rows": len(rows),
            "n_dates": n_dates, "n_blocks": n_dates / proto.BLOCK_DAYS}


def _by(rows: pd.DataFrame, key: str, names: list) -> dict:
    return {str(k): {"n": len(g), **{n: float(np.median(g[f"ape:{n}"])) for n in names}}
            for k, g in rows.groupby(key)}


def descriptive(rows: pd.DataFrame, serve: dict) -> dict:
    rows = rows.assign(**{"ape:served": served_ape(rows, serve)})
    names = ["served", config.NFT_FV_CANDIDATE, *BASELINES]
    inside = (rows["y"] >= rows["lo:B2_decile_90d"]) & (rows["y"] <= rows["hi:B2_decile_90d"])
    cov = {"pooled": float(inside.mean()), "lower_tail_miss": float((rows["y"] < rows["lo:B2_decile_90d"]).mean()),
           "upper_tail_miss": float((rows["y"] > rows["hi:B2_decile_90d"]).mean()),
           "by_collection": {s: float(g.mean()) for s, g in inside.groupby(rows["slug"])}}
    return {"by_collection": _by(rows, "slug", names), "by_rarity_decile": _by(rows, "rarity_decile", names),
            "by_month": _by(rows, "month", names), "b2_range_80pct_coverage": cov}


def run(data: dict, window: dict, test_w2_end: str) -> tuple[pd.DataFrame, list]:
    """Rows of the window with predictions of the candidate and the baselines, one monthly refit each."""
    h = fv.history(data["sales"])
    static, tcols = fv.static_features(data["tokens"], data["traits"])
    feats = fv.build(h, data["floor_points"], static, data["traits"])
    feats["y"] = feats["premium"]
    test_cut = int((pd.Timestamp(test_w2_end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    test_clean = fv.clean_mask(feats, data["sales"], test_cut)
    traits = data["traits"]
    id_like = {s: list(v) for s, v in traits[traits["id_like"]].groupby("slug")["trait_type"].unique().items()}
    parts, info = [], []
    for m in months(window):
        t0 = time.perf_counter()
        cut = int(m["train_end"].timestamp())
        ts = feats["timestamp"].to_numpy()
        train = feats[(ts < cut) & fv.clean_mask(feats, data["sales"], cut)]
        test = feats[(ts >= int(m["test_start"].timestamp())) & (ts < int(m["test_end"].timestamp())) & test_clean]
        out = test[["hid", "slug", "date", "y", "rarity_decile"]].assign(month=m["month"])
        for name, fn in fvm.BASELINE_FNS.items():
            y_hat, lo, hi = fn(train, test)
            out[f"pred:{name}"], out[f"lo:{name}"], out[f"hi:{name}"] = y_hat, lo, hi
        out[f"pred:{config.NFT_FV_CANDIDATE}"] = fvm.fit_predict(config.NFT_FV_CANDIDATE, train, test, tcols, id_like)
        for n in [config.NFT_FV_CANDIDATE, *BASELINES]:
            out[f"ape:{n}"] = proto.ape(out[f"pred:{n}"], out["y"])
        parts.append(out)
        info.append({"month": m["month"], "train_cutoff": str(m["train_end"].date()), "n_train": len(train),
                     "n_test": len(test), "test_dates": [test["date"].min(), test["date"].max()],
                     "seconds": round(time.perf_counter() - t0, 1)})
        say(f"{m['month']}: n_train {len(train)} n_test {len(test)}")
    return pd.concat(parts, ignore_index=True), info


def main() -> None:
    from ml.gitinfo import git_metadata
    from ml.nft import item_data
    parser = argparse.ArgumentParser(description="Sealed fair-value test (D79)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--sealed", action="store_true")
    args = parser.parse_args()
    mode = "sealed" if args.sealed else "dry_run"
    git = git_metadata()
    if mode == "sealed":
        if git["git_dirty"] or REPORTS["sealed"].exists():
            sys.exit("refusing: the sealed run needs a clean tree and runs once (its report already exists)")
        data, window = item_data.load_history("10.8"), SEALED
    else:
        data, window = item_data.load_dev(include_flagged=True), DRY_RUN
    rows, info = run(data, window, window["last"])
    serve = dict(config.NFT_FV_SERVE)
    report = {"mode": mode, "decision": "D79", **git,
              "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "window": window, "test_w2_from_sales_up_to": window["last"], "candidate": config.NFT_FV_CANDIDATE,
              "params": fvm.params(config.NFT_FV_CANDIDATE), "n_rounds": fvm.N_ROUNDS, "serve": serve,
              "item_manifest_sha256": item_data.require(), "months": info,
              "verdict": decide(rows, serve), "descriptive": descriptive(rows, serve)}
    out = REPORTS[mode]
    out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    rows.to_parquet(out.with_suffix(".rows.parquet"), index=False)
    say(f"{mode}: git {git['git_commit']} dirty {git['git_dirty']}; wrote {out}")
    say(f"verdict {json.dumps(report['verdict'], default=str)}")
    if mode == "sealed":
        LOG.write_text("\n".join(_LINES) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
