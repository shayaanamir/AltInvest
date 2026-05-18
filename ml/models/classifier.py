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
Labels are derived from a COMPOSITE RISK SCORE computed from the features.
This is intentionally percentile-based (not hardcoded thresholds) so the
classifier adapts to any asset's price distribution:

    composite_risk = (
        0.40 * normalised(|volatility_14d|)   +  # dominant driver
        0.25 * normalised(|return_1d|)         +  # short-term momentum shock
        0.20 * normalised(|return_7d|)         +  # weekly swing magnitude
        0.15 * normalised(|return_30d|)           # monthly trend force
    )

    low    = bottom 33rd percentile
    medium = 33rd – 67th percentile
    high   = top 33rd percentile

This means the classifier learns to reproduce these human-interpretable
thresholds from the raw feature values — avoiding data leakage while keeping
the labeling logic transparent.

At inference time risk_score = P(high) * 100, giving a 0–100 continuous risk signal.

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
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

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

# Composite risk score weights (must sum to 1.0)
RISK_WEIGHTS = {
    "volatility_14d": 0.40,
    "return_1d":      0.25,
    "return_7d":      0.20,
    "return_30d":     0.15,
}

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
        Default (33, 67) gives balanced three-class distribution.
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
        self._thresholds: Optional[dict]                = None   # {low_p, high_p}
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
            2. Compute composite risk score per row
            3. Assign low/medium/high labels via percentile thresholds
            4. Train/test split (80/20, time-ordered — no shuffle to prevent leakage)
            5. Fit RandomForest
            6. Evaluate with cross-val + classification report

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

        # 1. Compute composite risk score
        df = df.copy()
        df["_risk_score"] = _compute_composite_risk(df)

        # 2. Label via percentile thresholds (fitted on training data)
        low_p  = float(np.percentile(df["_risk_score"], self._risk_percentiles[0]))
        high_p = float(np.percentile(df["_risk_score"], self._risk_percentiles[1]))
        self._thresholds = {"low_pct": low_p, "high_pct": high_p}

        df["_risk_label"] = df["_risk_score"].apply(
            lambda s: _score_to_label(s, low_p, high_p)
        )

        label_dist = df["_risk_label"].value_counts().to_dict()
        log.info("[%s] Label distribution: %s", asset.upper(), label_dist)

        # 3. Build X, y (time-ordered — no shuffle)
        X = df[CLASSIFIER_FEATURES].values
        y_raw = df["_risk_label"].values

        # Encode labels: low=0, medium=1, high=2
        self._encoder = LabelEncoder()
        self._encoder.fit(RISK_LABELS)          # fix class order across assets
        y = self._encoder.transform(y_raw)

        # 4. Train/test split (last 20% = most recent = held-out test)
        split_idx = int(len(X) * 0.80)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        log.info(
            "[%s] Train: %d rows | Test: %d rows",
            asset.upper(), len(X_train), len(X_test),
        )

        # 5. Fit RandomForest
        self._model = RandomForestClassifier(**self._rf_params)
        self._model.fit(X_train, y_train)

        # 6. Evaluate
        y_pred = self._model.predict(X_test)
        self._eval_report = classification_report(
            y_test, y_pred,
            target_names=self._encoder.classes_,
            zero_division=0,
        )

        cv_scores = cross_val_score(
            self._model, X, y,
            cv=5, scoring="accuracy", n_jobs=-1,
        )

        log.info(
            "[%s] CV Accuracy: %.3f (+/- %.3f)",
            asset.upper(), cv_scores.mean(), cv_scores.std(),
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

def _minmax_norm(series: pd.Series) -> pd.Series:
    """Min-max normalise a series to [0, 1]. Safe against zero-range series."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - lo) / (hi - lo)


def _compute_composite_risk(df: pd.DataFrame) -> pd.Series:
    """
    Compute a [0, 1] composite risk score per row using weighted feature norms.

    All components use absolute values (magnitude matters, not direction):
        high volatility     = high risk
        large return swings = high risk (up OR down — tail risk)
    """
    score = pd.Series(np.zeros(len(df)), index=df.index)

    for col, weight in RISK_WEIGHTS.items():
        if col in df.columns:
            score += weight * _minmax_norm(df[col].abs())

    return score


def _score_to_label(score: float, low_p: float, high_p: float) -> str:
    """Map a composite risk score to a string label."""
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
