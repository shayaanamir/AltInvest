"""
classifier.py
─────────────────────────────────────────────────────────────────────────────
RandomForest-based risk classifier for AltInvest.

Design
------
- Input  : feature-engineered DataFrame from feature_engineering.build_features()
- Output : risk classification dict

Output contract:
    {
        "asset":        "btc",
        "risk_score":   67.5,       # 0–100 continuous score (higher = riskier, internal)
        "sharpe_ratio": 1.4         # annualised Sharpe ratio from return_1d
    }

Labeling Strategy
-----------------
Labels are based on FORWARD REALIZED VOLATILITY over the next 7 days
(168 hours), strictly after each observation row.

    Risk_t = Std(return_1h_{t+1}, ..., return_1h_{t+168})

This is the standard-deviation of hourly log returns in a 168-hour window
that begins AFTER row t. It does NOT overlap with the trailing 14-day
volatility feature (volatility_14d), which looks backward.

The continuous forward-vol values are bucketed into Low / Medium / High
using the 33rd and 67th percentile thresholds derived ONLY from the
training split. Those fixed thresholds are then applied to both training
and test data.

At inference time risk_score = P(high) × 100, giving a 0–100 continuous
risk signal interpretable as:

    "Probability that the asset will experience high realized volatility
     during the next 7 days."

This is NOT a complete financial-risk measure (e.g. VaR or Expected
Shortfall). It is a clean, forward-looking volatility-risk target.

Architecture
------------
    RiskClassifier
        .fit(df)             — label + train RandomForest
        .predict(df)         — classify latest market state
        .predict_latest(df)  — shortcut: predict on most recent row
        .save(path)          — persist to disk
        .load(path)          — restore from disk
        .feature_importances — dict of feature -> importance

Usage
-----
    from models.classifier import RiskClassifier
    from features.feature_engineering import load_raw_csv, build_features

    df = build_features(load_raw_csv("btc"))
    clf = RiskClassifier()
    clf.fit(df)
    result = clf.predict_latest(df)
    # -> {"asset": "btc", "risk_score": 67.5, "sharpe_ratio": 1.4}

CLI:
    python -m models.classifier --asset btc
    python -m models.classifier --asset eth --no-save

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
log = logging.getLogger("classifier")

# ─── Constants ────────────────────────────────────────────────────────────────
MODEL_DIR   = _ML_ROOT / "models" / "artifacts"
RISK_LABELS = ["low", "medium", "high"]     # ordered low -> high

FORWARD_HORIZON_HOURS = 24 * 7              # 168 hours = 7 days

# Feature columns used for classification
CLASSIFIER_FEATURES = [
    "return_1h",
    "return_1d",
    "return_7d",
    "return_30d",
    "volatility_14d",
    "ma_cross",
    "volume_change_pct",
]

# Percentile boundaries for low/medium/high
RISK_PERCENTILES = (33, 67)

# RandomForest hyperparameters
RF_PARAMS = {
    "n_estimators":      300,
    "max_depth":         8,
    "min_samples_leaf":  10,
    "class_weight":      "balanced",   # handles any class imbalance from labeling
    "random_state":      42,
    "n_jobs":            -1,
}


# ══════════════════════════════════════════════════════════════════════════════
#  RiskClassifier
# ══════════════════════════════════════════════════════════════════════════════

class RiskClassifier:
    """
    RandomForest risk classifier for crypto assets.

    Parameters
    ----------
    rf_params : dict
        RandomForestClassifier kwargs. Defaults to RF_PARAMS.
    risk_percentiles : tuple
        (low_pct, high_pct) percentile boundaries for labeling.
        Default (33, 67) gives approximately balanced three-class
        distribution on the training set.
    """

    def __init__(
        self,
        rf_params:        dict  = None,
        risk_percentiles: tuple = RISK_PERCENTILES,
    ):
        self._rf_params        = rf_params or RF_PARAMS
        self._risk_percentiles = risk_percentiles

        self._model:   Optional[RandomForestClassifier] = None
        self._encoder: Optional[LabelEncoder]           = None
        self._asset:   Optional[str]                    = None
        self._thresholds: Optional[dict]                = None   # {low_pct, high_pct}
        self._eval_report: Optional[str]                = None

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
            zip(CLASSIFIER_FEATURES, importances),
            key=lambda x: x[1], reverse=True,
        ))

    def fit(self, df: pd.DataFrame) -> "RiskClassifier":
        """
        Label data and train the RandomForest classifier.

        Steps:
            1. Validate input
            2. Compute forward realized volatility per row (next 168h)
            3. Drop rows with no forward label (~168 final rows)
            4. Chronological 80/20 split with 168h embargo
            5. Compute 33rd/67th percentile thresholds from TRAINING data only
            6. Assign low/medium/high labels to both sets using those thresholds
            7. Fit RandomForest on training data
            8. Evaluate: TimeSeriesSplit CV, test-set report, sanity check

        Parameters
        ----------
        df : pd.DataFrame
            Output of feature_engineering.build_features().
            Single-asset DataFrame only.

        Returns
        -------
        self
        """
        _validate_input(df)
        asset = df["asset"].iloc[0].lower()
        self._asset = asset
        log.info("[%s] Starting RiskClassifier fit ...", asset.upper())

        # 1. Compute forward realized volatility
        df = df.copy()
        df["_risk_score"] = _compute_forward_risk(df)

        # 2. Drop rows with NaN forward labels (final ~168 rows)
        n_before = len(df)
        df = df.dropna(subset=["_risk_score"]).reset_index(drop=True)
        n_dropped = n_before - len(df)
        log.info(
            "[%s] Dropped %d rows with no forward label (need %dh of future data). "
            "Remaining: %d rows.",
            asset.upper(), n_dropped, FORWARD_HORIZON_HOURS, len(df),
        )

        # 3. Chronological split with embargo
        split_idx = int(len(df) * 0.80)
        embargo = FORWARD_HORIZON_HOURS

        train_end = split_idx - embargo

        train_df = df.iloc[:train_end].copy()
        test_df_full = df.iloc[split_idx:].copy()

        log.info(
            "[%s] Split: train=%d rows (idx 0..%d), embargo=%d rows skipped, "
            "test=%d rows (idx %d..%d)",
            asset.upper(), len(train_df), train_end - 1, embargo,
            len(test_df_full), split_idx, len(df) - 1,
        )

        # 4. Percentile thresholds from TRAINING data only
        low_p  = float(np.percentile(train_df["_risk_score"], self._risk_percentiles[0]))
        high_p = float(np.percentile(train_df["_risk_score"], self._risk_percentiles[1]))
        self._thresholds = {"low_pct": low_p, "high_pct": high_p}

        log.info(
            "[%s] Thresholds (from training data): 33rd=%.6f  67th=%.6f",
            asset.upper(), low_p, high_p,
        )

        # 5. Label both sets using those fixed thresholds
        train_df["_risk_label"] = train_df["_risk_score"].apply(
            lambda s: _score_to_label(s, low_p, high_p)
        )
        test_df_full["_risk_label"] = test_df_full["_risk_score"].apply(
            lambda s: _score_to_label(s, low_p, high_p)
        )

        train_dist = train_df["_risk_label"].value_counts().to_dict()
        test_dist  = test_df_full["_risk_label"].value_counts().to_dict()
        log.info("[%s] Training label distribution: %s", asset.upper(), train_dist)
        log.info("[%s] Test label distribution:     %s", asset.upper(), test_dist)

        # 6. Build X, y
        X_train = train_df[CLASSIFIER_FEATURES].values
        X_test  = test_df_full[CLASSIFIER_FEATURES].values

        self._encoder = LabelEncoder()
        self._encoder.fit(RISK_LABELS)          # fix class order across assets

        y_train = self._encoder.transform(train_df["_risk_label"].values)
        y_test  = self._encoder.transform(test_df_full["_risk_label"].values)

        log.info(
            "[%s] Train: %d rows | Test: %d rows",
            asset.upper(), len(X_train), len(X_test),
        )

        # 7. Fit RandomForest
        self._model = RandomForestClassifier(**self._rf_params)
        self._model.fit(X_train, y_train)

        # 8a. Train accuracy
        y_train_pred = self._model.predict(X_train)
        train_acc = accuracy_score(y_train, y_train_pred)
        log.info("[%s] Train accuracy: %.3f", asset.upper(), train_acc)

        # 8b. Test accuracy + classification report
        y_pred = self._model.predict(X_test)
        test_acc = accuracy_score(y_test, y_pred)

        self._eval_report = classification_report(
            y_test, y_pred,
            target_names=self._encoder.classes_,
            zero_division=0,
        )
        log.info("[%s] Test accuracy:  %.3f", asset.upper(), test_acc)

        # 8c. TimeSeriesSplit CV (with gap = FORWARD_HORIZON_HOURS)
        #     Run on training data only to avoid look-ahead
        tscv = TimeSeriesSplit(
            n_splits=5,
            gap=FORWARD_HORIZON_HOURS,
        )
        cv_scores = cross_val_score(
            self._model, X_train, y_train,
            cv=tscv, scoring="accuracy", n_jobs=-1,
        )
        log.info(
            "[%s] TimeSeriesSplit CV Accuracy: %.3f (+/- %.3f)",
            asset.upper(), cv_scores.mean(), cv_scores.std(),
        )

        # 8d. Sanity check: mean actual forward vol by predicted class
        sanity_df = pd.DataFrame({
            "predicted_label": self._encoder.inverse_transform(y_pred),
            "actual_forward_vol": test_df_full["_risk_score"].values,
        })

        group_means = (
            sanity_df
            .groupby("predicted_label")["actual_forward_vol"]
            .mean()
        )

        log.info(
            "[%s] Mean actual forward vol by predicted bucket:\n%s",
            asset.upper(),
            group_means.reindex(RISK_LABELS).to_string(),
        )

        # Check monotonicity: High-predicted should have higher vol than Low-predicted
        mean_high = group_means.get("high", float("nan"))
        mean_low  = group_means.get("low", float("nan"))

        if pd.notna(mean_high) and pd.notna(mean_low):
            if mean_high > mean_low:
                log.info(
                    "[%s] ✓ SANITY CHECK PASSED: mean(High)=%.6f > mean(Low)=%.6f",
                    asset.upper(), mean_high, mean_low,
                )
            else:
                log.warning(
                    "[%s] ✗ SANITY CHECK FAILED: mean(High)=%.6f <= mean(Low)=%.6f  "
                    "— the classifier's predicted 'high' bucket does NOT have higher "
                    "actual forward volatility than the 'low' bucket!",
                    asset.upper(), mean_high, mean_low,
                )
        else:
            log.warning(
                "[%s] ✗ SANITY CHECK INCONCLUSIVE: one or both of high/low buckets "
                "have no test predictions.",
                asset.upper(),
            )

        # ── Summary report ────────────────────────────────────────────────
        log.info(
            "[%s] ── FIT SUMMARY ──\n"
            "  Rows dropped (no forward label) : %d\n"
            "  Training label distribution     : %s\n"
            "  Test label distribution          : %s\n"
            "  33rd percentile threshold        : %.6f\n"
            "  67th percentile threshold        : %.6f\n"
            "  Train accuracy                   : %.3f\n"
            "  Test accuracy                    : %.3f\n"
            "  TimeSeriesSplit CV accuracy       : %.3f (+/- %.3f)",
            asset.upper(),
            n_dropped,
            train_dist,
            test_dist,
            low_p,
            high_p,
            train_acc,
            test_acc,
            cv_scores.mean(), cv_scores.std(),
        )

        log.info("[%s] Fit complete.", asset.upper())
        return self

    def predict(self, df: pd.DataFrame) -> dict:
        """
        Classify risk for the LATEST row in df.

        This is the main inference method called by the API. It always
        predicts on the most recent observation in the DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Feature-engineered DataFrame (can be full history or just recent rows).

        Returns
        -------
        dict:
            {
                "asset":        str,
                "risk_score":   float,   # 0–100 continuous
                "sharpe_ratio": float,
            }
        """
        if not self.is_fitted:
            raise RuntimeError("Call .fit(df) before .predict().")

        _validate_input(df)

        # Use most recent row
        df_sorted = df.sort_values("timestamp").reset_index(drop=True)
        latest = df_sorted.iloc[[-1]]   # keep as DataFrame (not Series)

        X = latest[CLASSIFIER_FEATURES].values

        proba = self._model.predict_proba(X)[0]   # [P(low), P(med), P(high)]

        # risk_score = P(high) * 100  — continuous 0–100 signal (internal, higher = riskier)
        high_idx   = list(self._encoder.classes_).index("high")
        risk_score = round(float(proba[high_idx]) * 100, 1)

        # Annualised Sharpe ratio from the daily return column
        sharpe = compute_sharpe_ratio(df_sorted)

        result = {
            "asset":        self._asset.upper(),
            "risk_score":   risk_score,
            "sharpe_ratio": sharpe,
        }

        log.info(
            "[%s] Risk score=%.1f  sharpe=%.4f  probas=%s",
            self._asset.upper(), risk_score, sharpe,
            {c: round(p, 3) for c, p in zip(self._encoder.classes_, proba)},
        )
        return result

    # Alias — semantic sugar for the API
    def predict_latest(self, df: pd.DataFrame) -> dict:
        """Alias for predict(df) — predicts on most recent row."""
        return self.predict(df)

    def save(self, path: Optional[Path] = None) -> Path:
        """Persist model to ml/models/artifacts/<asset>_rf_classifier.pkl"""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        if path is None:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            path = MODEL_DIR / f"{self._asset}_rf_classifier.pkl"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self, f)

        size_kb = path.stat().st_size / 1024
        log.info("[%s] Classifier saved -> %s  (%.1f KB)", self._asset.upper(), path, size_kb)
        return path

    @classmethod
    def load(cls, path: Path) -> "RiskClassifier":
        """
        Restore a saved RiskClassifier.

        Example
        -------
            clf = RiskClassifier.load("ml/models/artifacts/btc_rf_classifier.pkl")
            result = clf.predict(features_df)
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Classifier artifact not found: {path}")

        with open(path, "rb") as f:
            obj = pickle.load(f)

        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not a RiskClassifier: {type(obj)}")

        log.info("Classifier loaded from %s  (asset=%s)", path, obj._asset)
        return obj

    def print_diagnostics(self) -> None:
        """Print training diagnostics: feature importances + classification report."""
        if not self.is_fitted:
            print("Model not fitted yet.")
            return

        sep = "=" * 55
        print(f"\n{sep}")
        print(f"  RiskClassifier Diagnostics — {self._asset.upper()}")
        print(sep)

        print("\n  Feature Importances (top -> bottom):")
        for feat, imp in self.feature_importances.items():
            bar = "#" * int(imp * 40)
            print(f"    {feat:<22}  {imp:.4f}  {bar}")

        print(f"\n  Risk thresholds  (percentile {self._risk_percentiles}):")
        print(f"    low  <  {self._thresholds['low_pct']:.6f}")
        print(f"    high >= {self._thresholds['high_pct']:.6f}")

        if self._eval_report:
            print(f"\n  Test Set Classification Report:")
            for line in self._eval_report.strip().split("\n"):
                print(f"    {line}")

        print(sep)


