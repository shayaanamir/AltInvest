"""Phase 9 step 9.5: direction at h = 30, LightGBM classifier next to the 4c logistic regression (D49).

    python -m ml.evaluation.run_walkforward_direction_v2

Writes ml/reports/{asset}/walkforward_direction_v2.json and backtest_v2.json. Per model type, configs are
ranked on the first 60% of folds by log loss; the top one is confirmed against the prior on the last 40%
(paired block-bootstrap 95% CI, block 30, D31). The D34 backtest of each model type's top config uses its
signals through generate_signal(serve=True) (evidence only; serving is unchanged, D33). D49 pass rule:
approved in walk-forward AND the backtest beats always-HOLD and buy-and-hold after 0.1% fees per side;
'beats' is reported both as a point estimate and as a paired CI above 0, for the planner to choose.
"""

import numpy as np

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.evaluation import part_runner as pr
from ml.evaluation.approval import rank_and_confirm
from ml.evaluation.prob_metrics import log_loss_rows
from ml.evaluation.run_backtest import backtest
from ml.evaluation.run_walkforward import run_metadata
from ml.evaluation.run_walkforward_direction import PRIOR, prob_columns
from ml.evaluation.walkforward import make_folds, run_folds
from ml.labels.labels import DIRECTION_CLASSES
from ml.models import direction, direction_v2

H = config.HORIZON_DAYS
BASELINES = ("buy_and_hold", "always_hold")


def run_asset(datas: dict, asset: str) -> tuple[dict, dict]:
    data, b2, n = datas[H][asset]
    folds = make_folds(len(data), b2)
    cache = direction.FitCache(direction_v2.factories())
    pooled, _ = run_folds(data, folds, direction.specs(cache), b2)
    actual = pooled["direction"].to_numpy()
    names = [c for cs in direction_v2.MODEL_CONFIGS.values() for c in cs] + [PRIOR]
    losses = {c: log_loss_rows(pooled[prob_columns(c)].to_numpy(), actual, DIRECTION_CLASSES) for c in names}
    at = pooled[pooled["row"].isin([f.origin for f in folds])]
    models, tests = {}, {}
    for model, configs in direction_v2.MODEL_CONFIGS.items():
        res = rank_and_confirm(pooled, folds, {c: losses[c] for c in configs + [PRIOR]}, configs, [PRIOR], H)
        top = res["verdict"]["top_config"]
        res["all_folds_mean_log_loss"] = {c: float(losses[c].mean()) for c in configs + [PRIOR]}
        bt = backtest(asset, at, top)
        ref = bt["strategies"]["reference"]
        beats = {}
        for b in BASELINES:
            ci = bt["paired_mean_window_return"][f"reference_minus_{b}"]
            beats[b] = {"point": bool(ref["mean_window_return"] > bt["baselines"][b]["mean_window_return"]),
                        "ci_above_0": bool(ci is not None and ci["low"] > 0)}
        res["verdict"]["backtest_beats"] = beats
        res["verdict"]["passes_point"] = bool(res["verdict"]["approved"] and all(v["point"] for v in beats.values()))
        res["verdict"]["passes_ci"] = bool(res["verdict"]["approved"] and all(v["ci_above_0"] for v in beats.values()))
        models[model] = res
        tests[model] = {"top_config": top, **bt}
    meta = run_metadata(asset, data, b2, n, pooled)
    return ({"models": models, "convergence_warnings": cache.convergence_warnings(), "metadata": meta},
            {"backtests": tests, "metadata": meta})


def verdict_rows(asset: str, wf: dict, bt: dict, trials: dict) -> list[dict]:
    rows = []
    for model, res in wf["models"].items():
        v, b = res["verdict"], bt["backtests"][model]
        rows.append({"part": "direction", "asset": asset, "horizon": H, "model": model,
                     "best_config": v["top_config"], "model_log_loss": v["model_loss"], "baseline": PRIOR,
                     "baseline_log_loss": v["baseline_loss"], "paired_ci": v["paired_diff_baseline_minus_model"],
                     "approved": v["approved"],
                     "backtest_mean_window_return": b["strategies"]["reference"]["mean_window_return"],
                     **{f"{k}_mean_window_return": b["baselines"][k]["mean_window_return"] for k in BASELINES},
                     "backtest_beats": v["backtest_beats"], "passes_point": v["passes_point"],
                     "passes_ci": v["passes_ci"], "trial_count": trials["per_model"][model]})
    return rows


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    datas = pr.load_all()
    per = {m: len(c) * len(config.ASSETS) for m, c in direction_v2.MODEL_CONFIGS.items()}
    trials = {"formula": "configs x assets x 1 horizon (h = 30 only, D42)", "per_model": per,
              "total": sum(per.values())}
    for asset in config.ASSETS:
        wf, bt = run_asset(datas, asset)
        rows = verdict_rows(asset, wf, bt, trials)
        print(f"direction {asset}: " + ", ".join(f"{r['model']} approved {r['approved']} passes_point "
                                                 f"{r['passes_point']}" for r in rows), flush=True)
        common = {"part": "direction", "asset": asset, "horizon": H, "trial_count": trials, "verdict_table": rows}
        pr.write(asset, "walkforward_direction_v2.json", {
            **common, "metric": "multiclass log loss (lower is better) vs the prior",
            "rule": "D31/D49: paired 95% CI (block 30) of logloss(prior) - logloss(top) on the last 40% excludes 0 "
                    "with a positive estimate; passes also needs the backtest to beat always-HOLD and buy-and-hold",
            "declared": direction_v2.declared(), **wf})
        pr.write(asset, "backtest_v2.json", {
            **common, "protocol": "D34: one 30-day window per fold origin, long-only, 0.1% fee per side; signals "
                                  "of each model type's top config via generate_signal(serve=True); evidence only",
            **bt})


if __name__ == "__main__":
    main()
