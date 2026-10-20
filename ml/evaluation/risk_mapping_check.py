"""Read-only check of the D36 risk_score mapping (Phase 6a). Report only: nothing is approved or served.

    python -m ml.evaluation.risk_mapping_check --asset btc

Writes ml/reports/{asset}/risk_mapping_check.json: Spearman of the D36 risk_score against fwd_vol_30d on the
walk-forward rows [first origin, b2 - 30), next to persistence's Spearman from walkforward_baselines.json,
both with block-30 bootstrap CIs. Each row's score is computed as it would have been served on that date
(pool = vol_30d of every asset dated <= that row) by ml.serving.responses.pooled_risk_score. Every asset is
cut at its OWN b2 before anything is computed, so no test row of any asset enters the pool or the metric.
risk_score is higher = safer, so a mapping that ranks risk well has a NEGATIVE Spearman with fwd_vol_30d.
"""

import argparse
import json

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean, ranking_metrics
from ml.evaluation.run_walkforward import load_dev, run_metadata
from ml.evaluation.walkforward import check_before_test, make_folds
from ml.serving.responses import pooled_risk_score

H = config.HORIZON_DAYS


def historical_scores(vol: pd.Series, pool: dict[str, pd.Series], rows: range) -> np.ndarray:
    """D36 risk_score of vol at each row in `rows`, with the pool cut at that row's date."""
    allv = pd.concat(pool.values()).sort_index()
    dates, values = allv.index, allv.to_numpy()
    out = []
    for r in rows:
        t = vol.index[r]
        out.append(pooled_risk_score(float(vol.iloc[r]), values[:dates.searchsorted(t, side="right")])[0])
    return np.array(out)


def run(asset: str) -> dict:
    data, b2, n = load_dev(asset)                     # features + labels, rows before this asset's b2 only
    pool = {a: (data if a == asset else load_dev(a)[0])["vol_30d"] for a in config.ASSETS}
    folds = make_folds(len(data), b2)
    rows = range(folds[0].origin, folds[-1].predict.stop)      # the pooled walk-forward rows (D21)
    check_before_test(rows, b2)
    score = historical_scores(data["vol_30d"], pool, rows)
    y = data["fwd_vol_30d"].to_numpy()[rows.start:rows.stop]
    d36 = {**ranking_metrics(score, y, block_size=H), "score": "D36 risk_score (higher = safer)"}
    flipped = {**ranking_metrics(100 - score, y, block_size=H), "score": "100 - D36 risk_score"}
    recomputed = ranking_metrics(data["vol_30d"].to_numpy()[rows.start:rows.stop], y, block_size=H)
    src = ML_ROOT / "reports" / asset / "walkforward_baselines.json"
    persistence = json.loads(src.read_text(encoding="utf-8"))["risk"]["pooled"]["persistence_ranking"]
    pool_ends = {a: s.index[-1] for a, s in pool.items()}
    row_dates = data.index[rows.start:rows.stop]
    cut = [row_dates > end for a, end in pool_ends.items() if a != asset]
    rows_cut, pairs_cut = int(np.logical_or.reduce(cut).sum()), int(sum(c.sum() for c in cut))

    report = {
        "asset": asset, "decision": "D36", "report_only": True,
        "rows": [rows.start, rows.stop], "n_rows": len(rows), "n_effective": len(rows) / H,
        "first_date": row_dates[0].strftime("%Y-%m-%d"), "last_date": row_dates[-1].strftime("%Y-%m-%d"),
        "d36_risk_score": d36,
        "d36_sign_flipped": flipped,
        "persistence": {"source": str(src.relative_to(ML_ROOT.parent)).replace("\\", "/"), **persistence},
        "persistence_recomputed_matches": bool(
            abs(round(recomputed["spearman"], 6) - persistence["spearman"]) < 1e-9
            and abs(round(recomputed["spearman_ci95"]["low"], 6) - persistence["spearman_ci95"]["low"]) < 1e-9
            and abs(round(recomputed["spearman_ci95"]["high"], 6) - persistence["spearman_ci95"]["high"]) < 1e-9),
        "pool": {
            "assets": list(config.ASSETS),
            "last_date_built": {a: end.strftime("%Y-%m-%d") for a, end in pool_ends.items()},
            "rows_with_cut_pool": rows_cut, "row_asset_pairs_cut": pairs_cut,
            "note": ("Each pooled asset is cut at its own b2 (sealed test). Where a row is dated after another "
                     "asset's last pre-test date, that asset's later values are missing from the row's pool, so "
                     "the score can differ slightly from D36 as served; rows_with_cut_pool counts such rows."),
        },
    }
    report["metadata"] = run_metadata(asset, data, b2, n, pd.DataFrame({"row": list(rows)}))
    report["metadata"]["note"] = ("Report only (D36 check). Labels only for rows < b2 - 30 of this asset; test rows "
                                  "[b2, n) of every asset were never built or read.")
    return _clean(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only check of the D36 risk_score mapping")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    for a in config.ASSETS:
        require_validated(a)
    report = run(asset)
    out = ML_ROOT / "reports" / asset / "risk_mapping_check.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