# ══════════════════════════════════════════════════════════════════════════════
#  Sharpe ratio
# ══════════════════════════════════════════════════════════════════════════════

def compute_sharpe_ratio(df: pd.DataFrame) -> float:
    """
    Compute the annualised Sharpe ratio from the ``return_1d`` column.

    Formula:
        sharpe = mean(return_1d) / std(return_1d) * sqrt(252)

    252 = conventional number of trading days in a year.
    We use daily returns (return_1d) already present in the feature DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Feature-engineered DataFrame containing a ``return_1d`` column.

    Returns
    -------
    float  — annualised Sharpe ratio, rounded to 4 decimal places.
             Returns 0.0 if std is zero (degenerate / constant price series).
    """
    if "return_1d" not in df.columns:
        log.warning("return_1d column not found — Sharpe ratio will be 0.0")
        return 0.0

    returns = df["return_1d"].dropna()
    if returns.empty:
        return 0.0

    mu  = returns.mean()
    std = returns.std()

    if std == 0:
        return 0.0

    sharpe = (mu / std) * np.sqrt(252)
    return round(float(sharpe), 4)


# ══════════════════════════════════════════════════════════════════════════════
#  Labeling helpers
# ══════════════════════════════════════════════════════════════════════════════

def _compute_forward_risk(
    df: pd.DataFrame,
    horizon_hours: int = FORWARD_HORIZON_HOURS,
) -> pd.Series:
    """
    Forward realized volatility: std of return_1h over the NEXT
    `horizon_hours`, strictly after row t.

    Risk_t = Std(r_{t+1}, ..., r_{t+168})

    Implementation uses the reverse-rolling trick:
      1. Reverse the series
      2. Apply a trailing rolling window (which in reversed order = forward)
      3. Reverse back
      4. Shift by -1 to exclude row t itself (strictly after)

    This does NOT overlap with the trailing volatility_14d feature
    because volatility_14d looks backward while this looks forward.
    """
    reversed_returns = df["return_1h"].iloc[::-1]

    fwd_vol = (
        reversed_returns
        .rolling(
            window=horizon_hours,
            min_periods=horizon_hours,
        )
        .std()
        .iloc[::-1]
        .shift(-1)
    )

    return fwd_vol


