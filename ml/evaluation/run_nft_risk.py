"""Phase 10 step 10.3: walk-forward of the floor-volatility forecasts vs persistence, pooled over collections.

    python -m ml.evaluation.run_nft_risk

Writes ml/reports/nft/walkforward_risk.json from the frozen NFT snapshot only (D62). Target: fwd_vol_30d of
the daily floor log returns in ETH (D59, the D24 definition). Primary metric QLIKE on variance (D43); Spearman
secondary. Per collection: 70/15/15 split, 30-day embargo, expanding walk-forward with NFT_MIN_TRAIN_ROWS,
step 30. Approval (D59 as amended): each model type's config is confirmed against persistence on the last 40%
of every collection's folds together, with a date-block bootstrap; it must also be not worse than persistence
in every collection. If both pass, the lower pooled confirmation QLIKE wins (D49). The served volatility is
the winner, or persistence vol_30d when nothing is approved; either way it feeds the cone (D52 as amended).
Sealed test rows are never built (ml.nft.risk_data.dev_frame).

The floor series is floor_eth_model (D66: one-day spikes held back). The same run on the unguarded
floor_eth_asof is written as `sensitivity_unguarded_floor`; it was declared before the run (D66), is reported
for the planner's review and takes no part in the approval.
"""

import json
import time
from datetime import datetime, timezone

import numpy as np

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation import part_runner as pr
from ml.evaluation.approval import rank_and_confirm
from ml.evaluation.metrics import qlike, spearman
from ml.evaluation.nft_approval import pooled_rank_and_confirm
from ml.evaluation.run_baselines import _clean
from ml.evaluation.walkforward import make_folds
from ml.evaluation.walkforward_history import run_history_folds
from ml.gitinfo import git_metadata
from ml.models import nft_risk
from ml.nft import risk_data, snapshot

REPORT = ML_ROOT / "reports" / "nft" / "walkforward_risk.json"
H = config.HORIZON_DAYS
BASE = nft_risk.BASELINE
SENSITIVITY_COLUMN = "floor_eth_asof"       # D66: the unguarded series, reported only
CONFIGS = [c for cs in nft_risk.MODEL_CONFIGS.values() for c in cs]


def run_collection(floor_one, column: str = risk_data.COLUMN) -> dict:
    """Walk-forward of every spec on one collection's pre-test rows."""
    data, b2, n = risk_data.dev_frame(floor_one, column=column)
    folds = make_folds(len(data), b2, config.NFT_MIN_TRAIN_ROWS, H, H)
    t0 = time.perf_counter()
    pooled, info = run_history_folds(data, folds, nft_risk.specs(H), b2, H, every=1,
                                     feature_columns=risk_data.FEATURES)
    y = pooled[f"fwd_vol_{H}d"].to_numpy()
    losses = {c: qlike(pooled[f"pred:{c}"].to_numpy(), y) for c in CONFIGS + [BASE]}
    in_rank = ~pr.confirmation_mask(pooled, folds)
    max_row = int(pooled["row"].max())
    meta = {"n_feature_rows": n, "b2_test_start_row": b2, "rows_built": [0, b2],
            "data_first_date": data.index[0].strftime("%Y-%m-%d"),
            "last_date_built": data.index[-1].strftime("%Y-%m-%d"),
            "sealed_test_first_date": (data.index[-1] + np.timedelta64(1, "D")).strftime("%Y-%m-%d"),
            "pooled_rows": [int(pooled["row"].min()), max_row + 1], "max_label_row_reached": max_row + H,
            "n_folds": len(folds), "n_pooled": len(pooled), "n_effective": len(pooled) / H,
            "min_train_rows": config.NFT_MIN_TRAIN_ROWS, "step_rows": H, "horizon_days": H, "embargo_days": H,
            "wall_seconds": time.perf_counter() - t0, **info}
    return {"pooled": pooled, "folds": folds, "losses": losses, "in_rank": in_rank, "y": y, "metadata": meta}


def collection_section(run: dict) -> dict:
    """Per-collection view (reported; approval is pooled): the D44 verdict per model and Spearman."""
    pooled, folds, losses, conf = run["pooled"], run["folds"], run["losses"], ~run["in_rank"]
    models = {m: rank_and_confirm(pooled, folds, {c: losses[c] for c in cs + [BASE]}, cs, [BASE], H)
              for m, cs in nft_risk.MODEL_CONFIGS.items()}
    sp = {c: spearman(pooled[f"pred:{c}"].to_numpy()[conf], run["y"][conf]) for c in CONFIGS + [BASE]}
    return {"metadata": run["metadata"], "models": models, "spearman_confirmation_last_40pct": sp,
            "all_folds_mean_qlike": {c: float(v.mean()) for c, v in losses.items()}}


