"""Phase 9 step 9.4: walk-forward of the volatility forecasts at h = 30 and 7 vs persistence vol_30d (D49).

    python -m ml.evaluation.run_walkforward_risk_v2

Writes ml/reports/{asset}/walkforward_risk_v2.json. Primary metric QLIKE on variance (D43):
s / p - log(s / p) - 1, s = realised fwd variance (fwd_vol_{h}d^2), p = predicted variance; lower is better.
Secondary: Spearman of the prediction vs fwd_vol_{h}d. Each model (EWMA, GARCH) is confirmed on the last 40%
against persistence with a paired block-bootstrap 95% CI (block = h). If both pass, the one with the lower
confirmation QLIKE wins (D49); it would be served through the D36 pooled percentile.
"""

import numpy as np

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.evaluation import part_runner as pr
from ml.evaluation.approval import rank_and_confirm
from ml.evaluation.metrics import qlike
from ml.evaluation.run_baselines import ranking_metrics
from ml.models import risk_v2

REPORT = "walkforward_risk_v2.json"
BASE = risk_v2.BASELINE


def _spearman(pred, actual, horizon: int) -> dict:
    """Spearman with a block-bootstrap CI (block = h); ranking_metrics' fixed 30-day labels are dropped."""
    res = ranking_metrics(pred, actual, horizon)
    return {"spearman": res["spearman"], "spearman_ci95": res["spearman_ci95"]}


def evaluate(pooled, folds, horizon: int) -> dict:
    y = pooled[f"fwd_vol_{horizon}d"].to_numpy()
    names = [BASE] + [c for cs in risk_v2.MODEL_CONFIGS.values() for c in cs]
    preds = {c: pooled[f"pred:{c}"].to_numpy() for c in names}
    losses = {c: qlike(preds[c], y) for c in names}
    conf = pr.confirmation_mask(pooled, folds)
    spearman = {part: {c: _spearman(preds[c][mask], y[mask], horizon) for c in names}
                for part, mask in (("all_folds", np.ones(len(y), bool)), ("confirmation_last_40pct", conf))}
    models = {m: rank_and_confirm(pooled, folds, {c: losses[c] for c in cs + [BASE]}, cs, [BASE], horizon)
              for m, cs in risk_v2.MODEL_CONFIGS.items()}
    approved = {m: r["verdict"]["model_loss"] for m, r in models.items() if r["verdict"]["approved"]}
    return {"models": models, "spearman": spearman,
            "all_folds_mean_qlike": {c: float(v.mean()) for c, v in losses.items()},
            "winner": min(approved, key=approved.get) if approved else None,
            "winner_rule": "D49: among approved models, the lower confirmation QLIKE"}


def verdict_rows(asset: str, results: dict, trials: dict) -> list[dict]:
    rows = []
    for h in sorted(results, reverse=True):
        sp = results[h]["spearman"]["confirmation_last_40pct"]
        for model, res in results[h]["models"].items():
            v = res["verdict"]
            rows.append({"part": "risk", "asset": asset, "horizon": h, "model": model,
                         "best_config": v["top_config"], "model_qlike": v["model_loss"], "baseline": BASE,
                         "baseline_qlike": v["baseline_loss"], "paired_ci": v["paired_diff_baseline_minus_model"],
                         "spearman_model": sp[v["top_config"]].get("spearman"),
                         "spearman_baseline": sp[BASE].get("spearman"), "approved": v["approved"],
                         "winner": results[h]["winner"] == model, "trial_count": trials["per_model"][model]})
    return rows


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    datas = pr.load_all()
    trials = pr.trial_count(risk_v2.MODEL_CONFIGS)
    for asset in config.ASSETS:
        results, sections = {}, {}
        for h in config.FORECAST_HORIZONS:
            pooled, folds, meta = pr.run_asset(datas, asset, h, risk_v2.specs(h))
            results[h] = evaluate(pooled, folds, h)
            sections[f"h{h}"] = {**results[h], **meta}
            print(f"risk {asset} h={h}: {meta['run']['wall_seconds']:.0f} s, approved "
                  f"{ {m: r['verdict']['approved'] for m, r in results[h]['models'].items()} }", flush=True)
        pr.write(asset, REPORT, {
            "part": "risk", "asset": asset, "target": "fwd_vol_{h}d (realised daily vol over the next h days)",
            "metric": "QLIKE on variance (primary, lower is better); Spearman (secondary)",
            "baseline": "persistence vol_30d (served today, D27)",
            "rule": "D44/D49: paired 95% CI (block = h) of QLIKE(persistence) - QLIKE(model) on the last 40% "
                    "excludes 0 with a positive estimate; if both pass, the lower confirmation QLIKE wins",
            "declared": risk_v2.declared(), "trial_count": trials,
            "verdict_table": verdict_rows(asset, results, trials), "horizons": sections})


if __name__ == "__main__":
    main()
