"""Evaluate the fixed baselines on validation and test (Phase 3, D20). No models are trained.

    python -m ml.evaluation.run_baselines --asset btc

Writes ml/reports/{asset}/baselines.json with sections price, direction, risk, strategy.
Test results are reported only; nothing is chosen on them (docs/EVALUATION.md rule 2).
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np

from ml import config
from ml.gitinfo import git_metadata
from ml.data.dataset_summary import prepare, require_validated
from ml.data.validate import ML_ROOT
from ml.evaluation import baselines as bl
from ml.evaluation import metrics as m
from ml.evaluation.splits import split_dates
from ml.labels.labels import DIRECTION_CLASSES, RISK_CLASSES

EVAL_SPLITS = ("validation", "test")
WINDOWS_PER_YEAR = config.ANNUALISATION_DAYS / config.HORIZON_DAYS
NO_PROBS = "roc_auc_ovr and calibration are null: baselines output hard classes, not probabilities"


def _clean(x):
    """Round floats for the report and turn numpy scalars into plain Python."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return round(float(x), 6) if np.isfinite(x) else None
    if isinstance(x, np.integer):
        return int(x)
    return x


def _add_note(d: dict, note: str) -> dict:
    d["note"] = f"{d['note']}; {note}" if "note" in d else note
    return d


def labelled_rows(d: dict, split: str) -> list[int]:
    ok = d["labels"].notna().all(axis=1)
    return [i for i in d["splits"][split] if ok.iloc[i]]


def counts(rows: list[int]) -> dict:
    return {"n_labelled": len(rows), "n_effective": len(rows) / config.HORIZON_DAYS}


def price_metrics(close_now: np.ndarray, actual_price: np.ndarray, actual_r: np.ndarray, pred_r,
                  block_size: int = 30) -> dict:
    """Price metrics for predicted log returns (a constant or one per row). Shared with walk-forward."""
    pred_r = np.broadcast_to(np.asarray(pred_r, dtype=float), actual_r.shape)
    pred_price = close_now * np.exp(pred_r)
    res = {
        "mae_price": m.mae(pred_price, actual_price),
        "rmse_price": m.rmse(pred_price, actual_price),
        "mape_pct": m.mape(pred_price, actual_price),
        "directional_accuracy": m.directional_accuracy(pred_r, actual_r),
        "skill_vs_last_value": m.skill_vs_naive(m.mae(pred_price, actual_price), m.mae(close_now, actual_price)),
        "mae_price_ci95": m.bootstrap_ci(np.abs(pred_price - actual_price), np.mean, block_size=block_size),
    }
    if res["directional_accuracy"] is None:
        _add_note(res, "directional_accuracy is null: every prediction is a 0 return, so no sign to compare")
    return res


def price_section(d: dict, rows: list[int], preds: dict[str, float]) -> dict:
    close = d["raw"].set_index("timestamp")["close"]
    now, future = close.loc[d["feats"].index], close.shift(-config.HORIZON_DAYS).loc[d["feats"].index]
    c, actual_price = now.iloc[rows].to_numpy(), future.iloc[rows].to_numpy()
    actual_r = d["labels"]["fwd_return_30d"].iloc[rows].to_numpy()
    out = counts(rows)
    for name, r in preds.items():
        out[name] = {"predicted_log_return": r, **price_metrics(c, actual_price, actual_r, r)}
    return out


def class_metrics(a: np.ndarray, p: np.ndarray, classes: tuple, block_size: int = 30) -> dict:
    """Hard-class metrics plus an accuracy CI. Shared with walk-forward."""
    res = m.classification_summary(a, p, classes)
    res["accuracy_ci95"] = m.bootstrap_ci((a == p).astype(float), np.mean, block_size=block_size)
    res["roc_auc_ovr"], res["calibration"] = None, None
    return _add_note(res, NO_PROBS)


def class_section(actual, preds: dict, rows: list[int], classes: tuple) -> dict:
    a = actual.iloc[rows].to_numpy()
    out = counts(rows)
    for name, pred in preds.items():
        out[name] = class_metrics(a, pred.iloc[rows].to_numpy(), classes)
    return out


def ranking_metrics(x: np.ndarray, y: np.ndarray, block_size: int = 30) -> dict:
    """Spearman of a risk score against forward vol, with a block-bootstrap CI. Shared with walk-forward."""
    def stat(idx):
        i = idx.astype(int)
        s = m.spearman(x[i], y[i])
        return np.nan if s is None else s

    return {"score": "vol_30d (trailing)", "target": "fwd_vol_30d", "spearman": m.spearman(x, y),
            "spearman_ci95": m.bootstrap_ci(np.arange(len(x)), stat, block_size=block_size)}


def risk_ranking(d: dict, rows: list[int]) -> dict:
    x = bl.risk_ranking_score(d["feats"]).iloc[rows].to_numpy()
    y = d["labels"]["fwd_vol_30d"].iloc[rows].to_numpy()
    return ranking_metrics(x, y)