def verdict_rows(pooled_results: dict, sections: dict, winner: str | None) -> list[dict]:
    rows = []
    for model, res in pooled_results.items():
        v = res["verdict"]
        rows.append({"part": "nft_risk", "scope": "pooled (all collections)", "horizon": H, "model": model,
                     "config": v["top_config"], "model_qlike": v["model_loss"], "baseline": BASE,
                     "baseline_qlike": v["baseline_loss"], "paired_ci": v["paired_diff_baseline_minus_model"],
                     "every_collection_not_worse": v["every_collection_not_worse"], "approved": v["approved"],
                     "winner": winner == model})
        for slug, sec in sections.items():
            c = sec["models"][model]["verdict"]
            rows.append({"part": "nft_risk", "scope": slug, "horizon": H, "model": model,
                         "config": c["top_config"], "model_qlike": c["model_loss"], "baseline": BASE,
                         "baseline_qlike": c["baseline_loss"], "paired_ci": c["paired_diff_baseline_minus_model"],
                         "spearman_model": sec["spearman_confirmation_last_40pct"][c["top_config"]],
                         "spearman_baseline": sec["spearman_confirmation_last_40pct"][BASE],
                         "approved_alone": c["approved"], "note": "reported only; approval is pooled (D59)"})
    return rows


def build(floor, column: str = risk_data.COLUMN) -> dict:
    runs = {slug: run_collection(f, column) for slug, f in floor.groupby("slug", sort=True)}
    rows = {slug: {"dates": r["pooled"].index.strftime("%Y-%m-%d").to_numpy(), "in_rank": r["in_rank"],
                   "losses": r["losses"]} for slug, r in runs.items()}
    pooled_results = {m: pooled_rank_and_confirm(rows, cs, BASE, H) for m, cs in nft_risk.MODEL_CONFIGS.items()}
    approved = {m: r["verdict"]["model_loss"] for m, r in pooled_results.items() if r["verdict"]["approved"]}
    winner = min(approved, key=approved.get) if approved else None
    sections = {slug: collection_section(r) for slug, r in runs.items()}
    n_trials = {m: len(cs) for m, cs in nft_risk.MODEL_CONFIGS.items()}
    return {
        "part": "nft_risk", "floor_column": column,
        "target": f"fwd_vol_30d of the daily floor log returns in ETH ({column}; D59, D63, D66)",
        "metric": "QLIKE on variance (primary, lower is better); Spearman (secondary)",
        "baseline": "persistence vol_30d of the floor",
        "rule": "D59 (amended 2026-11-10) with D44: pooled paired 95% CI (date blocks of 30) of QLIKE(persistence) "
                "- QLIKE(model) on the last 40% of every collection's folds excludes 0 with a positive estimate, "
                "and no collection is worse than persistence; if both models pass, the lower pooled QLIKE wins",
        "declared": nft_risk.declared(),
        "trial_count": {"formula": "configs x 1 pooled test x 1 horizon (baselines are not trials); the per-"
                                   "collection rows are reported, not separate approvals",
                        "per_model": n_trials, "total": sum(n_trials.values()),
                        "collection_level_rows_reported": sum(n_trials.values()) * len(runs),
                        "sensitivity_runs_reported_not_approvals": sum(n_trials.values())},
        "pooled": pooled_results, "winner": winner,
        "served_volatility": winner or BASE,
        "served_note": "the cone uses whichever volatility is served (D52 amended): the winner, or persistence "
                       "vol_30d when no model is approved",
        "verdict_table": verdict_rows(pooled_results, sections, winner),
        "collections": sections,
    }


def main() -> None:
    manifest_sha = snapshot.require_snapshot("floor")           # D62: frozen snapshot only
    floor = snapshot.load("floor")
    report = build(floor)
    sens = build(floor, column=SENSITIVITY_COLUMN)
    report["sensitivity_unguarded_floor"] = {
        "floor_column": SENSITIVITY_COLUMN,
        "note": "D66: the same run without the spike guard. Reported only; not an approval and not served.",
        "pooled_verdicts": {m: r["verdict"] for m, r in sens["pooled"].items()},
        "would_serve": sens["served_volatility"],
        "all_folds_mean_qlike": {s: c["all_folds_mean_qlike"] for s, c in sens["collections"].items()}}
    report["metadata"] = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                          **git_metadata(), "snapshot": config.NFT_SNAPSHOT_DATE,
                          "snapshot_manifest_sha256": manifest_sha, "collections": list(report["collections"])}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(_clean(report), indent=2), encoding="utf-8")
    print(f"wrote {REPORT}")
    for row in report["verdict_table"]:
        if row["scope"].startswith("pooled"):
            ci = row["paired_ci"] or {}
            print(f"{row['model']}: QLIKE {row['model_qlike']:.4f} vs {row['baseline_qlike']:.4f}, diff "
                  f"{ci.get('estimate', float('nan')):.4f} [{ci.get('low', float('nan')):.4f}, "
                  f"{ci.get('high', float('nan')):.4f}], approved {row['approved']}")
    print(f"served volatility: {report['served_volatility']}")


if __name__ == "__main__":
    main()
