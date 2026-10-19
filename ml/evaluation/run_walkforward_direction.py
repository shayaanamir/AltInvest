"""Walk-forward evaluation of the direction model configs vs the class prior, with the D31 verdict.

    python -m ml.evaluation.run_walkforward_direction --asset btc

Writes ml/reports/{asset}/walkforward_direction.json. Uses the Phase 4.0 harness, so the test split stays
sealed. Primary metric: multiclass log loss of DOWN/FLAT/UP with each fold's own classes. Configs are ranked
on the first 60% of folds and the winner is confirmed against the prior on the last 40% (D25, D31).
The hard Phase 3 baselines are context only: class metrics, never ranked or used for approval.
"""

import argparse
import json

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.validate import ML_ROOT
from ml.evaluation import baselines as bl
from ml.evaluation import metrics as m
from ml.evaluation.prob_metrics import ece, log_loss_rows
from ml.evaluation.run_baselines import NO_PROBS, _add_note, _clean, class_metrics
from ml.evaluation.run_walkforward import _pooled_counts, load_dev, run_metadata
from ml.evaluation.run_walkforward_risk import split_folds
from ml.evaluation.walkforward import make_folds, run_folds
from ml.labels.labels import DIRECTION_CLASSES
from ml.models import direction

H = config.HORIZON_DAYS
CLASSES = DIRECTION_CLASSES
HARD = ("train_majority", "always_up", "momentum")
HARD_NOTE = "hard class predictions have no probabilities; context only, not used in ranking or approval"
PRIOR = direction.BASELINE


def prob_columns(name: str) -> list[str]:
    prefix = "direction_prior" if name == PRIOR else f"direction_model/{name}"
    return [f"pred:{prefix}/P_{c}" for c in CLASSES]


def evaluate_prob(p: pd.DataFrame, name: str) -> dict:
    """Probabilistic metrics plus class metrics of the argmax, for one predictor on pooled rows `p`."""
    prob, actual = p[prob_columns(name)].to_numpy(), p["direction"].to_numpy()
    ll = log_loss_rows(prob, actual, CLASSES)
    argmax = np.array(CLASSES)[prob.argmax(axis=1)]
    cls = class_metrics(actual, argmax, CLASSES)
    for k in ("roc_auc_ovr", "calibration"):                  # reported at the top level for probabilities
        cls.pop(k)
    cls["note"] = cls["note"].replace(NO_PROBS, "").strip("; ")
    if not cls["note"]:
        cls.pop("note")
    return {
        **_pooled_counts(p),
        "log_loss": float(ll.mean()),
        "log_loss_ci95": m.bootstrap_ci(ll, np.mean, block_size=H),
        "brier": m.brier_multiclass(prob, actual, CLASSES),
        "roc_auc_ovr": m.roc_auc_ovr(prob, actual, CLASSES),
        "ece": ece(prob, actual, CLASSES),
        "reliability_bins": {c: m.calibration_bins(prob[:, k], (actual == c).astype(float))
                             for k, c in enumerate(CLASSES)},
        "mean_prob_vs_observed": {c: {"mean_predicted": float(prob[:, k].mean()),
                                      "observed_freq": float((actual == c).mean())} for k, c in enumerate(CLASSES)},
        "argmax_class_metrics": cls,
    }


def evaluate_hard(p: pd.DataFrame, name: str) -> dict:
    res = {**_pooled_counts(p),
           **class_metrics(p["direction"].to_numpy(), p[f"pred:direction/{name}"].to_numpy(), CLASSES)}
    res.update({"log_loss": None, "brier": None, "roc_auc_ovr": None, "ece": None})
    return _add_note(res, HARD_NOTE)


def results(p: pd.DataFrame) -> dict:
    out = {name: evaluate_prob(p, name) for name in (*direction.CONFIGS, PRIOR)}
    out.update({f"hard/{name}": evaluate_hard(p, name) for name in HARD})
    return out


