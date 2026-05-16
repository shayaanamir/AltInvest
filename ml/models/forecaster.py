"""
forecaster.py
─────────────────────────────────────────────────────────────────────────────
Prophet-based time-series price forecaster for AltInvest.

Design
------
- Input  : feature-engineered DataFrame from feature_engineering.build_features()
- Output : prediction dict matching the backend's GET /prediction/{asset} contract

Output contract (exact schema backend expects):
    {
        "asset":          "btc",
        "prediction_30d": 72450.50,
        "lower_bound":    68000.00,
        "upper_bound":    76000.00,
        "confidence":     0.78
    }

Architecture
------------
    ProphetForecaster
        .fit(df)             — train on historical price data
        .predict()           — return 30-day forward prediction dict
        .save(path)          — persist trained model to disk
        .load(path)          — restore model from disk
        .is_fitted           — bool property

Internal steps
--------------
1. Resample hourly -> daily OHLC (Prophet works best on daily cadence)
2. Add regressors: volatility_14d, ma_cross, volume_change_pct (daily median)
3. Fit Prophet with multiplicative seasonality (crypto is non-linear)
4. Forecast 30 days forward (horizon = 30 periods at daily frequency)
5. Extract yhat, yhat_lower, yhat_upper for day 30
6. Compute confidence score from uncertainty interval width
7. Return structured dict

Regressors note
---------------
Prophet regressors require future values at prediction time. We forward-fill
the last known regressor values into the future dataframe — a safe assumption
for a 30-day horizon where we have no sentiment signal yet.

Usage
-----
    from models.forecaster import ProphetForecaster
    from features.feature_engineering import load_raw_csv, build_features

    df = build_features(load_raw_csv("btc"))
    model = ProphetForecaster()
    model.fit(df)
    result = model.predict()
    # -> {"asset": "btc", "prediction_30d": ..., ...}

CLI:
    python -m models.forecaster --asset btc
    python -m models.forecaster --asset eth --no-save

Author : ML Engineer (Person C) — dev-shail branch
"""

import os
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

# Suppress Prophet / cmdstanpy verbosity
warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

from prophet import Prophet

# ─── Project imports ──────────────────────────────────────────────────────────
_ML_ROOT = Path(__file__).resolve().parent.parent   # …/ml/
sys.path.insert(0, str(_ML_ROOT))

