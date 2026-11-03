"""Phase 9 step 9.2b: time one Prophet and one pooled LSTM fit + predict on the largest fold, and project the
total 9.2 run time with the D41 refit cadence. Run inside the training image (ml/Dockerfile.train):

    python -m ml.evaluation.timing_price_v2

Writes ml/reports/timing_price_v2.json. Fits are timed, not evaluated: no metric is computed.
Projection: upper = n_fits x largest-fold time; mean = n_fits x largest-fold time x (mean train rows /
largest train rows), assuming fit time grows linearly with rows.
"""

import json
import os
import platform
import time
from datetime import datetime, timezone

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation.run_walkforward import load_dev
from ml.evaluation.walkforward_pooled import asset_folds, pooled_train_sets
from ml.gitinfo import git_metadata
from ml.models import lstm, price_v2


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def per_asset_fits(datas, horizon, every):
    """Fits for one config of a per-asset model, and the mean / largest train rows over the fitted folds."""
    sizes = []
    for data, b2, _ in datas.values():
        folds = asset_folds(data, b2, horizon)
        sizes += [len(f.train) for k, f in enumerate(folds) if k % every == 0]
    return len(sizes), sum(sizes) / len(sizes), max(sizes)


def pooled_fits(datas, horizon, every):
    """Distinct pooled fit cutoffs (assets with the same fold dates share them) and their pooled row counts."""
    cutoffs = set()
    for data, b2, _ in datas.values():
        folds = asset_folds(data, b2, horizon)
        cutoffs |= {data.index[folds[k - k % every].origin] for k in range(len(folds))}
    frames = {a: (d, b2) for a, (d, b2, _) in datas.items()}
    sizes = [sum(len(s) for s in pooled_train_sets(frames, c, horizon).values()) for c in cutoffs]
    return len(cutoffs), sum(sizes) / len(sizes), max(sizes), max(cutoffs)


def main() -> None:
    require_snapshot()
    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata(),
           "host": {"platform": platform.platform(), "cpu_count": os.cpu_count(),
                    "torch_threads": lstm.SETTINGS["threads"]}, "horizons": {}}
    for h in config.FORECAST_HORIZONS:
        datas = {a: load_dev(a, h) for a in config.ASSETS}
        data, b2, _ = datas["btc"]
        last = asset_folds(data, b2, h)[-1]
        train, inputs = data.iloc[last.train], data.iloc[last.predict]
        sec = {}
        every_p = price_v2.refit_every_folds("prophet", h)
        n_p, mean_p, max_p = per_asset_fits(datas, h, every_p)
        for name in price_v2.PROPHET_CONFIGS:
            model, t_fit = _timed(lambda: price_v2.prophet_fit(train, name))
            _, t_pred = _timed(lambda: price_v2.prophet_predict(model, inputs, h))
            t = t_fit + t_pred
            sec[name] = {"largest_fold_train_rows": len(train), "fit_seconds": t_fit, "predict_seconds": t_pred,
                         "n_fits": n_p, "refit_every_folds": every_p, "projected_hours_upper": n_p * t / 3600,
                         "projected_hours_mean": n_p * t * mean_p / max_p / 3600}
        every_l = 1 if h == 30 else price_v2.PROPHET_REFIT_EVERY_ROWS_AT_7 // h
        n_l, mean_l, max_l, cutoff = pooled_fits(datas, h, every_l)
        sets = pooled_train_sets({a: (d, b) for a, (d, b, _) in datas.items()}, cutoff, h)
        for name in lstm.CONFIGS:
            model, t_fit = _timed(lambda: lstm.fit(sets, name, h))
            _, t_pred = _timed(lambda: lstm.predict(model, "btc", data, last.predict))
            t = t_fit + t_pred
            sec[name] = {"largest_fold_pooled_rows": max_l, "fit_seconds": t_fit, "predict_seconds": t_pred,
                         "epochs": model.epochs, "n_fits": n_l, "refit_every_folds": every_l,
                         "projected_hours_upper": n_l * t / 3600, "projected_hours_mean": n_l * t * mean_l / max_l / 3600}
        out["horizons"][f"h{h}"] = sec
        print(json.dumps({f"h{h}": sec}, indent=1), flush=True)
    total = {k: sum(v[k] for sec in out["horizons"].values() for v in sec.values())
             for k in ("projected_hours_upper", "projected_hours_mean")}
    out["projected_total_prophet_and_lstm"] = total
    path = ML_ROOT / "reports" / "timing_price_v2.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"total {total}\nwrote {path}")


if __name__ == "__main__":
    main()
