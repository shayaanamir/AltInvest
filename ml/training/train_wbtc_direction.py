# train_wbtc_direction.py
# WBTC DirectionClassifier standalone training script.
#
# Pipeline:
#   1. Load the three pre-split WBTC CSVs from ml/data/
#   2. Train DirectionClassifier via fit_presplit(train_df, val_df)
#      - target_return_30d is read directly from the CSV
#      - _compute_forward_return() is NEVER called (price is StandardScaled,
#        can be negative; log(price_fwd/price) would be NaN/garbage)
#      - THRESH = P40 of |target_return_30d| from training data only
#   3. Report: label distribution, val accuracy vs baseline, confusion matrix,
#              feature importances, per-class probability behaviour
#   4. Save ml/models/artifacts/wbtc_direction_clf.pkl
#
# Usage:
#   cd ml/
#   python training/train_wbtc_direction.py
#   python training/train_wbtc_direction.py --no-save

import sys
import json
import logging
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, accuracy_score

_ML_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ML_ROOT))

from models.direction_classifier import DirectionClassifier, DIRECTION_FEATURES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s -- %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("train_wbtc_direction")

DATA_DIR      = _ML_ROOT / "data"
ARTIFACTS_DIR = _ML_ROOT / "models" / "artifacts"
TRAIN_CSV     = DATA_DIR / "wbtc_train_model.csv"
VAL_CSV       = DATA_DIR / "wbtc_validation_model.csv"
TEST_CSV      = DATA_DIR / "wbtc_test_model.csv"


def main(no_save=False):
    sep = "=" * 62
    print()
    print(sep)
    print("  AltInvest -- WBTC DirectionClassifier Training")
    print(sep)

    # 1. Load CSVs
    log.info("Loading WBTC CSV splits ...")
    train_df = pd.read_csv(TRAIN_CSV)
    val_df   = pd.read_csv(VAL_CSV)
    test_df  = pd.read_csv(TEST_CSV)
    log.info("Train=%d  Val=%d  Test=%d rows", len(train_df), len(val_df), len(test_df))

    # 2. Data regime note
    # Val/test may have a narrow target_return_30d range (e.g. no UP labels).
    # This is a genuine regime difference, not a code error.
    print()
    print("  [Data Regime Note]")
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        lo = df["target_return_30d"].min()
        hi = df["target_return_30d"].max()
        mu = df["target_return_30d"].mean()
        print("    {:5s} target_return_30d: min={:.4f}  max={:.4f}  mean={:.4f}".format(
            name, lo, hi, mu))

    # 3. Train via fit_presplit
    log.info("Training DirectionClassifier via fit_presplit() ...")
    clf = DirectionClassifier()
    clf.fit_presplit(train_df, val_df, asset="wbtc")

    # 4. Diagnostics
    clf.print_diagnostics()

    # 5. Confusion matrix on val
    thresh  = clf._thresh
    val_tmp = val_df.copy()
    val_tmp["_direction"] = val_tmp["target_return_30d"].apply(
        lambda r: "UP" if r > thresh else ("DOWN" if r < -thresh else "FLAT")
    )
    X_val          = val_tmp[DIRECTION_FEATURES].values
    y_true_names   = val_tmp["_direction"].values
    y_pred_encoded = clf._model.predict(X_val)
    y_pred_names   = clf._encoder.inverse_transform(y_pred_encoded)

    present = sorted(set(y_true_names) | set(y_pred_names))
    cm = confusion_matrix(y_true_names, y_pred_names, labels=present)
    print()
    print("  [Confusion Matrix -- Val Split]  (rows=actual, cols=predicted)")
    print("          " + "  ".join("{:>6}".format(c) for c in present))
    for i, lbl in enumerate(present):
        print("  {:>6}  ".format(lbl) + "  ".join("{:>6d}".format(v) for v in cm[i]))

    # 6. Per-class probability behaviour
    proba  = clf._model.predict_proba(X_val)
    cnames = list(clf._encoder.classes_)
    print()
    print("  [Mean Predicted Probabilities by Actual Class -- Val]")
    prob_df = pd.DataFrame(proba, columns=cnames)
    prob_df["actual"] = y_true_names
    print(prob_df.groupby("actual")[cnames].mean().round(3).to_string())

    # 7. Save
    if not no_save:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        ap = ARTIFACTS_DIR / "wbtc_direction_clf.pkl"
        clf.save(ap)
        print()
        print("  Artifact saved -> " + str(ap))
    else:
        print()
        print("  [--no-save] Skipping artifact write (dry-run).")

    # 8. Summary
    val_acc  = accuracy_score(y_true_names, y_pred_names)
    baseline = float(pd.Series(y_true_names).value_counts(normalize=True).max())
    summary  = {
        "asset":          "wbtc",
        "thresh":         round(thresh, 4),
        "train_rows":     len(train_df),
        "val_rows":       len(val_df),
        "val_accuracy":   round(val_acc, 4),
        "val_baseline":   round(baseline, 4),
        "beats_baseline": val_acc > baseline,
    }
    print()
    print("  [Summary]")
    print(json.dumps(summary, indent=4))
    print(sep)
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Train WBTC DirectionClassifier")
    p.add_argument("--no-save", action="store_true", help="Skip artifact write")
    a = p.parse_args()
    main(no_save=a.no_save)
