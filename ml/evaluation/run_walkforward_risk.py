"""Walk-forward evaluation of the risk model configs vs persistence, with the D25 approval verdict.

    python -m ml.evaluation.run_walkforward_risk --asset btc

Writes ml/reports/{asset}/walkforward_risk.json. Uses the Phase 4.0 harness, so the test split stays sealed.
Spearman is computed on the raw predicted log-vol; class metrics apply exp(prediction) and each fold's
own thresholds (D24). Configs are ranked on the first 60% of folds and the winner is confirmed on the
last 40% (D25). Nothing is tuned here.
"""

import argparse
import json
import math

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.validate import ML_ROOT
from ml.evaluation import baselines as bl
from ml.evaluation import metrics as m
from ml.evaluation.run_baselines import _clean, class_metrics, ranking_metrics
from ml.evaluation.run_walkforward import _pooled_counts, load_dev, run_metadata
from ml.evaluation.walkforward import Fold, make_folds, run_folds
from ml.labels.labels import RISK_CLASSES, risk_class
from ml.models import risk

H = config.HORIZON_DAYS
RANK_FRACTION = 0.6
PERSISTENCE = "persistence"


def split_folds(folds: list[Fold]) -> tuple[list[Fold], list[Fold]]:
    """Chronological 60/40 split of the folds: ranking set first, confirmation set after it."""
    k = math.floor(RANK_FRACTION * len(folds))
    if k == 0 or k == len(folds):
        raise ValueError(f"{len(folds)} folds cannot be split into ranking and confirmation sets")
    return folds[:k], folds[k:]


def classes_from_vol(vol: pd.Series, origins: pd.Series, fold_thresholds: dict) -> pd.Series:
    """Risk classes of a vol-scale score, using the thresholds of each row's own fold."""
    out = pd.Series(index=vol.index, dtype=object)
    for origin, th in fold_thresholds.items():
        sel = origins == origin
        out[sel] = risk_class(vol[sel], th)
    return out


def predictors(pooled: pd.DataFrame, fold_thresholds: dict) -> dict[str, dict]:
    """Per predictor: ranking score (log-vol for models, vol_30d for persistence) and fold-threshold classes."""
    out = {name: {"score": pooled[f"pred:risk_model/{name}"],
                  "classes": classes_from_vol(np.exp(pooled[f"pred:risk_model/{name}"]), pooled["origin"],
                                              fold_thresholds)}
           for name in risk.CONFIGS}
    out[PERSISTENCE] = {"score": pooled["pred:risk_ranking/persistence"], "classes": pooled["pred:risk/persistence"]}
    return out


def evaluate(p: pd.DataFrame, pred: dict) -> dict:
    sel = p.index
    res = {**_pooled_counts(p),
           **ranking_metrics(pred["score"].loc[sel].to_numpy(), p["fwd_vol_30d"].to_numpy())}
    cls = class_metrics(p["risk"].to_numpy(), pred["classes"].loc[sel].to_numpy(), RISK_CLASSES)
    res.update({k: cls[k] for k in ("accuracy", "balanced_accuracy", "macro_f1", "mcc", "per_class",
                                    "confusion_matrix", "accuracy_ci95")})
    if "note" in cls:
        res["class_note"] = cls["note"]
    res.pop("score")
    return res


def _spearman_rows(x: np.ndarray) -> float:
    s = m.spearman(x[:, 0], x[:, 1])
    return np.nan if s is None else s


def run(asset: str) -> dict:
    data, b2, n = load_dev(asset)
    folds = make_folds(len(data), b2)
    base = bl.walkforward_specs()
    specs = {**risk.specs(), "risk_ranking/persistence": base["risk_ranking/persistence"],
             "risk/persistence": base["risk/persistence"]}
    pooled, fold_table = run_folds(data, folds, specs, b2)
    fold_th = {row["origin"]: row["thresholds"] for row in fold_table}
    preds = predictors(pooled, fold_th)

    rank_folds, conf_folds = split_folds(folds)
    in_rank = pooled["origin"].isin([f.origin for f in rank_folds])
    p_rank, p_conf = pooled[in_rank], pooled[~in_rank]

    all_folds = {name: evaluate(pooled, pr) for name, pr in preds.items()}
    first = {name: evaluate(p_rank, pr) for name, pr in preds.items()}
    ranking = sorted(risk.CONFIGS, key=lambda c: -(first[c]["spearman"] if first[c]["spearman"] is not None
                                                   else -np.inf))
    top = ranking[0]

    actual = p_conf["fwd_vol_30d"].to_numpy()
    a = np.c_[preds[top]["score"].loc[p_conf.index].to_numpy(), actual]
    b = np.c_[preds[PERSISTENCE]["score"].loc[p_conf.index].to_numpy(), actual]
    diff = m.paired_bootstrap_ci(a, b, _spearman_rows, block_size=H)
    approved = bool(diff is not None and diff["estimate"] > 0 and diff["low"] > 0)
    conf_counts = _pooled_counts(p_conf)

    report = {
        "configs_declared": {"count": len(risk.CONFIGS),
                             "configs": {k: {"features": v["features"], "model": repr(v["model"]())}
                                         for k, v in risk.CONFIGS.items()},
                             "target": "log(fwd_vol_30d)", "scaling": "standardised with train-fold mean/std"},
        "all_folds": all_folds,
        "ranking_first_60pct": {
            "n_folds": len(rank_folds),
            "date_range": [p_rank.index[0].strftime("%Y-%m-%d"), p_rank.index[-1].strftime("%Y-%m-%d")],
            "metric": "pooled Spearman(predicted log-vol, fwd_vol_30d)",
            "order": ranking,
            "results": first,
        },
        "confirmation_last_40pct": {
            **conf_counts,
            "first_origin_row": conf_folds[0].origin,
            "date_range": [p_conf.index[0].strftime("%Y-%m-%d"), p_conf.index[-1].strftime("%Y-%m-%d")],
            "top_config": top,
            "spearman_top": m.spearman(a[:, 0], actual),
            "spearman_persistence": m.spearman(b[:, 0], actual),
            "paired_diff_spearman_top_minus_persistence": diff,
            "results": {name: evaluate(p_conf, pr) for name, pr in preds.items()},
        },
        "verdict": {
            "top_config": top,
            "approved": approved,
            "rule": "D25: paired 95% CI of the Spearman difference vs persistence on the last 40% excludes 0 "
                    "and the estimate is positive",
            "note": (f"The confirmation set is small (n_effective {conf_counts['n_effective']:.1f}), so "
                     "'not approved' reflects limited statistical power as well as possible lack of skill."),
        },
    }
    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    report["metadata"]["note"] = ("Risk model walk-forward (D21, D24, D25). All configs and fold thresholds fit "
                                  "on each fold's train rows only. Test rows [b2, n) were never built or read.")
    return _clean(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward risk model evaluation and approval verdict")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out_dir = ML_ROOT / "reports" / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "walkforward_risk.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
