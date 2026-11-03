"""Phase 9 step 9.2: walk-forward of the price candidates at h = 30 and 7 vs last value, with the D44 verdict.

    python -m ml.evaluation.run_walkforward_price_v2 --model ridge  (then lightgbm, prophet_9_2, prophet, lstm)

One model type per run, all assets and both horizons. Its section is merged into
ml/reports/{asset}/walkforward_price_v2.json and the verdict table is rebuilt from all sections there.
Metric: MAE of the h-day log return. Baseline: last value (predicted return 0). Test rows are never built.
"prophet" is the D48 protocol; "prophet_9_2" is the superseded 9.2 protocol, reported for the record only.
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation.approval import rank_and_confirm
from ml.evaluation.run_baselines import _clean, price_metrics
from ml.evaluation.run_walkforward import load_dev, run_metadata
from ml.evaluation.walkforward import make_folds, run_folds
from ml.evaluation.walkforward_history import run_history_folds
from ml.evaluation.walkforward_pooled import PooledSpec, asset_folds, run_pooled
from ml.models import lstm, price_v2

MODELS = ("ridge", "lightgbm", "prophet_9_2", "prophet", "lstm")
LABELS = {"prophet_9_2": "prophet (9.2 protocol, superseded)"}  # D48
BASELINE = "last_value"
REPORT = "walkforward_price_v2.json"


def model_configs(model: str) -> list[str]:
    return list(lstm.CONFIGS) if model == "lstm" else price_v2.MODEL_CONFIGS[model]


def trial_count(model: str) -> int:
    return len(model_configs(model)) * len(config.ASSETS) * len(config.FORECAST_HORIZONS)


def evaluate(pooled: pd.DataFrame, folds, configs: list[str], horizon: int) -> dict:
    """D44 rank and confirm on per-row absolute errors of the h-day log return."""
    actual = pooled[f"fwd_return_{horizon}d"].to_numpy()
    losses = {c: np.abs(pooled[f"pred:{c}"].to_numpy() - actual) for c in configs}
    losses[BASELINE] = np.abs(actual)                           # last value predicts a 0 return
    res = rank_and_confirm(pooled, folds, losses, configs, [BASELINE], horizon)
    top = res["verdict"]["top_config"]
    conf = pooled[pooled["origin"].isin(pooled["origin"].unique()[res["ranking_first_60pct"]["n_folds"]:])]
    res["confirmation_last_40pct"]["usdt_top_config"] = price_metrics(
        conf["close"].to_numpy(), conf[f"close_fwd_{horizon}d"].to_numpy(),
        conf[f"fwd_return_{horizon}d"].to_numpy(), conf[f"pred:{top}"].to_numpy(), horizon)
    res["all_folds"] = {"n_folds": len(folds), "n_pooled": len(pooled), "n_effective": len(pooled) / horizon,
                        "mae_return": {k: float(v.mean()) for k, v in losses.items()},
                        "mean_predicted_log_return": {c: float(pooled[f"pred:{c}"].mean()) for c in configs}}
    return res


def run_per_asset(model: str, datas: dict) -> dict:
    """{asset: {h: section}} for a model fitted per asset through the walk-forward harness."""
    out = {a: {} for a in config.ASSETS}
    for horizon in config.FORECAST_HORIZONS:
        for asset in config.ASSETS:
            data, b2, n = datas[horizon][asset]
            folds = make_folds(len(data), b2, config.MIN_TRAIN_ROWS, horizon, horizon)
            every = price_v2.refit_every_folds(model, horizon)
            t0 = time.perf_counter()
            if model in price_v2.HISTORY_MODELS:
                specs = price_v2.history_specs(model, horizon)
                pooled, info = run_history_folds(data, folds, specs, b2, horizon, every)
                run = {"wall_seconds": time.perf_counter() - t0, **info}
            else:
                specs = price_v2.specs(model, horizon)
                pooled, _ = run_folds(data, folds, {f"price_model/{k}": s for k, s in specs.items()}, b2, horizon)
                pooled = pooled.rename(columns={f"pred:price_model/{k}": f"pred:{k}" for k in specs})
                run = {"wall_seconds": time.perf_counter() - t0, "refit_every_folds": every,
                       "n_fits": {k: s.fit.n_fits for k, s in specs.items()},
                       "fit_seconds": {k: s.fit.fit_seconds for k, s in specs.items()}}
            wall = run["wall_seconds"]
            section = evaluate(pooled, folds, list(specs), horizon)
            section["run"] = run
            section["metadata"] = run_metadata(asset, data, b2, n, pooled, horizon)
            out[asset][horizon] = section
            print(f"{model} {asset} h={horizon}: {wall:.0f} s, approved {section['verdict']['approved']}", flush=True)
    return out


def run_lstm(datas: dict) -> dict:
    out = {a: {} for a in config.ASSETS}
    for horizon in config.FORECAST_HORIZONS:
        every = price_v2.PROPHET_REFIT_EVERY_ROWS_AT_7 // horizon if horizon == 7 else 1
        specs = {name: PooledSpec(fit=lambda sets, name=name: lstm.fit(sets, name, horizon), predict=lstm.predict)
                 for name in lstm.CONFIGS}
        frames = {a: (datas[horizon][a][0], datas[horizon][a][1]) for a in config.ASSETS}
        t0 = time.perf_counter()
        pooled, info = run_pooled(frames, specs, horizon, every)
        wall = time.perf_counter() - t0
        for asset in config.ASSETS:
            data, b2, n = datas[horizon][asset]
            folds = asset_folds(data, b2, horizon)
            section = evaluate(pooled[asset], folds, list(lstm.CONFIGS), horizon)
            section["run"] = {"wall_seconds_all_assets": wall, **info}
            section["metadata"] = run_metadata(asset, data, b2, n, pooled[asset], horizon)
            out[asset][horizon] = section
        print(f"lstm h={horizon}: {wall:.0f} s, fits {info['n_fits']}", flush=True)
    return out


def declared(model: str) -> dict:
    if model == "lstm":
        return {"configs": {k: {"hidden": v, **lstm.SETTINGS} for k, v in lstm.CONFIGS.items()},
                "pooled_over": list(config.ASSETS), "scored_and_approved": "per asset",
                "scaling": "features per asset with that asset's train mean/std; target / pooled train std",
                "early_stopping": "last 15% of each asset's train rows, after an h-row gap"}
    return {"configs": price_v2.declared(model)}


def verdict_table(asset: str, models: dict) -> list[dict]:
    rows = []
    for model in MODELS:
        for key, sec in sorted(models.get(model, {}).get("horizons", {}).items(), key=lambda kv: -int(kv[0][1:])):
            v = sec["verdict"]
            rows.append({"part": "price", "asset": asset, "horizon": int(key[1:]), "model": LABELS.get(model, model),
                         "best_config": v["top_config"], "model_mae": v["model_loss"],
                         "baseline": v["baseline"], "baseline_mae": v["baseline_loss"],
                         "paired_ci": v["paired_diff_baseline_minus_model"], "approved": v["approved"],
                         "trial_count": models[model]["trial_count"], "superseded": model in LABELS})
    return rows


def write(asset: str, model: str, sections: dict) -> None:
    path = ML_ROOT / "reports" / asset / REPORT
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    models = report.get("models", {})
    models[model] = {"label": LABELS.get(model, model), "declared": declared(model), "trial_count": trial_count(model),
                     "horizons": {f"h{h}": sections[h] for h in config.FORECAST_HORIZONS}}
    report = {
        "part": "price", "asset": asset,
        "target": "fwd_return_{h}d, the h-day log return (D41)", "metric": "MAE of the h-day log return",
        "baseline": "last value (predicted return 0)", "rule": "D44: rank on the first 60% of folds, confirm "
        "the top config on the last 40% with a paired block-bootstrap 95% CI (block = h) of MAE(last value) - "
        "MAE(model); approved if it excludes 0 and the estimate is positive",
        "trial_count": {"formula": "configs x assets x horizons; superseded protocols count (D48)",
                        "per_model": {k: v["trial_count"]
                        for k, v in models.items()}, "total": sum(v["trial_count"] for v in models.values())},
        "verdict_table": verdict_table(asset, models),
        "models": {k: models[k] for k in MODELS if k in models},
    }
    path.write_text(json.dumps(_clean(report), indent=2), encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    parser = argparse.ArgumentParser(description="Phase 9 price walk-forward (one model type, all assets)")
    parser.add_argument("--model", required=True, choices=MODELS)
    model = parser.parse_args().model
    for asset in config.ASSETS:
        require_validated(asset)
    datas = {h: {a: load_dev(a, h) for a in config.ASSETS} for h in config.FORECAST_HORIZONS}
    sections = run_lstm(datas) if model == "lstm" else run_per_asset(model, datas)
    for asset in config.ASSETS:
        write(asset, model, sections[asset])


if __name__ == "__main__":
    main()
