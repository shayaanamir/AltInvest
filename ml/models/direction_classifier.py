"""
direction_classifier.py
─────────────────────────────────────────────────────────────────────────────
RandomForest-based 30-day price direction classifier for AltInvest.

Design
------
- Input  : feature-engineered DataFrame from feature_engineering.build_features()
- Output : direction classification dict

Output contract:
    {
        "asset":         "BTC",
        "prob_up_30d":   0.72,     # P(price rises > THRESH in next 30 days)
        "prob_flat_30d": 0.18,     # P(price stays within THRESH in next 30 days)
        "prob_down_30d": 0.10,     # P(price falls > THRESH in next 30 days)
        "direction":     "UP",     # argmax of above
        "thresh":        0.0984,   # per-asset threshold used (from Phase 0)
    }

Labeling Strategy
-----------------
Labels are based on FORWARD LOG-RETURN over the next 30 days (720 hours),
strictly after each observation row:

    target_return_30d_t = ln(price_{t+720} / price_t)

This is NOT stored in any CSV — it is computed ephemerally inside .fit().
The existing `return_30d` feature is a TRAILING log-return (backward-looking)
and is safe to use as a model input.

The dead-zone threshold (THRESH) is determined by the Phase 0 pre-committed
decision rule — specifically Option A, the P40 of |target_return_30d| computed
from the TRAINING split only. Results from Phase 0:

    BTC: THRESH = 0.0984  (±9.84%)
    ETH: THRESH = 0.0892  (±8.92%)
    SOL: THRESH = 0.1355  (±13.55%)

Labels:
    +1 (UP)   if target_return_30d >  +THRESH
     0 (FLAT) if target_return_30d in [-THRESH, +THRESH]
    -1 (DOWN) if target_return_30d <  -THRESH

Leakage-Prevention
------------------
Identical discipline to classifier.py's RiskClassifier:
  - Forward label computed via reverse-rolling trick (no look-ahead)
  - Final 720 rows dropped (no forward label available)
  - Chronological 80/20 split with 720-hour embargo (horizon-matched)
  - THRESH computed from TRAINING split ONLY, stored in artifact
  - TimeSeriesSplit(n_splits=5, gap=720) CV on training data only

Architecture
------------
    DirectionClassifier
        .fit(df)             — label + train RandomForest  (BTC/ETH/SOL path)
        .fit_presplit(       — WBTC path: accepts pre-split, pre-labeled DFs
            train_df,          reads target_return_30d directly, skips
            val_df)            internal auto-split/embargo logic entirely
        .predict(df)         — classify latest market state
        .predict_latest(df)  — shortcut: predict on most recent row
        .save(path)          — persist to disk
        .load(path)          — restore from disk
        .feature_importances — dict of feature -> importance

Usage
-----
    from models.direction_classifier import DirectionClassifier
    from features.feature_engineering import load_raw_csv, build_features

    df = build_features(load_raw_csv("btc"))
    clf = DirectionClassifier()
    clf.fit(df)
    result = clf.predict_latest(df)
    # -> {"asset": "BTC", "prob_up_30d": 0.72, "prob_flat_30d": 0.18,
    #     "prob_down_30d": 0.10, "direction": "UP", "thresh": 0.0984}

WBTC (pre-split) usage
----------------------
    train_df = pd.read_csv("ml/data/wbtc_train_model.csv")
    val_df   = pd.read_csv("ml/data/wbtc_validation_model.csv")
    clf = DirectionClassifier()
    clf.fit_presplit(train_df, val_df)
    # IMPORTANT: the WBTC price column is StandardScaled (can be negative), so
    # _compute_forward_return() is NEVER called on WBTC data.
    # target_return_30d from the CSV is the SOLE label source.
    # Do NOT pass WBTC DataFrames to the regular .fit() path.

CLI:
    python -m models.direction_classifier --asset btc
    python -m models.direction_classifier --asset eth --no-save

Author : ML Engineer (Person C) — dev-shail branch
"""

import sys
import json
import pickle
import logging
import argparse
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

warnings.filterwarnings("ignore")

# ─── Project imports ──────────────────────────────────────────────────────────
_ML_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ML_ROOT))

