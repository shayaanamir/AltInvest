"""Phase 10 step 10.6b: walk-forward of the fair-value baselines and candidates (D76 as amended).

    python -m ml.evaluation.run_nft_fair_value

Writes ml/reports/nft/walkforward_fair_value.json (and the per-row predictions as walkforward_fair_value_rows.parquet).
Development data only (ml.nft.item_data.load_dev); nothing dated on or after 2026-01-25 is read. Per fold
(nft_fv_protocol.folds): training rows = clean as of the fold's training cutoff, test rows = clean as of
2026-01-25 (fv_features.clean_mask); B0, B1, B2 and the 6 candidates of ml/models/nft_fair_value.py, each with
its 80% range (quantile predictions sorted per row). Selection: nft_fv_protocol.select (top-only, D32, D44).
Descriptive tables (MdAPE by collection, sale_type, floor-age bucket; feature importances) select nothing.
"""

import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation import nft_fv_protocol as proto
from ml.gitinfo import git_metadata
from ml.models import nft_fair_value as fvm
from ml.nft import fv_features as fv
from ml.nft import fv_leakage, item_data, snapshot

REPORT = ML_ROOT / "reports" / "nft" / "walkforward_fair_value.json"
ROWS = ML_ROOT / "reports" / "nft" / "walkforward_fair_value_rows.parquet"
AGE_BUCKETS = [0, 6, 12, 24, 72, np.inf]                 # floor_age_hours, descriptive only
AGE_LABELS = ["0-6h", "6-12h", "12-24h", "24-72h", ">72h"]


def _importance(models: dict) -> pd.Series:
    """Gain share per feature, summed over a candidate's boosters (one per collection when per collection)."""
    s = pd.concat([pd.Series(m.feature_importance("gain"), index=m.feature_name()) for m in models.values()])
    s = s.groupby(level=0).sum()
    return s / s.sum()


def run_fold(f: dict, feats: pd.DataFrame, sales: pd.DataFrame, tcols: list, id_like: dict) -> tuple:
    train_m, test_m = proto.fold_rows(feats, f)
    train_m &= fv.clean_mask(feats, sales, int(f["train_end"].timestamp()))
    test_m &= feats["clean"].to_numpy(bool)
    train, test = feats[train_m], feats[test_m]
    assert train["timestamp"].max() < int(f["train_end"].timestamp()) <= test["timestamp"].min() - 7 * 86400
    out = test[["hid", "slug", "date", "y", "floor_age_hours", "sale_type"]].assign(fold=f["fold"], part=f["part"])
    for name, fn in fvm.BASELINE_FNS.items():
        y_hat, lo, hi = fn(train, test)
        out[f"pred:{name}"], out[f"lo:{name}"], out[f"hi:{name}"] = y_hat, lo, hi
    qcache, imp, crossed = {}, {}, {}
    for name in fvm.NAMES:
        models = {}
        out[f"pred:{name}"] = fvm.fit_predict(name, train, test, tcols, id_like, models=models)
        imp[name] = _importance(models)
        key = fvm.range_key(name)
        if key not in qcache:
            q = [fvm.fit_predict(name, train, test, tcols, id_like, quantile=a) for a in fvm.QUANTILES]
            qcache[key] = fvm.ordered_range(*q)
        out[f"lo:{name}"], out[f"hi:{name}"], crossed[name] = qcache[key]
    for name in list(fvm.BASELINE_FNS) + fvm.NAMES:
        out[f"ape:{name}"] = proto.ape(out[f"pred:{name}"], out["y"])
    info = {"fold": f["fold"], "part": f["part"], "train_cutoff": str(f["train_end"].date()),
            "test": [str(f["test_start"].date()), str(f["test_end"].date())], "n_train": int(train_m.sum()),
            "n_test": int(test_m.sum()), "train_dates": [train["date"].min(), train["date"].max()],
            "test_dates": [test["date"].min(), test["date"].max()], "quantile_rows_crossed": crossed}
    return out, imp, info


