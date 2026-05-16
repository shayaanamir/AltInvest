"""
train.py
─────────────────────────────────────────────────────────────────────────────
Training Orchestrator — AltInvest ML Pipeline

Coordinates the full training pipeline for one asset in a single command:

    Step 1  LOAD       Load raw price CSV (mock or real — same code path)
    Step 2  FEATURES   Run feature engineering -> processed CSV
    Step 3  FORECAST   Fit Prophet forecaster  -> .pkl artifact + prediction
    Step 4  CLASSIFY   Fit RF risk classifier  -> .pkl artifact + risk label
    Step 5  REPORT     Write JSON training report to ml/models/artifacts/

Usage
-----
    python training/train.py --asset btc
    python training/train.py --asset eth
    python training/train.py --asset btc --skip-forecast   (classifier only)
    python training/train.py --asset btc --skip-classify   (forecaster only)
    python training/train.py --asset btc --dry-run         (no saves)

Output
------
    ml/models/artifacts/btc_prophet.pkl
    ml/models/artifacts/btc_rf_classifier.pkl
    ml/models/artifacts/btc_training_report.json

Training Report Schema
----------------------
    {
        "asset":       "btc",
        "trained_at":  "2024-01-01T00:00:00Z",
        "data": {
            "raw_rows":       17521,
            "feature_rows":   16801,
            "date_range":     ["2024-01-31", "2025-12-31"]
        },
        "forecast": {
            "asset":          "btc",
            "prediction_30d": 72450.50,
            "lower_bound":    68000.00,
            "upper_bound":    76000.00,
            "confidence":     0.78,
            "duration_sec":   12.4
        },
        "classify": {
            "asset":          "btc",
            "risk_label":     "medium",
            "risk_score":     67.5,
            "cv_accuracy":    0.83,
            "duration_sec":   8.1
        },
        "total_duration_sec": 22.5,
        "status": "success"
    }

Author : ML Engineer (Person C) — dev-shail branch
"""

import sys
import json
import time
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ─── Path setup ───────────────────────────────────────────────────────────────
_ML_ROOT = Path(__file__).resolve().parent.parent   # …/ml/
sys.path.insert(0, str(_ML_ROOT))

from features.feature_engineering import (
    load_raw_csv,
    build_features,
    run_pipeline as fe_run_pipeline,
)
from models.forecaster  import ProphetForecaster
from models.classifier  import RiskClassifier

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("train")

ARTIFACTS_DIR = _ML_ROOT / "models" / "artifacts"


# ══════════════════════════════════════════════════════════════════════════════
#  Step runners
# ══════════════════════════════════════════════════════════════════════════════

def step_load(asset: str) -> tuple[pd.DataFrame, dict]:
    """
    Step 1: Load raw CSV and run feature engineering.

    Returns
    -------
    (features_df, data_meta)
        features_df  — full feature-engineered DataFrame
        data_meta    — dict for training report
    """
    _banner(1, "LOAD + FEATURE ENGINEERING", asset)
    t0 = time.perf_counter()

    # 1a. Load raw
    raw_df = load_raw_csv(asset)
    log.info("[%s] Raw rows loaded: %d", asset.upper(), len(raw_df))

    # 1b. Feature engineering (also saves processed CSV)
    features_df = build_features(raw_df)
    asset_df    = features_df[features_df["asset"] == asset].copy()

    elapsed = time.perf_counter() - t0

    # Parse date range
    ts = pd.to_datetime(asset_df["timestamp"], utc=True)

    data_meta = {
        "raw_rows":     int(len(raw_df)),
        "feature_rows": int(len(asset_df)),
        "date_range":   [
            ts.min().strftime("%Y-%m-%d"),
            ts.max().strftime("%Y-%m-%d"),
        ],
        "duration_sec": round(elapsed, 2),
    }

    log.info(
        "[%s] Feature engineering complete: %d rows, %d cols in %.1fs",
        asset.upper(), len(asset_df), asset_df.shape[1], elapsed,
    )
    return asset_df, data_meta


def step_forecast(
    asset_df:  pd.DataFrame,
    asset:     str,
    dry_run:   bool = False,
) -> tuple[dict, dict]:
    """
    Step 2: Fit Prophet and generate 30-day prediction.

    Returns
    -------
    (prediction_dict, forecast_meta)
    """
    _banner(2, "PROPHET FORECASTER", asset)
    t0 = time.perf_counter()

    model = ProphetForecaster()
    model.fit(asset_df)
    prediction = model.predict()

    elapsed = time.perf_counter() - t0

    if not dry_run:
        model.save()

    forecast_meta = {**prediction, "duration_sec": round(elapsed, 2)}

    _print_result("Forecast", prediction)
    log.info("[%s] Prophet step done in %.1fs", asset.upper(), elapsed)
    return prediction, forecast_meta


def step_classify(
    asset_df:  pd.DataFrame,
    asset:     str,
    dry_run:   bool = False,
) -> tuple[dict, dict]:
    """
    Step 3: Fit RandomForest risk classifier.

    Returns
    -------
    (risk_dict, classify_meta)
    """
    _banner(3, "RISK CLASSIFIER", asset)
    t0 = time.perf_counter()

    clf = RiskClassifier()
    clf.fit(asset_df)
    risk = clf.predict_latest(asset_df)

    elapsed = time.perf_counter() - t0

    if not dry_run:
        clf.save()

    # Pull CV accuracy from the fitted model's internal report
    cv_accuracy = _extract_cv_accuracy(clf)

    classify_meta = {
        **risk,
        "cv_accuracy":  cv_accuracy,
        "duration_sec": round(elapsed, 2),
    }

    _print_result("Risk", risk)
    log.info("[%s] Classifier step done in %.1fs", asset.upper(), elapsed)
    return risk, classify_meta