def _score_to_label(score: float, low_p: float, high_p: float) -> str:
    """Map a forward-risk score to a string label."""
    if score < low_p:
        return "low"
    elif score < high_p:
        return "medium"
    else:
        return "high"


# ══════════════════════════════════════════════════════════════════════════════
#  Validation
# ══════════════════════════════════════════════════════════════════════════════

_REQUIRED_COLS = {"asset", "timestamp"} | set(CLASSIFIER_FEATURES)

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
            f"RiskClassifier expects a single-asset DataFrame. "
            f"Got: {assets}\n"
            "  -> Filter first: df[df['asset'] == 'btc']"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  —  python -m models.classifier --asset btc
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AltInvest Risk Classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m models.classifier --asset btc\n"
            "  python -m models.classifier --asset eth\n"
            "  python -m models.classifier --asset sol --no-save\n"
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
    log.info("AltInvest Risk Classifier — %s", asset.upper())
    log.info("=" * 60)

    # 1. Load + feature engineer
    log.info("Loading and engineering features ...")
    raw         = load_raw_csv(asset)
    features_df = build_features(raw)
    asset_df    = features_df[features_df["asset"] == asset].copy()
    log.info("Rows available: %d", len(asset_df))

    # 2. Fit
    clf = RiskClassifier()
    clf.fit(asset_df)

    # 3. Classify latest market state
    result = clf.predict_latest(asset_df)

    # 4. Pretty print result
    print("\n" + "=" * 55)
    print(f"  Risk Classification — {asset.upper()}")
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
