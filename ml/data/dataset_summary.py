"""Build features, labels and splits for one asset and write the dataset summary (no models).

    python -m ml.data.dataset_summary --asset btc

Writes ml/reports/data/{asset}_dataset_summary.json. Refuses data whose validation report did not pass
(AGENTS rule 4). Thresholds are fitted on train only (D19).
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from ml import config
from ml.data.loader import load_raw
from ml.data.validate import ML_ROOT, REPORT_DIR
from ml.evaluation.splits import make_splits, split_dates
from ml.features.features import FEATURE_COLUMNS, build_features
from ml.labels.labels import DIRECTION_CLASSES, RISK_CLASSES, apply_thresholds, build_labels, fit_thresholds


def class_balance(classes, names) -> dict[str, float]:
    """Percent of labelled rows in each class."""
    c = classes.dropna()
    return {k: round(100 * float((c == k).mean()), 2) if len(c) else None for k in names}


def require_validated(asset: str) -> None:
    """AGENTS rule 4: never use data whose validation report did not pass."""
    validation = REPORT_DIR / f"{asset}_validation.json"
    if not validation.exists() or not json.loads(validation.read_text(encoding="utf-8"))["passed"]:
        sys.exit(f"{validation.relative_to(ML_ROOT.parent)} missing or not passed; run ml.data.validate first")


def prepare(asset: str) -> dict:
    """The one Phase 2 pipeline: raw -> features, labels, splits, train-only thresholds, classes."""
    raw = load_raw(asset)
    feats = build_features(raw)
    labels = build_labels(raw.set_index("timestamp")["close"]).loc[feats.index]
    splits = make_splits(len(feats))
    thresholds = fit_thresholds(labels.iloc[splits["train"]])
    classes = apply_thresholds(labels, thresholds)
    return {"raw": raw, "feats": feats, "labels": labels, "splits": splits,
            "thresholds": thresholds, "classes": classes}


def summarise(asset: str) -> dict:
    d = prepare(asset)
    raw, feats, labels, splits = d["raw"], d["feats"], d["labels"], d["splits"]
    thresholds, classes = d["thresholds"], d["classes"]
    dates = split_dates(feats.index, splits)

    per_split = {}
    for name, r in splits.items():
        lab = labels.iloc[r]
        cls = classes.iloc[r]
        per_split[name] = {
            "rows": len(r),
            "index_range": [r.start, r.stop],
            "first_date": dates[name]["first"],
            "last_date": dates[name]["last"],
            "labelled_rows": int(lab.notna().all(axis=1).sum()),
            "direction_balance_pct": class_balance(cls["direction"], DIRECTION_CLASSES),
            "risk_balance_pct": class_balance(cls["risk"], RISK_CLASSES),
        }
    return {
        "asset": asset,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_rows": len(raw),
        "warmup_rows_dropped": config.WARMUP_ROWS,
        "n_feature_rows": len(feats),
        "feature_columns": FEATURE_COLUMNS,
        "feature_nan_count": int(feats.isna().sum().sum()),
        "horizon_days": config.HORIZON_DAYS,
        "embargo_days": config.EMBARGO_DAYS,
        "thresholds": {
            "fitted_on": "train",
            "direction_flat_percentile": config.DIRECTION_FLAT_PERCENTILE,
            "risk_percentiles": list(config.RISK_PERCENTILES),
            **{k: round(v, 6) for k, v in thresholds.items()},
        },
        "splits": per_split,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dataset summary: features, labels, splits")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = summarise(asset)
    out = REPORT_DIR / f"{asset}_dataset_summary.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