from features.feature_engineering import (
    load_raw_csv,
    build_features,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("direction_classifier")

# ─── Constants ────────────────────────────────────────────────────────────────
MODEL_DIR              = _ML_ROOT / "models" / "artifacts"
DIRECTION_LABELS       = ["DOWN", "FLAT", "UP"]   # ordered: -1 -> 0 -> +1
FORWARD_HORIZON_HOURS  = 24 * 30                   # 720 hours = 30 days
EMBARGO_HOURS          = FORWARD_HORIZON_HOURS     # horizon-matched embargo

# Feature columns (same as RiskClassifier — already verified leakage-free)
DIRECTION_FEATURES = [
    "return_1h",
    "return_1d",
    "return_7d",
    "return_30d",
    "volatility_14d",
    "ma_cross",
    "volume_change_pct",
]

# RandomForest hyperparameters (same as RiskClassifier for consistency)
RF_PARAMS = {
    "n_estimators":     300,
    "max_depth":        8,
    "min_samples_leaf": 10,
    "class_weight":     "balanced",
    "random_state":     42,
    "n_jobs":           -1,
}

# Phase 0 pre-committed thresholds (P40 of |fwd_return| on training split)
# These are stored here as documentation; .fit() recomputes from training data.
PHASE0_THRESHOLDS = {
    "btc": 0.0984,
    "eth": 0.0892,
    "sol": 0.1355,
}


# ══════════════════════════════════════════════════════════════════════════════
#  DirectionClassifier
# ══════════════════════════════════════════════════════════════════════════════

class DirectionClassifier:
    """
    RandomForest direction classifier for crypto assets.

    Predicts whether the asset price will be UP, FLAT, or DOWN in 30 days,
    relative to a per-asset threshold derived from the Phase 0 analysis.

    Parameters
    ----------
    rf_params : dict
        RandomForestClassifier kwargs. Defaults to RF_PARAMS.
    """

    def __init__(self, rf_params: dict = None):
        self._rf_params = rf_params or RF_PARAMS

        self._model:       Optional[RandomForestClassifier] = None
        self._encoder:     Optional[LabelEncoder]           = None
        self._asset:       Optional[str]                    = None
        self._thresh:      Optional[float]                  = None   # per-asset THRESH
        self._eval_report: Optional[str]                    = None
        self._calibration: Optional[dict]                   = None

    # ── Public interface ───────────────────────────────────────────────────────

    @property
    def is_fitted(self) -> bool:
        return self._model is not None

    @property
    def feature_importances(self) -> dict:
        """Return feature -> importance mapping (sorted descending)."""
        if not self.is_fitted:
            raise RuntimeError("Call .fit() first.")
        importances = self._model.feature_importances_
        return dict(sorted(
            zip(DIRECTION_FEATURES, importances),
            key=lambda x: x[1], reverse=True,
        ))

    def fit(self, df: pd.DataFrame) -> "DirectionClassifier":
        """
        Label data and train the RandomForest direction classifier.

        Steps:
            1. Validate input
            2. Compute forward 30d log-return per row (720h ahead, strictly after t)
            3. Drop rows with no forward label (~720 final rows)
            4. Chronological 80/20 split with 720h embargo
            5. Compute THRESH from TRAINING data only (P40 of |fwd_return|)
               — Phase 0 Option A: per-asset data-driven threshold
            6. Assign UP/FLAT/DOWN labels using fixed THRESH
            7. Fit RandomForest on training data
            8. Evaluate: TimeSeriesSplit CV, test-set report, sanity check

        Parameters
        ----------
        df : pd.DataFrame
            Output of feature_engineering.build_features(). Single-asset only.

        Returns
        -------
        self
        """
        _validate_input(df)
        asset = df["asset"].iloc[0].lower()
        self._asset = asset
        log.info("[%s] Starting DirectionClassifier fit ...", asset.upper())

        # 1. Compute forward 30d log-return (no look-ahead)
        df = df.copy()
        df["_fwd_return_30d"] = _compute_forward_return(df)

        # 2. Drop rows with no forward label (final FORWARD_HORIZON_HOURS rows)
        n_before = len(df)
        df = df.dropna(subset=["_fwd_return_30d"]).reset_index(drop=True)
        n_dropped = n_before - len(df)
        log.info(
            "[%s] Dropped %d rows with no forward label (need %dh of future data). "
            "Remaining: %d rows.",
            asset.upper(), n_dropped, FORWARD_HORIZON_HOURS, len(df),
        )

        # 3. Chronological split with embargo (horizon-matched)
        split_idx = int(len(df) * 0.80)
        train_end = split_idx - EMBARGO_HOURS

        if train_end <= 0:
            raise ValueError(
                f"[{asset.upper()}] Dataset too small for training split after embargo. "
                f"Need at least {EMBARGO_HOURS + 100} labeled rows."
            )

        train_df      = df.iloc[:train_end].copy()
        test_df_full  = df.iloc[split_idx:].copy()

        log.info(
            "[%s] Split: train=%d rows (idx 0..%d), embargo=%d rows skipped, "
            "test=%d rows (idx %d..%d)",
            asset.upper(), len(train_df), train_end - 1, EMBARGO_HOURS,
            len(test_df_full), split_idx, len(df) - 1,
        )

        # 4. Compute THRESH from TRAINING data only (Phase 0 Option A)
        #    P40 of absolute forward returns on training split
        thresh = float(np.abs(train_df["_fwd_return_30d"]).quantile(0.40))
        self._thresh = thresh

        # Cross-check against Phase 0 documented values
        doc_thresh = PHASE0_THRESHOLDS.get(asset)
        if doc_thresh is not None:
            delta = abs(thresh - doc_thresh)
            if delta > 0.01:
                log.warning(
                    "[%s] Computed thresh %.4f differs from Phase 0 doc value %.4f "
                    "(delta=%.4f) — this is expected if data was regenerated.",
                    asset.upper(), thresh, doc_thresh, delta,
                )
            else:
                log.info(
                    "[%s] THRESH=%.4f matches Phase 0 doc value %.4f (delta=%.4f) OK",
                    asset.upper(), thresh, doc_thresh, delta,
                )
        log.info("[%s] THRESH (P40 of |fwd_return|, training only): %.4f", asset.upper(), thresh)

        # 5. Label both sets using fixed THRESH
        train_df["_direction"]    = train_df["_fwd_return_30d"].apply(
            lambda r: _return_to_label(r, thresh)
        )
        test_df_full["_direction"] = test_df_full["_fwd_return_30d"].apply(
            lambda r: _return_to_label(r, thresh)
        )

        train_dist = train_df["_direction"].value_counts().to_dict()
        test_dist  = test_df_full["_direction"].value_counts().to_dict()
        log.info("[%s] Training label distribution: %s", asset.upper(), train_dist)
        log.info("[%s] Test label distribution:     %s", asset.upper(), test_dist)

        # 6. Build X, y
        X_train = train_df[DIRECTION_FEATURES].values
        X_test  = test_df_full[DIRECTION_FEATURES].values

        self._encoder = LabelEncoder()
        self._encoder.fit(DIRECTION_LABELS)   # fixed class order: DOWN, FLAT, UP

        y_train = self._encoder.transform(train_df["_direction"].values)
        y_test  = self._encoder.transform(test_df_full["_direction"].values)

        log.info(
            "[%s] Train: %d rows | Test: %d rows",
            asset.upper(), len(X_train), len(X_test),
        )

        # 7. Fit RandomForest
        self._model = RandomForestClassifier(**self._rf_params)
        self._model.fit(X_train, y_train)

        # 8a. Train accuracy
        y_train_pred = self._model.predict(X_train)
        train_acc    = accuracy_score(y_train, y_train_pred)
        log.info("[%s] Train accuracy: %.3f", asset.upper(), train_acc)

        # 8b. Test accuracy + classification report
        y_pred   = self._model.predict(X_test)
        test_acc = accuracy_score(y_test, y_pred)

        self._eval_report = classification_report(
            y_test, y_pred,
            target_names=self._encoder.classes_,
            zero_division=0,
        )
        log.info("[%s] Test accuracy:  %.3f", asset.upper(), test_acc)

        # 8c. TimeSeriesSplit CV (training data only, gap = EMBARGO_HOURS)
        tscv = TimeSeriesSplit(
            n_splits=5,
            gap=EMBARGO_HOURS,
        )
        cv_scores = cross_val_score(
            self._model, X_train, y_train,
            cv=tscv, scoring="accuracy", n_jobs=-1,
        )
        log.info(
            "[%s] TimeSeriesSplit CV Accuracy: %.3f (+/- %.3f)",
            asset.upper(), cv_scores.mean(), cv_scores.std(),
        )

        # 8d. Sanity check: mean actual forward return by predicted class
        #     UP-predicted rows should have higher mean forward return than DOWN-predicted
        sanity_df = pd.DataFrame({
            "predicted_label": self._encoder.inverse_transform(y_pred),
            "actual_fwd_return": test_df_full["_fwd_return_30d"].values,
        })
        group_means = sanity_df.groupby("predicted_label")["actual_fwd_return"].mean()
        log.info(
            "[%s] Mean actual 30d return by predicted class:\n%s",
            asset.upper(),
            group_means.reindex(["UP", "FLAT", "DOWN"]).to_string(),
        )

        mean_up   = group_means.get("UP",   float("nan"))
        mean_down = group_means.get("DOWN", float("nan"))
        if pd.notna(mean_up) and pd.notna(mean_down):
            if mean_up > mean_down:
                log.info(
                    "[%s] SANITY CHECK PASSED: mean(UP)=%.4f > mean(DOWN)=%.4f",
                    asset.upper(), mean_up, mean_down,
                )
            else:
                log.warning(
                    "[%s] SANITY CHECK FAILED: mean(UP)=%.4f <= mean(DOWN)=%.4f "
                    "— UP-predicted class does NOT have higher actual forward returns!",
                    asset.upper(), mean_up, mean_down,
                )

        # 8e. Summary
        log.info(
            "[%s] -- FIT SUMMARY --\n"
            "  Rows dropped (no forward label) : %d\n"
            "  THRESH (P40 of |fwd_return|)     : %.4f\n"
            "  Training label distribution      : %s\n"
            "  Test label distribution          : %s\n"
            "  Train accuracy                   : %.3f\n"
            "  Test accuracy                    : %.3f\n"
            "  TimeSeriesSplit CV accuracy       : %.3f (+/- %.3f)",
            asset.upper(),
            n_dropped, thresh,
            train_dist, test_dist,
            train_acc, test_acc,
            cv_scores.mean(), cv_scores.std(),
        )

        log.info("[%s] Fit complete.", asset.upper())
        return self

    def fit_presplit(
        self,
        train_df: pd.DataFrame,
        val_df:   pd.DataFrame,
        asset:    str = "wbtc",
    ) -> "DirectionClassifier":
        """
        WBTC-specific fit path for pre-split, pre-labeled DataFrames.

        This method bypasses the internal 80/20 chronological auto-split and
        the 720-hour embargo logic in .fit(), which are incompatible with
        pre-assembled CSV splits.  It reads ``target_return_30d`` directly
        from each DataFrame as the label source.

        *** IMPORTANT ***
        The WBTC ``price`` column is StandardScaled and can be negative.
        ``_compute_forward_return()`` (which calls log(price_fwd / price))
        is NEVER called here.  Doing so would produce NaN or garbage output.
        The ``target_return_30d`` column is the sole ground truth.

        Parameters
        ----------
        train_df : pd.DataFrame
            WBTC training split CSV loaded as-is.
            Must contain DIRECTION_FEATURES and ``target_return_30d``.
        val_df : pd.DataFrame
            WBTC validation split CSV loaded as-is.
            Used only for evaluation — NOT for any threshold decisions.
        asset : str
            Asset name tag, default ``"wbtc"``.

        Returns
        -------
        self
        """
        _validate_presplit_input(train_df, "train_df")
        _validate_presplit_input(val_df,   "val_df")

        self._asset = asset.lower()
        log.info("[%s] Starting DirectionClassifier.fit_presplit() ...", self._asset.upper())
        log.info("[%s] Train rows: %d | Val rows: %d",
                 self._asset.upper(), len(train_df), len(val_df))

        train_df = train_df.copy()
        val_df   = val_df.copy()

        # ── 1. Compute THRESH from TRAINING data only (P40 of |target_return_30d|)
        #    This mirrors the Phase 0 Option-A decision rule used in .fit().
        #    THRESH is derived strictly from train_df; val_df is never touched here.
        thresh = float(np.abs(train_df["target_return_30d"]).quantile(0.40))
        self._thresh = thresh
        log.info("[%s] THRESH (P40 of |target_return_30d|, training only): %.4f",
                 self._asset.upper(), thresh)

        # ── 2. Label both splits using the fixed training THRESH
        train_df["_direction"] = train_df["target_return_30d"].apply(
            lambda r: _return_to_label(r, thresh)
        )
        val_df["_direction"] = val_df["target_return_30d"].apply(
            lambda r: _return_to_label(r, thresh)
        )

        train_dist = train_df["_direction"].value_counts().to_dict()
        val_dist   = val_df["_direction"].value_counts().to_dict()
        log.info("[%s] Training label distribution: %s", self._asset.upper(), train_dist)
        log.info("[%s] Val label distribution:     %s",  self._asset.upper(), val_dist)

        # Warn if val split lacks any class — this is a regime/data limitation,
        # not a code bug.  It means the evaluation is restricted to present classes.
        missing_in_val = set(DIRECTION_LABELS) - set(val_dist.keys())
        if missing_in_val:
            log.warning(
                "[%s] Val split is missing classes: %s  "
                "(target_return_30d range in val: [%.4f, %.4f]).  "
                "This is a regime shift in the data, not a code error.  "
                "Metrics on val will only cover present classes.",
                self._asset.upper(), missing_in_val,
                val_df["target_return_30d"].min(),
                val_df["target_return_30d"].max(),
            )

        # ── 3. Build X, y
        X_train = train_df[DIRECTION_FEATURES].values
        X_val   = val_df[DIRECTION_FEATURES].values

        # LabelEncoder must be fitted on ALL possible labels so class order is
        # stable even if a class is absent from one split.
        self._encoder = LabelEncoder()
        self._encoder.fit(DIRECTION_LABELS)   # fixed order: DOWN, FLAT, UP

        y_train = self._encoder.transform(train_df["_direction"].values)
        y_val   = self._encoder.transform(val_df["_direction"].values)

        # ── 4. Fit RandomForest on training data only
        self._model = RandomForestClassifier(**self._rf_params)
        self._model.fit(X_train, y_train)
        log.info("[%s] RandomForest fitted on %d training samples.",
                 self._asset.upper(), len(X_train))

        # ── 5a. Train accuracy
        y_train_pred = self._model.predict(X_train)
        train_acc    = accuracy_score(y_train, y_train_pred)
        log.info("[%s] Train accuracy: %.3f", self._asset.upper(), train_acc)

        # ── 5b. Val accuracy + classification report
        y_val_pred = self._model.predict(X_val)
        val_acc    = accuracy_score(y_val, y_val_pred)

        # classes_ contains only labels present in y_train; use inverse_transform
        # for the report so it matches the actual label names from the encoder.
        present_labels = sorted(set(y_val.tolist()) | set(y_val_pred.tolist()))
        present_names  = self._encoder.inverse_transform(present_labels)

        self._eval_report = classification_report(
            y_val, y_val_pred,
            labels=present_labels,
            target_names=present_names,
            zero_division=0,
        )
        log.info("[%s] Val accuracy:   %.3f", self._asset.upper(), val_acc)

        # ── 5c. Majority-class baseline on val
        majority_class_encoded = int(
            pd.Series(y_train).value_counts().idxmax()
        )
        baseline_pred = np.full_like(y_val, majority_class_encoded)
        baseline_acc  = accuracy_score(y_val, baseline_pred)
        majority_name = self._encoder.inverse_transform([majority_class_encoded])[0]
        log.info(
            "[%s] Majority-class baseline (always predict '%s'): val_acc=%.3f",
            self._asset.upper(), majority_name, baseline_acc,
        )
        if val_acc > baseline_acc:
            log.info(
                "[%s] Model BEATS majority-class baseline by %.3f",
                self._asset.upper(), val_acc - baseline_acc,
            )
        else:
            log.warning(
                "[%s] Model does NOT beat majority-class baseline "
                "(model=%.3f, baseline=%.3f). "
                "Consider whether the model provides useful information.",
                self._asset.upper(), val_acc, baseline_acc,
            )

        # ── 5d. TimeSeriesSplit CV on training data only
        #    For the WBTC pre-split path the training set is small relative to
        #    the EMBARGO_HOURS gap.  Compute the minimum samples needed:
        #      min_samples = n_splits * (test_size + gap)
        #    where test_size ~ n_train / (n_splits + 1).
        #    We try n_splits=3 first; if infeasible, skip CV with a clear message.
        n_splits = 3
        min_test = len(X_train) // (n_splits + 1)
        min_needed = n_splits * (min_test + EMBARGO_HOURS)
        if len(X_train) >= min_needed and min_test > 0:
            tscv = TimeSeriesSplit(n_splits=n_splits, gap=EMBARGO_HOURS)
            cv_scores = cross_val_score(
                self._model, X_train, y_train,
                cv=tscv, scoring="accuracy", n_jobs=-1,
            )
            log.info(
                "[%s] TimeSeriesSplit CV Accuracy (n=%d): %.3f (+/- %.3f)",
                self._asset.upper(), n_splits, cv_scores.mean(), cv_scores.std(),
            )
        else:
            log.warning(
                "[%s] CV skipped: dataset too small for TimeSeriesSplit(n=%d, gap=%d) "
                "(need >= %d rows, have %d). "
                "The val split serves as held-out evaluation instead.",
                self._asset.upper(), n_splits, EMBARGO_HOURS, min_needed, len(X_train),
            )


        # ── 5e. Sanity check: mean actual fwd return by predicted class on val
        sanity_df = pd.DataFrame({
            "predicted_label":  self._encoder.inverse_transform(y_val_pred),
            "actual_fwd_return": val_df["target_return_30d"].values,
        })
        group_means = sanity_df.groupby("predicted_label")["actual_fwd_return"].mean()
        log.info(
            "[%s] Mean actual 30d return by predicted class (val):\n%s",
            self._asset.upper(),
            group_means.reindex(["UP", "FLAT", "DOWN"]).dropna().to_string(),
        )
        mean_up   = group_means.get("UP",   float("nan"))
        mean_down = group_means.get("DOWN", float("nan"))
        if pd.notna(mean_up) and pd.notna(mean_down):
            if mean_up > mean_down:
                log.info(
                    "[%s] SANITY CHECK PASSED: mean(UP)=%.4f > mean(DOWN)=%.4f",
                    self._asset.upper(), mean_up, mean_down,
                )
            else:
                log.warning(
                    "[%s] SANITY CHECK FAILED: mean(UP)=%.4f <= mean(DOWN)=%.4f",
                    self._asset.upper(), mean_up, mean_down,
                )
        else:
            log.warning(
                "[%s] Sanity check inconclusive: UP or DOWN absent from val predictions.",
                self._asset.upper(),
            )

        # ── 6. Summary
        log.info(
            "[%s] -- FIT_PRESPLIT SUMMARY --\n"
            "  THRESH (P40 of |target_return_30d|, train only) : %.4f\n"
            "  Training label distribution                      : %s\n"
            "  Val label distribution                           : %s\n"
            "  Train accuracy                                   : %.3f\n"
            "  Val accuracy                                     : %.3f\n"
            "  Majority-class baseline (val)                    : %.3f  [predict='%s']",
            self._asset.upper(),
            thresh,
            train_dist, val_dist,
            train_acc, val_acc,
            baseline_acc, majority_name,
        )

        log.info("[%s] fit_presplit() complete.", self._asset.upper())
        return self

    def predict(self, df: pd.DataFrame) -> dict:
        """
        Classify direction for the LATEST row in df.

        Called by the API at inference time. Always predicts on the most
        recent observation in the DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Feature-engineered DataFrame.

        Returns
        -------
        dict:
            {
                "asset":         str,
                "prob_up_30d":   float,   # P(UP), 0.0-1.0
                "prob_flat_30d": float,   # P(FLAT), 0.0-1.0
                "prob_down_30d": float,   # P(DOWN), 0.0-1.0
                "direction":     str,     # "UP" | "FLAT" | "DOWN"
                "thresh":        float,   # THRESH used in labeling
            }
        """
        if not self.is_fitted:
            raise RuntimeError("Call .fit(df) before .predict().")

        _validate_input(df)

        df_sorted = df.sort_values("timestamp").reset_index(drop=True)
        latest    = df_sorted.iloc[[-1]]

        X     = latest[DIRECTION_FEATURES].values
        proba = self._model.predict_proba(X)[0]

        # Map probabilities to named classes
        class_names = list(self._encoder.classes_)   # ["DOWN", "FLAT", "UP"]
        prob_dict   = {c: float(p) for c, p in zip(class_names, proba)}

        prob_up   = round(prob_dict.get("UP",   0.0), 4)
        prob_flat = round(prob_dict.get("FLAT", 0.0), 4)
        prob_down = round(prob_dict.get("DOWN", 0.0), 4)

        # Predicted direction = argmax
        direction = max(prob_dict, key=prob_dict.get)

        result = {
            "asset":         self._asset.upper(),
            "prob_up_30d":   prob_up,
            "prob_flat_30d": prob_flat,
            "prob_down_30d": prob_down,
            "direction":     direction,
            "thresh":        round(self._thresh, 4),
        }

        log.info(
            "[%s] Direction=%s  prob_up=%.3f  prob_flat=%.3f  prob_down=%.3f  thresh=%.4f",
            self._asset.upper(), direction, prob_up, prob_flat, prob_down, self._thresh,
        )
        return result

    def predict_latest(self, df: pd.DataFrame) -> dict:
        """Alias for predict(df) — predicts on most recent row."""
        return self.predict(df)

    def save(self, path: Optional[Path] = None) -> Path:
        """Persist model to ml/models/artifacts/{asset}_direction_clf.pkl"""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        if path is None:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            path = MODEL_DIR / f"{self._asset}_direction_clf.pkl"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self, f)

        size_kb = path.stat().st_size / 1024
        log.info(
            "[%s] DirectionClassifier saved -> %s  (%.1f KB)",
            self._asset.upper(), path, size_kb,
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "DirectionClassifier":
        """
        Restore a saved DirectionClassifier.

        Example
        -------
            clf = DirectionClassifier.load("ml/models/artifacts/btc_direction_clf.pkl")
            result = clf.predict(features_df)
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"DirectionClassifier artifact not found: {path}")

        with open(path, "rb") as f:
            obj = pickle.load(f)

        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not a DirectionClassifier: {type(obj)}")

        log.info("DirectionClassifier loaded from %s  (asset=%s)", path, obj._asset)
        return obj

    def print_diagnostics(self) -> None:
        """Print training diagnostics: feature importances + classification report."""
        if not self.is_fitted:
            print("Model not fitted yet.")
            return

        sep = "=" * 55
        print(f"\n{sep}")
        print(f"  DirectionClassifier Diagnostics — {self._asset.upper()}")
        print(sep)

        print("\n  Feature Importances (top -> bottom):")
        for feat, imp in self.feature_importances.items():
            bar = "#" * int(imp * 40)
            print(f"    {feat:<22}  {imp:.4f}  {bar}")

        print(f"\n  THRESH (P40 of |fwd_return|, training only): {self._thresh:.4f}")
        print(f"  Labels: UP > +{self._thresh:.4f} | FLAT within +-{self._thresh:.4f} | DOWN < -{self._thresh:.4f}")

        if self._eval_report:
            print(f"\n  Test Set Classification Report:")
            for line in self._eval_report.strip().split("\n"):
                print(f"    {line}")

        print(sep)


# ══════════════════════════════════════════════════════════════════════════════
#  Labeling helpers
# ══════════════════════════════════════════════════════════════════════════════

def _compute_forward_return(
    df: pd.DataFrame,
    horizon_hours: int = FORWARD_HORIZON_HOURS,
) -> pd.Series:
    """
    Forward 30d log-return: ln(price_{t+720} / price_t).

    Implementation uses the reverse-rolling trick (same as _compute_forward_risk
    in classifier.py) to avoid any look-ahead:
      1. Reverse the price series
      2. Apply a trailing rolling window (= forward in reversed order)
      3. Extract the last value in each window (= price_{t+720})
      4. Reverse back
      5. Shift by -1 to exclude price_t from its own forward return

    Result: row t contains ln(price_{t+horizon} / price_t), or NaN if the
    forward price is unavailable (final `horizon_hours` rows).
    """
    price = df["price"]

    # Forward price via reverse-rolling: last value in window = price_{t+horizon}
    fwd_price = (
        price.iloc[::-1]
        .rolling(window=horizon_hours, min_periods=horizon_hours)
        .apply(lambda x: x.iloc[0], raw=False)   # first in reversed = last in forward
        .iloc[::-1]
        .shift(-1)
    )

    fwd_return = np.log(fwd_price / price)
    return fwd_return


def _return_to_label(r: float, thresh: float) -> str:
    """Map a forward return to a direction label using symmetric THRESH."""
    if r > thresh:
        return "UP"
    elif r < -thresh:
        return "DOWN"
    else:
        return "FLAT"


# ══════════════════════════════════════════════════════════════════════════════
#  Validation
# ══════════════════════════════════════════════════════════════════════════════

_REQUIRED_COLS = {"asset", "timestamp", "price"} | set(DIRECTION_FEATURES)


def _validate_input(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        raise ValueError("Input DataFrame is None or empty.")

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame missing required columns: {missing}\n"
            "  -> Pass the output of feature_engineering.build_features()"
        )

    assets = df["asset"].unique()
    if len(assets) != 1:
        raise ValueError(
            f"DirectionClassifier expects a single-asset DataFrame. "
            f"Got: {assets}\n"
            "  -> Filter first: df[df['asset'] == 'btc']"
        )


# Columns required by fit_presplit() — no 'asset' since WBTC CSVs don't carry it.
_PRESPLIT_REQUIRED_COLS = set(DIRECTION_FEATURES) | {"timestamp", "target_return_30d"}


def _validate_presplit_input(df: pd.DataFrame, name: str) -> None:
    """Validate a pre-split WBTC DataFrame for use with fit_presplit()."""
    if df is None or df.empty:
        raise ValueError(f"`{name}` is None or empty.")

    missing = _PRESPLIT_REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"`{name}` is missing required columns: {missing}\n"
            "  -> Ensure the WBTC CSV is loaded as-is from ml/data/wbtc_*_model.csv"
        )

    if df["target_return_30d"].isna().any():
        n_null = df["target_return_30d"].isna().sum()
        raise ValueError(
            f"`{name}` has {n_null} NaN values in `target_return_30d`. "
            "Resolve nulls before calling fit_presplit()."
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  —  python -m models.direction_classifier --asset btc
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AltInvest Direction Classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m models.direction_classifier --asset btc\n"
            "  python -m models.direction_classifier --asset eth\n"
            "  python -m models.direction_classifier --asset sol --no-save\n"
        ),
    )
    parser.add_argument("--asset", choices=["btc", "eth", "sol"], required=True)
    parser.add_argument(
        "--no-save", action="store_true",
        help="Skip saving model artifact (dry-run)"
    )
    return parser.parse_args()


def main():
    args  = _parse_args()
    asset = args.asset

    log.info("=" * 60)
    log.info("AltInvest Direction Classifier -- %s", asset.upper())
    log.info("=" * 60)

    # 1. Load + feature engineer
    log.info("Loading and engineering features ...")
    raw         = load_raw_csv(asset)
    features_df = build_features(raw)
    asset_df    = features_df[features_df["asset"] == asset].copy()
    log.info("Rows available: %d", len(asset_df))

    # 2. Fit
    clf = DirectionClassifier()
    clf.fit(asset_df)

    # 3. Classify latest market state
    result = clf.predict_latest(asset_df)

    # 4. Pretty print result
    print("\n" + "=" * 55)
    print(f"  Direction Classification -- {asset.upper()}")
    print("=" * 55)
    print(json.dumps(result, indent=2))
    print("=" * 55)

    # 5. Print diagnostics
    clf.print_diagnostics()

    # 6. Save artifact
    if not args.no_save:
        saved_path = clf.save()
        print(f"\n  Classifier saved -> {saved_path}")

    return result


if __name__ == "__main__":
    main()