def risk_persistence_check(d: dict) -> dict:
    """Sanity check: Spearman(vol_30d, fwd_vol_30d) per split, on the full labelled series, and on
    non-overlapping rows (every 30th labelled row). Train is included as a diagnostic of a fixed rule."""
    ok = d["labels"].notna().all(axis=1)
    full = [i for i in range(len(ok)) if ok.iloc[i]]
    out = {split: {**counts(labelled_rows(d, split)), **risk_ranking(d, labelled_rows(d, split))}
           for split in ("train", "validation", "test")}
    out["full_labelled"] = {**counts(full), **risk_ranking(d, full)}
    step = full[::config.HORIZON_DAYS]
    x = bl.risk_ranking_score(d["feats"]).iloc[step].to_numpy()
    y = d["labels"]["fwd_vol_30d"].iloc[step].to_numpy()
    out["full_non_overlapping"] = {"step_rows": config.HORIZON_DAYS, "n_points": len(step),
                                   "spearman": m.spearman(x, y)}
    return out


def spread(values: np.ndarray) -> dict:
    """Distribution summary: n, min, percentiles, max, std (ddof=1) and IQR."""
    q = {p: float(np.percentile(values, p)) for p in (5, 25, 50, 75, 95)}
    return {"n": len(values), "min": float(values.min()), **{f"p{p}": v for p, v in q.items()},
            "max": float(values.max()), "std": float(np.std(values, ddof=1)), "iqr": q[75] - q[25]}


def vol_spreads(d: dict) -> dict:
    """Spread of fwd_vol_30d (target) and vol_30d (trailing predictor) on each split's labelled rows."""
    out = {"fwd_vol_30d_spread": {}, "vol_30d_spread": {}}
    for split in ("train", "validation", "test"):
        rows = labelled_rows(d, split)
        out["fwd_vol_30d_spread"][split] = spread(d["labels"]["fwd_vol_30d"].iloc[rows].to_numpy())
        out["vol_30d_spread"][split] = spread(d["feats"]["vol_30d"].iloc[rows].to_numpy())
    return out


def strategy_stats(r: np.ndarray) -> dict:
    """Stats of per-window returns from non-overlapping 30-day windows. Shared with walk-forward."""
    res = {
        "mean_window_return": float(r.mean()),
        "median_window_return": float(np.median(r)),
        "hit_rate": float((r > 0).mean()),
        "cumulative_return": m.cumulative_return(r),
        "max_drawdown": m.max_drawdown(r),
        "sharpe_annualised": m.sharpe(r, WINDOWS_PER_YEAR),
        "mean_window_return_ci95": m.bootstrap_ci(r, np.mean, block_size=1),
        "window_returns": r.tolist(),
    }
    if res["sharpe_annualised"] is None:
        _add_note(res, "sharpe_annualised is null: window returns have zero variance")
    return res


def strategy_section(d: dict, split: str) -> dict:
    labelled = d["labels"].notna().all(axis=1)
    starts = bl.window_starts(d["splits"][split], labelled)
    idx = d["feats"].index
    out = {"n_windows": len(starts), "step_days": config.HORIZON_DAYS,
           "first_window_start": idx[starts[0]].strftime("%Y-%m-%d") if starts else None,
           "last_window_start": idx[starts[-1]].strftime("%Y-%m-%d") if starts else None,
           **counts(labelled_rows(d, split))}
    for name, r in bl.strategy_window_returns(d["labels"]["fwd_return_30d"], starts).items():
        out[name] = strategy_stats(r)
    return out


def run(asset: str) -> dict:
    d = prepare(asset)
    feats, labels, classes, th = d["feats"], d["labels"], d["classes"], d["thresholds"]
    train = d["splits"]["train"]
    price_preds = bl.price_baselines(labels.iloc[train])
    dir_preds = bl.direction_baselines(feats, classes["direction"].iloc[train], th)
    risk_preds = bl.risk_baselines(feats, classes["risk"].iloc[train], th)

    report = {"price": {}, "direction": {}, "risk": {}, "strategy": {}}
    for split in EVAL_SPLITS:
        rows = labelled_rows(d, split)
        report["price"][split] = price_section(d, rows, price_preds)
        report["direction"][split] = class_section(classes["direction"], dir_preds, rows, DIRECTION_CLASSES)
        risk = class_section(classes["risk"], risk_preds, rows, RISK_CLASSES)
        risk["persistence_ranking"] = risk_ranking(d, rows)
        risk["train_majority"]["spearman"] = None
        _add_note(risk["train_majority"], "spearman is null: a constant prediction has no ranking")
        report["risk"][split] = risk
        report["strategy"][split] = strategy_section(d, split)
    report["risk_persistence_check"] = risk_persistence_check(d)
    report.update(vol_spreads(d))

    report["metadata"] = {
        "asset": asset,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **git_metadata(),
        "data_first_date": d["raw"]["timestamp"].min().strftime("%Y-%m-%d"),
        "data_last_date": d["raw"]["timestamp"].max().strftime("%Y-%m-%d"),
        "n_feature_rows": len(feats),
        "splits": {k: {"index_range": [r.start, r.stop], **v}
                   for (k, r), v in zip(d["splits"].items(), split_dates(feats.index, d["splits"]).values())},
        "thresholds": {"fitted_on": "train", **th},
        "fitted_on_train": {
            "drift_log_return": price_preds["drift"],
            "direction_majority": dir_preds["train_majority"].iloc[0],
            "risk_majority": risk_preds["train_majority"].iloc[0],
        },
        "horizon_days": config.HORIZON_DAYS,
        "n_effective_rule": "n_labelled / 30 (D20)",
        "note": "Baselines are fixed rules fitted on train only. Test results are reported, never used to choose.",
    }
    return _clean(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baselines on validation and test")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out_dir = ML_ROOT / "reports" / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "baselines.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
