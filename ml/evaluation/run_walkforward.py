"""Walk-forward evaluation of the Phase 3 baselines (Phase 4.0, D21). No models are trained.

    python -m ml.evaluation.run_walkforward --asset btc

Writes ml/reports/{asset}/walkforward_baselines.json. Only feature rows before b2 are ever built:
the raw CSV is read for its row count, then cut before the first test row, so test rows never enter
any computation (the test split stays sealed until the final, one-time evaluation).
"""

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.loader import load_raw
from ml.data.validate import ML_ROOT
from ml.evaluation import baselines as bl
from ml.evaluation.run_baselines import (_add_note, _clean, class_metrics, price_metrics, ranking_metrics,
                                         strategy_stats)
from ml.evaluation.splits import make_splits
from ml.evaluation.walkforward import make_folds, run_folds
from ml.features.features import build_features
from ml.gitinfo import git_metadata
from ml.labels.labels import DIRECTION_CLASSES, RISK_CLASSES, build_labels

H = config.HORIZON_DAYS


def dev_data(raw_dev: pd.DataFrame) -> pd.DataFrame:
    """Features, close and labels for the pre-test raw rows. close_fwd_30d is a label (never an input)."""
    feats = build_features(raw_dev)
    close = raw_dev.set_index("timestamp")["close"]
    data = feats.join(build_labels(close).loc[feats.index])
    data["close"] = close.loc[feats.index]
    data["close_fwd_30d"] = close.shift(-H).loc[feats.index]
    return data


def load_dev(asset: str) -> tuple[pd.DataFrame, int, int]:
    """(data for feature rows [0, b2), b2, n). Test rows are dropped before anything is computed."""
    raw = load_raw(asset)
    n = len(raw) - config.WARMUP_ROWS
    b2 = make_splits(n)["test"].start
    data = dev_data(raw.iloc[:config.WARMUP_ROWS + b2].copy())
    del raw
    assert len(data) == b2
    return data, b2, n


def _pooled_counts(pooled: pd.DataFrame) -> dict:
    return {"n_folds": int(pooled["origin"].nunique()), "n_pooled": len(pooled), "n_effective": len(pooled) / H}


def sections(p: pd.DataFrame, block_size: int) -> dict:
    """Price, direction and risk metrics for one set of pooled rows (all rows, or every 30th)."""
    close, fut, r = p["close"].to_numpy(), p["close_fwd_30d"].to_numpy(), p["fwd_return_30d"].to_numpy()
    out = {"price": {}, "direction": {}, "risk": {}}
    for name in ("last_value", "drift"):
        pred = p[f"pred:price/{name}"].to_numpy()
        out["price"][name] = {"mean_predicted_log_return": float(pred.mean()),
                              **price_metrics(close, fut, r, pred, block_size)}
    for name in ("train_majority", "always_up", "momentum"):
        out["direction"][name] = class_metrics(p["direction"].to_numpy(), p[f"pred:direction/{name}"].to_numpy(),
                                               DIRECTION_CLASSES, block_size)
    for name in ("train_majority", "persistence"):
        out["risk"][name] = class_metrics(p["risk"].to_numpy(), p[f"pred:risk/{name}"].to_numpy(),
                                          RISK_CLASSES, block_size)
    out["risk"]["train_majority"]["spearman"] = None
    _add_note(out["risk"]["train_majority"], "spearman is null: a constant prediction has no ranking")
    out["risk"]["persistence_ranking"] = ranking_metrics(
        p["pred:risk_ranking/persistence"].to_numpy(), p["fwd_vol_30d"].to_numpy(), block_size)
    return out


def run(asset: str) -> dict:
    data, b2, n = load_dev(asset)
    folds = make_folds(len(data), b2)
    pooled, fold_table = run_folds(data, folds, bl.walkforward_specs(), b2)
    every = pooled.iloc[::config.WALKFORWARD_STEP]          # the fold origins: non-overlapping rows

    allp, sub = sections(pooled, block_size=H), sections(every, block_size=1)
    counts = _pooled_counts(pooled)
    sub_counts = {"n_points": len(every), "step_rows": config.WALKFORWARD_STEP,
                  "bootstrap_block_size": 1, "note": "rows do not overlap, so the bootstrap resamples single rows"}
    report = {sec: {"pooled": {**counts, "bootstrap_block_size": H, **allp[sec]},
                    "every_30th": {**sub_counts, **sub[sec]}}
              for sec in ("price", "direction", "risk")}

    starts = [int(i) for i in np.flatnonzero(pooled["row"].isin([f.origin for f in folds]).to_numpy())]
    strat = {"n_windows": len(starts), "step_days": H, "window_starts": "fold origins", **counts}
    for name, r in bl.strategy_window_returns(pooled["fwd_return_30d"], starts).items():
        strat[name] = strategy_stats(r)
    report["strategy"] = {"pooled": strat}
    report["folds"] = fold_table

    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    report["metadata"]["note"] = ("Expanding-window walk-forward over rows [0, b2-30) (D21). Thresholds and "
                                  "baseline parameters refit per fold on that fold's train rows. Test rows [b2, n) "
                                  "were never built or read.")
    return _clean(report)


def run_metadata(asset: str, data: pd.DataFrame, b2: int, n: int, pooled: pd.DataFrame) -> dict:
    """Git state, data range and the evidence that the test split stayed sealed. Shared by walk-forward runners."""
    max_row = int(pooled["row"].max())
    return {
        "asset": asset,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **git_metadata(),
        "n_feature_rows": n,
        "b2_test_start_row": b2,
        "rows_built": [0, b2],
        "data_first_date": data.index[0].strftime("%Y-%m-%d"),
        "last_date_built": data.index[-1].strftime("%Y-%m-%d"),
        "sealed_test_first_date": (data.index[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "pooled_rows": [int(pooled["row"].min()), max_row + 1],
        "max_label_row_reached": max_row + H,
        "min_train_rows": config.MIN_TRAIN_ROWS,
        "step_rows": config.WALKFORWARD_STEP,
        "horizon_days": H,
        "embargo_days": config.EMBARGO_DAYS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward evaluation of the baselines")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out_dir = ML_ROOT / "reports" / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "walkforward_baselines.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