def _mdape_by(rows: pd.DataFrame, key: str, names: list) -> dict:
    return {str(k): {"n": len(g), **{n: float(np.median(g[f"ape:{n}"])) for n in names}}
            for k, g in rows.groupby(key, observed=True)}


def descriptive(rows: pd.DataFrame, names: list) -> dict:
    rows = rows.assign(floor_age_bucket=pd.cut(rows["floor_age_hours"], AGE_BUCKETS, labels=AGE_LABELS, right=False))
    out = {}
    for part, sub in {"all_folds": rows, "ranking": rows[rows["part"] == "rank"],
                      "confirmation": rows[rows["part"] == "confirm"]}.items():
        out[part] = {"by_collection": _mdape_by(sub, "slug", names), "by_sale_type": _mdape_by(sub, "sale_type", names),
                     "by_floor_age_bucket": _mdape_by(sub, "floor_age_bucket", names)}
    out["by_fold"] = _mdape_by(rows, "fold", names)
    return out


def main() -> None:
    git = git_metadata()
    t0 = time.perf_counter()
    p = fv_leakage.prepare()
    feats, sales = p["features"], p["dev"]["sales"]
    feats["y"] = feats["premium"]
    st = sales[["slug", "tx", "token_id", "sale_type"]]                        # descriptive only, never a feature
    feats["sale_type"] = feats[["slug", "tx", "token_id"]].merge(st, how="left")["sale_type"].to_numpy()
    traits = p["dev"]["traits"]
    id_like = {s: list(v) for s, v in traits[traits["id_like"]].groupby("slug")["trait_type"].unique().items()}
    parts, imps, infos = [], {n: [] for n in fvm.NAMES}, []
    for f in proto.folds():
        tf = time.perf_counter()
        out, imp, info = run_fold(f, feats, sales, p["trait_cols"], id_like)
        parts.append(out)
        infos.append({**info, "seconds": round(time.perf_counter() - tf, 1)})
        for n in fvm.NAMES:
            imps[n].append(imp[n])
        print(f"fold {f['fold']} done in {infos[-1]['seconds']} s", flush=True)
    rows = pd.concat(parts, ignore_index=True)
    names = list(proto.BASELINES) + fvm.NAMES
    importance = {n: pd.concat(v, axis=1).fillna(0).mean(axis=1).sort_values(ascending=False) for n, v in imps.items()}
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git,
        "step": "10.6b", "decision": "D76 (as amended 2026-11-14)",
        "item_snapshot": config.NFT_ITEM_SNAPSHOT_V3, "item_manifest_sha256": item_data.require(),
        "base_manifest_sha256": snapshot.require_snapshot("floor_points", "eth_usd"),
        "data": {"dev_end_exclusive": "2026-01-25", "last_row_date": str(feats["date"].max()),
                 "history_rows": len(feats), "test_rows_pooled": len(rows),
                 "test_date_range": [rows["date"].min(), rows["date"].max()]},
        "trial_count": fvm.TRIAL_COUNT, "candidates": fvm.declared(), "baselines": list(proto.BASELINES),
        "metric": "MdAPE = median |exp(y_hat - y) - 1| (price), pooled over collections",
        "bootstrap": {"block_days": proto.BLOCK_DAYS, "n_boot": proto.N_BOOT, "seed": proto.SEED},
        "folds": infos, "selection": proto.select(rows, fvm.NAMES), "descriptive": descriptive(rows, names),
        "feature_importance_gain_share_mean_over_folds": {n: {k: float(v) for k, v in s.head(25).items()}
                                                          for n, s in importance.items()},
        "wall_seconds": round(time.perf_counter() - t0, 1),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    rows.to_parquet(ROWS, index=False, compression="zstd")
    print(f"wrote {REPORT} and {ROWS}")


if __name__ == "__main__":
    main()
