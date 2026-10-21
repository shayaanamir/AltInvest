"""Mechanism check of the Phase 4c direction model (Phase 5a). Report only: nothing is decided from it.

    python -m ml.evaluation.direction_mechanism --asset eth

Recomputes the 4c pooled walk-forward predictions in memory with the same specs, takes the 4c top config
from walkforward_direction.json (no re-ranking) and writes ml/reports/{asset}/direction_mechanism.json with,
on the last-40% rows and on all folds:
  1. Spearman(P(FLAT), vol_30d)                - calm markets -> more FLAT?
  2. Spearman(P(FLAT), |fwd_return_30d|)       - move-vs-no-move skill
  3. Spearman(P(UP) - P(DOWN), fwd_return_30d) - up/down skill
plus the mean predicted P(FLAT) vs the observed FLAT share. The test split stays sealed (Phase 4.0 harness).
"""

import argparse
import json

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation.prob_metrics import log_loss_rows
from ml.evaluation.run_baselines import _clean, ranking_metrics
from ml.evaluation.run_walkforward import _pooled_counts, load_dev, run_metadata
from ml.evaluation.run_walkforward_direction import PRIOR, prob_columns
from ml.evaluation.run_walkforward_risk import split_folds
from ml.evaluation.walkforward import make_folds, run_folds
from ml.labels.labels import DIRECTION_CLASSES
from ml.models import direction

H = config.HORIZON_DAYS
TOLERANCE = 1e-9


def pooled_predictions(data: pd.DataFrame, b2: int, min_train: int = config.MIN_TRAIN_ROWS):
    """The 4c pooled predictions (same specs, same harness) and the folds. Adds vol_30d by row position."""
    folds = make_folds(len(data), b2, min_train)
    pooled, _ = run_folds(data, folds, direction.specs(direction.FitCache()), b2)
    pooled = pooled.assign(vol_30d=data["vol_30d"].iloc[pooled["row"].to_numpy()].to_numpy())
    return pooled, folds


def _check(x: np.ndarray, y: np.ndarray, score: str, target: str, expected: str) -> dict:
    res = ranking_metrics(x, y, block_size=H)
    return {**res, "score": score, "target": target, "expected": expected}


def mechanism_checks(prob: np.ndarray, vol_30d, fwd_return, actual) -> dict:
    """The three rank correlations and the FLAT share. prob columns are in DIRECTION_CLASSES order."""
    k = {c: i for i, c in enumerate(DIRECTION_CLASSES)}
    p_flat, up_minus_down = prob[:, k["FLAT"]], prob[:, k["UP"]] - prob[:, k["DOWN"]]
    r, actual = np.asarray(fwd_return, dtype=float), np.asarray(actual)
    return {
        "check_1_pflat_vs_vol30d": _check(p_flat, np.asarray(vol_30d, dtype=float), "P(FLAT)", "vol_30d",
                                          "negative: calm -> FLAT"),
        "check_2_pflat_vs_abs_fwd_return": _check(p_flat, np.abs(r), "P(FLAT)", "|fwd_return_30d|",
                                                  "negative: move-vs-no-move skill"),
        "check_3_up_minus_down_vs_fwd_return": _check(up_minus_down, r, "P(UP) - P(DOWN)", "fwd_return_30d",
                                                      "CI containing 0 (no demonstrated up/down skill)"),
        "mean_predicted_p_flat": float(p_flat.mean()),
        "observed_flat_share": float((actual == "FLAT").mean()),
    }


def block(p: pd.DataFrame, top: str) -> dict:
    return {**_pooled_counts(p), **mechanism_checks(p[prob_columns(top)].to_numpy(), p["vol_30d"],
                                                     p["fwd_return_30d"], p["direction"])}


def run(asset: str) -> dict:
    wf = json.loads((ML_ROOT / "reports" / asset / "walkforward_direction.json").read_text(encoding="utf-8"))
    top, conf = wf["verdict"]["top_config"], wf["confirmation_last_40pct"]
    data, b2, n = load_dev(asset)
    pooled, folds = pooled_predictions(data, b2)
    rank_folds, _ = split_folds(folds)
    p_conf = pooled[~pooled["origin"].isin([f.origin for f in rank_folds])]

    actual = p_conf["direction"].to_numpy()
    recomputed = {"logloss_prior": float(log_loss_rows(p_conf[prob_columns(PRIOR)].to_numpy(), actual,
                                                       DIRECTION_CLASSES).mean()),
                  "logloss_top": float(log_loss_rows(p_conf[prob_columns(top)].to_numpy(), actual,
                                                     DIRECTION_CLASSES).mean())}
    # the 4c report stores values rounded to 6 decimals, so compare the rounded recomputation
    matches = {k: abs(round(v, 6) - conf[k]) <= TOLERANCE for k, v in recomputed.items()}
    if not all(matches.values()):
        raise RuntimeError(f"recomputed confirmation log losses differ from walkforward_direction.json: "
                           f"{recomputed} vs {conf['logloss_prior']}, {conf['logloss_top']}")

    report = {
        "top_config": top,
        "source": f"ml/reports/{asset}/walkforward_direction.json (top config read, not re-ranked)",
        "consistency_check": {"recomputed": recomputed,
                              "reported": {k: conf[k] for k in recomputed},
                              "tolerance_after_rounding_to_6dp": TOLERANCE, "matches": matches},
        "last_40pct": {"date_range": [p_conf.index[0].strftime("%Y-%m-%d"), p_conf.index[-1].strftime("%Y-%m-%d")],
                       **block(p_conf, top)},
        "all_folds": block(pooled, top),
        "note": "Report only (Phase 5a). Spearman CIs: moving-block bootstrap, block 30. No decision is made here.",
    }
    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    return _clean(report)


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    parser = argparse.ArgumentParser(description="Mechanism check of the 4c direction model (report only)")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out = ML_ROOT / "reports" / asset / "direction_mechanism.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
