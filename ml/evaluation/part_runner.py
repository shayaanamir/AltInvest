"""Shared plumbing for the Phase 9 range and risk runners (9.3, 9.4): load each asset's pre-test rows per
horizon, run HistorySpecs through the D48 harness, split rows into ranking / confirmation folds, and write the
per-asset report. Test rows [b2, n) are never built (load_dev).
"""

import json
import time

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean
from ml.evaluation.run_walkforward import load_dev, run_metadata
from ml.evaluation.run_walkforward_risk import split_folds
from ml.evaluation.walkforward import make_folds
from ml.evaluation.walkforward_history import run_history_folds


def load_all() -> dict:
    """{h: {asset: (data, b2, n)}} for every horizon and asset (validated snapshot only)."""
    for asset in config.ASSETS:
        require_validated(asset)
    return {h: {a: load_dev(a, h) for a in config.ASSETS} for h in config.FORECAST_HORIZONS}


def run_asset(datas: dict, asset: str, horizon: int, specs: dict) -> tuple[pd.DataFrame, list, dict]:
    """(pooled rows with pred:<spec>, folds, run info incl. wall seconds and the run metadata)."""
    data, b2, n = datas[horizon][asset]
    folds = make_folds(len(data), b2, config.MIN_TRAIN_ROWS, horizon, horizon)
    t0 = time.perf_counter()
    pooled, info = run_history_folds(data, folds, specs, b2, horizon, every=1)
    info = {"wall_seconds": time.perf_counter() - t0, **info}
    return pooled, folds, {"run": info, "metadata": run_metadata(asset, data, b2, n, pooled, horizon)}


def confirmation_mask(pooled: pd.DataFrame, folds: list) -> np.ndarray:
    _, conf = split_folds(folds)
    return pooled["origin"].isin([f.origin for f in conf]).to_numpy()


def high_vol_mask(data: pd.DataFrame, folds: list, pooled: pd.DataFrame) -> np.ndarray:
    """vol_30d at t above the upper RISK_PERCENTILES threshold of that fold's TRAIN rows (D43)."""
    q = config.RISK_PERCENTILES[1]
    thresholds = {f.origin: float(np.percentile(data["vol_30d"].iloc[f.train], q)) for f in folds}
    vol = data["vol_30d"].to_numpy()[pooled["row"].to_numpy()]      # pooled rows carry no feature columns
    return vol > pooled["origin"].map(thresholds).to_numpy()


def trial_count(model_configs: dict) -> dict:
    per = {m: len(c) * len(config.ASSETS) * len(config.FORECAST_HORIZONS) for m, c in model_configs.items()}
    return {"formula": "configs x assets x horizons (baselines are not trials)", "per_model": per,
            "total": sum(per.values())}


def write(asset: str, filename: str, report: dict) -> None:
    path = ML_ROOT / "reports" / asset / filename
    path.write_text(json.dumps(_clean(report), indent=2), encoding="utf-8")
    print(f"wrote {path}", flush=True)
