"""Phase 9 step 9.3: walk-forward of the 80% range of the h-day log return at h = 30 and 7 (D43, D44, D49).

    python -m ml.evaluation.run_walkforward_range

Writes ml/reports/{asset}/walkforward_range.json. Per model type (EWMA band, quantile LightGBM): configs ranked
on the first 60% of folds by mean interval score; the top config is confirmed on the last 40% against the
vol_30d band with a paired block-bootstrap 95% CI (block = h). Passes only if that CI excludes 0 with a positive
estimate AND coverage is in [75%, 85%] AND each tail miss <= 15%, on the confirmation folds.
"""

import numpy as np

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.evaluation import interval_metrics as im
from ml.evaluation import part_runner as pr
from ml.evaluation.approval import rank_and_confirm
from ml.models import range_v2

REPORT = "walkforward_range.json"
BASE = range_v2.BASELINE


def _bounds(pooled, name):
    return pooled[f"pred:{name}:lo"].to_numpy(), pooled[f"pred:{name}:hi"].to_numpy()


def evaluate(pooled, folds, data, horizon: int) -> dict:
    y = pooled[f"fwd_return_{horizon}d"].to_numpy()
    names = [BASE] + [c for cs in range_v2.MODEL_CONFIGS.values() for c in cs]
    losses = {c: im.winkler(*_bounds(pooled, c), y) for c in names}
    conf, high = pr.confirmation_mask(pooled, folds), pr.high_vol_mask(data, folds, pooled)
    summaries = {part: {c: im.summary(*(b[mask] for b in _bounds(pooled, c)), y[mask], high[mask]) for c in names}
                 for part, mask in (("all_folds", np.ones(len(y), bool)), ("confirmation_last_40pct", conf))}
    models = {}
    for model, configs in range_v2.MODEL_CONFIGS.items():
        res = rank_and_confirm(pooled, folds, {c: losses[c] for c in configs + [BASE]}, configs, [BASE], horizon)
        top = res["verdict"]["top_config"]
        conditions = im.passes(summaries["confirmation_last_40pct"][top])
        res["verdict"]["approved_ci"] = res["verdict"].pop("approved")
        res["verdict"].update(conditions)
        res["verdict"]["approved"] = bool(res["verdict"]["approved_ci"] and conditions["coverage_in_bounds"]
                                          and conditions["tails_within_max"])
        models[model] = res
    return {"models": models, "summaries": summaries}


def verdict_rows(asset: str, results: dict, trials: dict) -> list[dict]:
    rows = []
    for h in sorted(results, reverse=True):
        conf = results[h]["summaries"]["confirmation_last_40pct"]
        for model, res in results[h]["models"].items():
            v, s = res["verdict"], conf[res["verdict"]["top_config"]]
            rows.append({"part": "range", "asset": asset, "horizon": h, "model": model,
                         "best_config": v["top_config"], "model_interval_score": v["model_loss"],
                         "baseline": BASE, "baseline_interval_score": v["baseline_loss"],
                         "paired_ci": v["paired_diff_baseline_minus_model"], "coverage": s["coverage"],
                         "lower_tail_miss": s["lower_tail_miss"], "upper_tail_miss": s["upper_tail_miss"],
                         "coverage_high_vol": s["coverage_high_vol"],
                         "baseline_coverage": conf[BASE]["coverage"], "approved": v["approved"],
                         "trial_count": trials["per_model"][model]})
    return rows


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    datas = pr.load_all()
    trials = pr.trial_count(range_v2.MODEL_CONFIGS)
    for asset in config.ASSETS:
        results, sections = {}, {}
        for h in config.FORECAST_HORIZONS:
            pooled, folds, meta = pr.run_asset(datas, asset, h, range_v2.specs(h))
            results[h] = evaluate(pooled, folds, datas[h][asset][0], h)
            sections[f"h{h}"] = {**results[h], **meta}
            print(f"range {asset} h={h}: {meta['run']['wall_seconds']:.0f} s, approved "
                  f"{ {m: r['verdict']['approved'] for m, r in results[h]['models'].items()} }", flush=True)
        pr.write(asset, REPORT, {
            "part": "range", "asset": asset,
            "target": "80% interval of fwd_return_{h}d (h-day log return)",
            "metric": f"interval (Winkler) score, alpha = {im.ALPHA:.2f}; lower is better",
            "baseline": "vol_30d band (normal quantiles)",
            "rule": "D44/D49: paired 95% CI (block = h) of score(baseline) - score(model) on the last 40% excludes 0 "
                    "with a positive estimate AND coverage in [0.75, 0.85] AND each tail miss <= 0.15",
            "declared": range_v2.declared(), "trial_count": trials,
            "verdict_table": verdict_rows(asset, results, trials), "horizons": sections})


if __name__ == "__main__":
    main()