def step_report(
    asset:         str,
    data_meta:     dict,
    forecast_meta: Optional[dict],
    classify_meta: Optional[dict],
    total_elapsed: float,
    dry_run:       bool = False,
) -> dict:
    """
    Step 4: Assemble and save the training report JSON.

    Returns
    -------
    report dict
    """
    _banner(4, "TRAINING REPORT", asset)

    report = {
        "asset":      asset,
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data":       data_meta,
        "forecast":   forecast_meta,
        "classify":   classify_meta,
        "total_duration_sec": round(total_elapsed, 2),
        "status":     "success",
    }

    if not dry_run:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = ARTIFACTS_DIR / f"{asset}_training_report.json"
        report_path.write_text(json.dumps(report, indent=2))
        log.info("[%s] Training report saved -> %s", asset.upper(), report_path)

    return report


# ══════════════════════════════════════════════════════════════════════════════
#  Main orchestrator
# ══════════════════════════════════════════════════════════════════════════════

def run_training(
    asset:          str,
    skip_forecast:  bool = False,
    skip_classify:  bool = False,
    dry_run:        bool = False,
) -> dict:
    """
    Full training pipeline for a single asset.

    Parameters
    ----------
    asset          : "btc" or "eth"
    skip_forecast  : skip Prophet step (useful when retraining classifier only)
    skip_classify  : skip RF classifier step
    dry_run        : run all steps but do not write any files

    Returns
    -------
    dict  — complete training report
    """
    pipeline_start = time.perf_counter()

    _print_header(asset, dry_run)

    report_data    = {}
    forecast_meta  = None
    classify_meta  = None

    try:
        # ── Step 1: Load + Feature Engineering ────────────────────────────
        asset_df, data_meta = step_load(asset)

        # ── Step 2: Prophet Forecaster ─────────────────────────────────────
        if not skip_forecast:
            _, forecast_meta = step_forecast(asset_df, asset, dry_run=dry_run)
        else:
            log.info("[%s] Skipping forecast step (--skip-forecast)", asset.upper())

        # ── Step 3: Risk Classifier ────────────────────────────────────────
        if not skip_classify:
            _, classify_meta = step_classify(asset_df, asset, dry_run=dry_run)
        else:
            log.info("[%s] Skipping classify step (--skip-classify)", asset.upper())

        # ── Step 4: Training Report ────────────────────────────────────────
        total_elapsed = time.perf_counter() - pipeline_start
        report = step_report(
            asset=asset,
            data_meta=data_meta,
            forecast_meta=forecast_meta,
            classify_meta=classify_meta,
            total_elapsed=total_elapsed,
            dry_run=dry_run,
        )

    except Exception as exc:
        elapsed = time.perf_counter() - pipeline_start
        log.error("[%s] Training FAILED after %.1fs: %s", asset.upper(), elapsed, exc)
        raise

    _print_footer(report, dry_run)
    return report


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _banner(step: int, name: str, asset: str) -> None:
    log.info("")
    log.info("--- Step %d: %s [%s] ---", step, name, asset.upper())


def _print_header(asset: str, dry_run: bool) -> None:
    sep = "=" * 62
    mode = "  [DRY RUN — no files will be written]" if dry_run else ""
    print(f"\n{sep}")
    print(f"  AltInvest Training Orchestrator{mode}")
    print(f"  Asset   : {asset.upper()}")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)


def _print_footer(report: dict, dry_run: bool) -> None:
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  Training complete in {report['total_duration_sec']:.1f}s")
    if report.get("forecast"):
        fc = report["forecast"]
        print(f"  Forecast  : ${fc['prediction_30d']:,.2f}"
              f"  [{fc['lower_bound']:,.0f} – {fc['upper_bound']:,.0f}]"
              f"  conf={fc['confidence']}")
    if report.get("classify"):
        cl = report["classify"]
        print(f"  Risk      : {cl['risk_label'].upper()}"
              f"  (score={cl['risk_score']},"
              f"  cv_acc={cl.get('cv_accuracy', 'N/A')})")
    if not dry_run:
        print(f"  Artifacts : ml/models/artifacts/")
    print(sep)


def _print_result(label: str, result: dict) -> None:
    print(f"\n  [{label} Result]")
    for k, v in result.items():
        print(f"    {k:<18}: {v}")


def _extract_cv_accuracy(clf: RiskClassifier) -> Optional[float]:
    """
    Best-effort extraction of CV accuracy from the classifier's eval report.
    Returns None if unavailable (graceful degradation for the report).
    """
    try:
        # The eval report string contains 'accuracy   x.xx'
        if clf._eval_report:
            for line in clf._eval_report.split("\n"):
                if "accuracy" in line and "macro" not in line:
                    parts = line.split()
                    for part in parts:
                        try:
                            val = float(part)
                            if 0.0 < val <= 1.0:
                                return round(val, 3)
                        except ValueError:
                            continue
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  —  python training/train.py --asset btc
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AltInvest ML Training Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python training/train.py --asset btc\n"
            "  python training/train.py --asset eth\n"
            "  python training/train.py --asset btc --skip-forecast\n"
            "  python training/train.py --asset btc --dry-run\n"
        ),
    )
    parser.add_argument(
        "--asset", choices=["btc", "eth"], required=True,
        help="Asset to train models for"
    )
    parser.add_argument(
        "--skip-forecast", action="store_true",
        help="Skip Prophet forecaster step"
    )
    parser.add_argument(
        "--skip-classify", action="store_true",
        help="Skip RandomForest classifier step"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run full pipeline but write no files to disk"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_training(
        asset=args.asset,
        skip_forecast=args.skip_forecast,
        skip_classify=args.skip_classify,
        dry_run=args.dry_run,
    )