def rank(first: dict) -> list[str]:
    """Order of the declared configs by pooled log loss (lower first). Prior and hard baselines never enter."""
    return sorted(direction.CONFIGS, key=lambda c: first[c]["log_loss"])


def run(asset: str) -> dict:
    data, b2, n = load_dev(asset)
    folds = make_folds(len(data), b2)
    cache = direction.FitCache()
    base = bl.walkforward_specs()
    specs = {**direction.specs(cache), **{f"direction/{h}": base[f"direction/{h}"] for h in HARD}}
    pooled, fold_table = run_folds(data, folds, specs, b2)

    rank_folds, conf_folds = split_folds(folds)
    in_rank = pooled["origin"].isin([f.origin for f in rank_folds])
    p_rank, p_conf = pooled[in_rank], pooled[~in_rank]

    first = results(p_rank)
    ranking = rank(first)
    top = ranking[0]

    actual = p_conf["direction"].to_numpy()
    ll_prior = log_loss_rows(p_conf[prob_columns(PRIOR)].to_numpy(), actual, CLASSES)
    ll_top = log_loss_rows(p_conf[prob_columns(top)].to_numpy(), actual, CLASSES)
    diff = m.paired_bootstrap_ci(ll_prior, ll_top, np.mean, block_size=H, n_boot=1000, seed=0)
    approved = bool(diff is not None and diff["estimate"] > 0 and diff["low"] > 0)
    conf_counts = _pooled_counts(p_conf)

    report = {
        "configs_declared": {
            "count": len(direction.CONFIGS),
            "configs": {k: repr(v()) for k, v in direction.CONFIGS.items()},
            "baseline": f"{PRIOR}: train-fold class frequencies as probabilities",
            "eps": direction.EPS,
            "features": "all existing feature columns",
            "scaling": "standardised with train-fold mean/std",
            "target": "direction class (DOWN/FLAT/UP) with each fold's own thresholds (D19, D21)",
            "convergence_warnings": cache.convergence_warnings(),
        },
        "all_folds": results(pooled),
        "ranking_first_60pct": {
            "n_folds": len(rank_folds),
            "date_range": [p_rank.index[0].strftime("%Y-%m-%d"), p_rank.index[-1].strftime("%Y-%m-%d")],
            "metric": "pooled mean log loss (lower is better)",
            "order": ranking,
            "results": first,
        },
        "confirmation_last_40pct": {
            **conf_counts,
            "date_range": [p_conf.index[0].strftime("%Y-%m-%d"), p_conf.index[-1].strftime("%Y-%m-%d")],
            "top_config": top,
            "logloss_prior": float(ll_prior.mean()),
            "logloss_top": float(ll_top.mean()),
            "paired_diff_logloss_prior_minus_top": diff,
            "ci_half_width": None if diff is None else (diff["high"] - diff["low"]) / 2,
            "results": results(p_conf),
        },
        "verdict": {
            "top_config": top,
            "approved": approved,
            "rule": "D31: paired 95% CI of logloss(prior) - logloss(top) on the last 40% is above 0 and the "
                    "estimate is positive",
            "note": (f"The confirmation set is small (n_effective {conf_counts['n_effective']:.1f}), so "
                     "'not approved' means 'no demonstrated gain' (D29, D30), not 'no skill'."),
        },
        "folds": [{"origin": r["origin"], "origin_date": r["origin_date"], "train_rows": r["train_rows"],
                   "predict_rows": r["predict_rows"],
                   "direction_flat_abs_return": r["thresholds"]["direction_flat_abs_return"]} for r in fold_table],
    }
    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    report["metadata"]["note"] = ("Direction model walk-forward (D21, D25, D31). Configs and the prior fit on each "
                                  "fold's train rows only. Test rows [b2, n) were never built or read.")
    return _clean(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward direction model evaluation and approval verdict")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out_dir = ML_ROOT / "reports" / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "walkforward_direction.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