from features.feature_engineering import (
    load_raw_csv,
    build_features,
    get_feature_names,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("forecaster")

# ─── Constants ────────────────────────────────────────────────────────────────
FORECAST_HORIZON_DAYS = 30
INTERVAL_WIDTH        = 0.80    # 80% prediction interval (Prophet default is 80%)
MODEL_DIR             = _ML_ROOT / "models" / "artifacts"

# Regressors we pass to Prophet (must be aggregatable from hourly features)
REGRESSORS = ["volatility_14d", "ma_cross", "volume_change_pct"]


# ══════════════════════════════════════════════════════════════════════════════
#  ProphetForecaster
# ══════════════════════════════════════════════════════════════════════════════

class ProphetForecaster:
    """
    Wraps Facebook Prophet for AltInvest price forecasting.

    Parameters
    ----------
    interval_width : float
        Width of the uncertainty interval (default 0.80 = 80%).
        Affects confidence score derivation.
    horizon_days : int
        Number of days to forecast forward (default 30).
    """

    def __init__(
        self,
        interval_width: float = INTERVAL_WIDTH,
        horizon_days: int     = FORECAST_HORIZON_DAYS,
    ):
        self.interval_width = interval_width
        self.horizon_days   = horizon_days

        self._model:  Optional[Prophet] = None
        self._asset:  Optional[str]     = None
        self._last_regressors: Optional[pd.Series] = None   # for future frame fill
        self._daily_df: Optional[pd.DataFrame] = None       # stored for diagnostics

    # ── Public interface ───────────────────────────────────────────────────────

    @property
    def is_fitted(self) -> bool:
        return self._model is not None and self._asset is not None

    def fit(self, df: pd.DataFrame) -> "ProphetForecaster":
        """
        Train Prophet on the feature-engineered DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Output of feature_engineering.build_features().
            Must contain exactly ONE asset (use df[df.asset == 'btc'] if needed).

        Returns
        -------
        self  — enables method chaining: model.fit(df).predict()
        """
        _validate_input(df)

        # Infer asset name from data (never hardcoded)
        asset = df["asset"].iloc[0].lower()
        self._asset = asset
        log.info("[%s] Starting Prophet fit ...", asset.upper())

        # 1. Resample hourly -> daily
        daily = self._resample_daily(df)
        self._daily_df = daily
        log.info("[%s] Resampled to %d daily rows", asset.upper(), len(daily))

        # 2. Store last regressor values (used to fill future frame)
        self._last_regressors = daily[REGRESSORS].iloc[-1].copy()

        # 3. Build Prophet-format DataFrame
        prophet_df = self._build_prophet_df(daily)

        # 4. Configure & fit Prophet
        self._model = self._build_prophet_model()
        self._model.fit(prophet_df)

        log.info("[%s] Prophet fit complete.", asset.upper())
        return self

    def predict(self) -> dict:
        """
        Generate 30-day forward prediction.

        Returns
        -------
        dict matching the backend's /prediction/{asset} contract:
            {
                "asset":          str,
                "prediction_30d": float,
                "lower_bound":    float,
                "upper_bound":    float,
                "confidence":     float   (0.0 – 1.0)
            }

        Raises
        ------
        RuntimeError  — if called before fit()
        """
        if not self.is_fitted:
            raise RuntimeError(
                "Model is not fitted. Call .fit(df) before .predict()."
            )

        log.info("[%s] Generating %d-day forecast ...", self._asset.upper(), self.horizon_days)

        # 1. Build future DataFrame (includes history + horizon)
        future = self._build_future_df()

        # 2. Prophet forecast
        forecast = self._model.predict(future)

        # 3. Extract day-30 values (last row of future = t+30)
        row = forecast.iloc[-1]
        pred   = round(float(row["yhat"]),       2)
        lower  = round(float(row["yhat_lower"]), 2)
        upper  = round(float(row["yhat_upper"]), 2)

        # 4. Ensure lower <= pred <= upper (Prophet can occasionally invert)
        lower = min(lower, pred)
        upper = max(upper, pred)

        # 5. Derive confidence score from interval width
        confidence = self._compute_confidence(pred, lower, upper)

        result = {
            "asset":          self._asset,
            "prediction_30d": pred,
            "lower_bound":    lower,
            "upper_bound":    upper,
            "confidence":     confidence,
        }

        log.info(
            "[%s] Prediction: $%.2f  [%.2f – %.2f]  confidence=%.2f",
            self._asset.upper(), pred, lower, upper, confidence,
        )
        return result

    def save(self, path: Optional[Path] = None) -> Path:
        """
        Persist the trained model to disk using pickle.

        Parameters
        ----------
        path : optional override; defaults to ml/models/artifacts/<asset>_prophet.pkl

        Returns
        -------
        Path  — where the model was saved
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        if path is None:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            path = MODEL_DIR / f"{self._asset}_prophet.pkl"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self, f)

        size_kb = path.stat().st_size / 1024
        log.info("[%s] Model saved -> %s  (%.1f KB)", self._asset.upper(), path, size_kb)
        return path

    @classmethod
    def load(cls, path: Path) -> "ProphetForecaster":
        """
        Restore a previously saved ProphetForecaster from disk.

        Parameters
        ----------
        path : path to the .pkl file

        Returns
        -------
        ProphetForecaster  — ready to call .predict() immediately

        Example
        -------
            model = ProphetForecaster.load("ml/models/artifacts/btc_prophet.pkl")
            result = model.predict()
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        with open(path, "rb") as f:
            obj = pickle.load(f)

        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not a ProphetForecaster: {type(obj)}")

        log.info("Model loaded from %s  (asset=%s)", path, obj._asset)
        return obj

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _resample_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate hourly data to daily OHLC + feature medians.

        Prophet is designed for daily (or lower) frequency.
        Using close-of-day price (last value) as 'y'.
        Regressors use daily median — robust to intra-day spikes.
        """
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp").sort_index()

        daily = pd.DataFrame()
        daily["y"] = df["price"].resample("D").last()          # close price

        # Regressors: daily median
        for col in REGRESSORS:
            if col in df.columns:
                daily[col] = df[col].resample("D").median()

        # ma_cross: daily mode (it's categorical -1/0/1)
        if "ma_cross" in REGRESSORS and "ma_cross" in df.columns:
            daily["ma_cross"] = (
                df["ma_cross"]
                .resample("D")
                .apply(lambda x: x.mode().iloc[0] if len(x) > 0 else 0)
            )

        daily = daily.dropna().reset_index()
        daily = daily.rename(columns={"timestamp": "ds"})
        daily["ds"] = daily["ds"].dt.tz_localize(None)         # Prophet needs tz-naive
        return daily

    def _build_prophet_df(self, daily: pd.DataFrame) -> pd.DataFrame:
        """Return the minimal ds/y + regressor columns Prophet.fit() expects."""
        cols = ["ds", "y"] + [r for r in REGRESSORS if r in daily.columns]
        return daily[cols].copy()

    def _build_prophet_model(self) -> Prophet:
        """
        Configure Prophet with crypto-appropriate settings.

        Key choices:
        - multiplicative seasonality: crypto prices scale non-linearly
        - yearly/weekly seasonality on; daily off (daily cadence data)
        - uncertainty_samples=500 for stable interval estimates
        """
        model = Prophet(
            interval_width=self.interval_width,
            seasonality_mode="multiplicative",
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            uncertainty_samples=500,
            changepoint_prior_scale=0.15,      # moderate flexibility
            seasonality_prior_scale=10.0,
        )

        # Add external regressors
        for regressor in REGRESSORS:
            if regressor in (self._daily_df.columns if self._daily_df is not None else []):
                model.add_regressor(regressor, standardize=True)

        return model

    def _build_future_df(self) -> pd.DataFrame:
        """
        Build Prophet's future DataFrame (history + horizon).

        Regressor values for future dates are forward-filled from the last
        known values — standard practice when future signals are unavailable.
        """
        future = self._model.make_future_dataframe(
            periods=self.horizon_days,
            freq="D",
        )

        # Fill regressors: history from training data, future = last known value
        for regressor in REGRESSORS:
            if regressor in self._daily_df.columns:
                # Map historical ds -> regressor value
                hist_map = self._daily_df.set_index("ds")[regressor]
                future[regressor] = future["ds"].map(hist_map)
                # Forward-fill future rows with last known value
                last_val = float(self._last_regressors[regressor])
                future[regressor] = future[regressor].fillna(last_val)

        return future

    @staticmethod
    def _compute_confidence(pred: float, lower: float, upper: float) -> float:
        """
        Derive a [0, 1] confidence score from the prediction interval width.

        Logic:
        - Narrower interval relative to predicted price => higher confidence
        - confidence = 1 - (interval_width / predicted_price)
        - Clipped to [0.0, 0.99] — never report 100% confidence

        Example:
            pred=70000, lower=60000, upper=80000
            interval_width = 20000 / 70000 = 0.286
            confidence = 1 - 0.286 = 0.71
        """
        if pred <= 0:
            return 0.50

        relative_width = (upper - lower) / pred
        confidence = 1.0 - relative_width
        return round(float(np.clip(confidence, 0.0, 0.99)), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  Validation helper
# ══════════════════════════════════════════════════════════════════════════════

_REQUIRED_COLS = {"asset", "price", "timestamp"}

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
            f"ProphetForecaster expects a single-asset DataFrame. "
            f"Got {len(assets)} assets: {assets}\n"
            "  -> Filter first: df[df['asset'] == 'btc']"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  —  python -m models.forecaster --asset btc
# ══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AltInvest Prophet Forecaster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m models.forecaster --asset btc\n"
            "  python -m models.forecaster --asset eth --no-save\n"
        ),
    )
    parser.add_argument("--asset", choices=["btc", "eth"], required=True)
    parser.add_argument(
        "--no-save", action="store_true",
        help="Skip saving the model artifact (dry-run)"
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    asset = args.asset

    log.info("=" * 60)
    log.info("AltInvest Prophet Forecaster — %s", asset.upper())
    log.info("=" * 60)

    # 1. Load + feature engineer
    log.info("Loading and engineering features ...")
    raw          = load_raw_csv(asset)
    features_df  = build_features(raw)
    asset_df     = features_df[features_df["asset"] == asset].copy()

    log.info("Training rows: %d", len(asset_df))

    # 2. Fit
    model = ProphetForecaster()
    model.fit(asset_df)

    # 3. Predict
    result = model.predict()

    # 4. Pretty print
    print("\n" + "=" * 55)
    print(f"  Prediction Result — {asset.upper()}")
    print("=" * 55)
    print(json.dumps(result, indent=2))
    print("=" * 55)

    # 5. Save model artifact
    if not args.no_save:
        saved_path = model.save()
        print(f"\n  Model saved -> {saved_path}")

    return result


if __name__ == "__main__":
    main()
