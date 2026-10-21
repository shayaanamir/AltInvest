"""Walk-forward evaluation of the price model configs vs the price baselines, with the D28 verdict.

    python -m ml.evaluation.run_walkforward_price --asset btc

Writes ml/reports/{asset}/walkforward_price.json. Uses the Phase 4.0 harness, so the test split stays sealed.
Primary view: errors of fwd_return_30d (30-day log return). Secondary view: USDT, price = close[t] * exp(pred).
Configs are ranked on the first 60% of folds by pooled return MAE and the winner is confirmed on the
last 40% against last-value (D25, D28). Nothing is tuned here.
"""

import argparse
import json

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation import metrics as m
from ml.evaluation.run_baselines import _add_note, _clean, price_metrics
from ml.evaluation.run_walkforward import _pooled_counts, load_dev, run_metadata
from ml.evaluation.run_walkforward_risk import split_folds
from ml.evaluation.walkforward import make_folds, run_folds
from ml.models import price

H = config.HORIZON_DAYS
LAST_VALUE = "price_baseline/last_value"


def return_metrics(pred: np.ndarray, actual: np.ndarray, block_size: int = H) -> dict:
    """Errors of the predicted 30-day log return, with block-bootstrap CIs."""
    err = pred - actual
    res = {
        "mae_return": m.mae(pred, actual),
        "mae_return_ci95": m.bootstrap_ci(np.abs(err), np.mean, block_size=block_size),
        "rmse_return": m.rmse(pred, actual),
        "rmse_return_ci95": m.bootstrap_ci(err ** 2, lambda s: float(np.sqrt(np.mean(s))), block_size=block_size),
        "skill_vs_last_value": m.skill_vs_naive(m.mae(pred, actual), m.mae(np.zeros_like(actual), actual)),
        "directional_accuracy": m.directional_accuracy(pred, actual),
    }
    if res["directional_accuracy"] is None:
        _add_note(res, "directional_accuracy is null: every prediction is a 0 return, so no sign to compare")
    return res


def evaluate(p: pd.DataFrame, col: str) -> dict:
    pred, actual = p[col].to_numpy(), p["fwd_return_30d"].to_numpy()
    usdt = price_metrics(p["close"].to_numpy(), p["close_fwd_30d"].to_numpy(), actual, pred)
    return {**_pooled_counts(p), "mean_predicted_log_return": float(pred.mean()),
            "return": return_metrics(pred, actual), "usdt": usdt}


def _mae_rows(x: np.ndarray) -> float:
    return float(np.mean(np.abs(x[:, 0] - x[:, 1])))


def run(asset: str) -> dict:
    data, b2, n = load_dev(asset)
    folds = make_folds(len(data), b2)
    pooled, fold_table = run_folds(data, folds, price.specs(), b2)
    cols = {name: f"price_model/{name}" for name in price.CONFIGS}
    cols.update({name: f"price_baseline/{name}" for name in price.BASELINES})

    rank_folds, conf_folds = split_folds(folds)
    in_rank = pooled["origin"].isin([f.origin for f in rank_folds])
    p_rank, p_conf = pooled[in_rank], pooled[~in_rank]

    first = {name: evaluate(p_rank, f"pred:{c}") for name, c in cols.items()}
    ranking = sorted(price.CONFIGS, key=lambda c: first[c]["return"]["mae_return"])
    top = ranking[0]
    best_baseline = min(price.BASELINES, key=lambda b: first[b]["return"]["mae_return"])

    actual = p_conf["fwd_return_30d"].to_numpy()
    lv = np.c_[p_conf[f"pred:{LAST_VALUE}"].to_numpy(), actual]
    model = np.c_[p_conf[f"pred:price_model/{top}"].to_numpy(), actual]
    diff = m.paired_bootstrap_ci(lv, model, _mae_rows, block_size=H)        # MAE(last-value) - MAE(model)
    approved = bool(diff is not None and diff["estimate"] > 0 and diff["low"] > 0)
    conf_counts = _pooled_counts(p_conf)

    report = {
        "configs_declared": {"count": len(price.CONFIGS),
                             "configs": {k: repr(v()) for k, v in price.CONFIGS.items()},
                             "baselines": list(price.BASELINES),
                             "target": "fwd_return_30d (30-day log return)",
                             "features": "all existing feature columns",
                             "scaling": "standardised with train-fold mean/std"},
        "all_folds": {name: evaluate(pooled, f"pred:{c}") for name, c in cols.items()},
        "ranking_first_60pct": {
            "n_folds": len(rank_folds),
            "date_range": [p_rank.index[0].strftime("%Y-%m-%d"), p_rank.index[-1].strftime("%Y-%m-%d")],
            "metric": "pooled MAE of fwd_return_30d (lower is better)",
            "order": ranking,
            "best_baseline": best_baseline,
            "results": first,
        },
        "confirmation_last_40pct": {
            **conf_counts,
            "date_range": [p_conf.index[0].strftime("%Y-%m-%d"), p_conf.index[-1].strftime("%Y-%m-%d")],
            "top_config": top,
            "mae_return_last_value": _mae_rows(lv),
            "mae_return_top": _mae_rows(model),
            "paired_diff_mae_last_value_minus_top": diff,
            "results": {name: evaluate(p_conf, f"pred:{c}") for name, c in cols.items()},
        },
        "verdict": {
            "top_config": top,
            "approved": approved,
            "rule": "D28: paired 95% CI of MAE(last-value) - MAE(model) of fwd_return_30d on the last 40% "
                    "is above 0 (and the estimate is positive)",
            "note": (f"The confirmation set is small (n_effective {conf_counts['n_effective']:.1f}), so "
                     "'not approved' reflects limited statistical power as well as possible lack of skill."),
        },
        "folds": [{k: row[k] for k in ("origin", "origin_date", "train_rows", "predict_rows")} for row in fold_table],
    }
    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    report["metadata"]["note"] = ("Price model walk-forward (D21, D25, D28). Configs and baselines fit on each "
                                  "fold's train rows only. Test rows [b2, n) were never built or read.")
    return _clean(report)


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    parser = argparse.ArgumentParser(description="Walk-forward price model evaluation and approval verdict")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out_dir = ML_ROOT / "reports" / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "walkforward_price.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
