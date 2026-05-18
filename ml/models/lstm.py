"""
AltInvest - LSTM Time-Series Forecaster
ml/models/lstm.py

Person C (ML Engineer) - AltInvest
Produces same output format as Prophet forecaster so Person B
can swap or A/B test models without changing the API contract.

Architecture based on Murray et al. (2023) "On Forecasting Cryptocurrency
Prices: A Comparison of Machine Learning, Deep Learning, and Ensembles"
which found LSTM to be the best-performing model across BTC, ETH, LTC, XMR,
XRP with RMSE=0.0222. Their exact architecture:
    Conv1D(64, kernel=5, relu) → LSTM(75) → Dense(16, relu) → Dense(1)
    learning rate: 1e-4, sliding window: 30 days

Pre-processing follows their paper:
    1. First-order differencing (detrending for stationarity)
    2. Min-Max normalisation on training data only (to avoid leakage)

Baseline comparison: Prophet (Taylor & Letham, 2017) already implemented
in forecaster.py. LSTM targets lower MAPE than Prophet.

Usage:
    python models/lstm.py --asset btc
    python models/lstm.py --asset eth
"""

import argparse
import json
from datetime import datetime, timezone
import os
import pickle
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Optional: use tensorflow if available, else sklearn fallback ──────────────
try:
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.layers import (LSTM, Conv1D, Dense, Dropout,
                                         Flatten, Input, MaxPooling1D)
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("[WARN] TensorFlow not found. Falling back to sklearn-based approximation.")

from sklearn.preprocessing import MinMaxScaler

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "models", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ── Hyperparameters (Murray et al. 2023, Table A1) ────────────────────────────
SEQUENCE_LEN   = 30    # 30-day sliding window (paper: "sliding window of 30 days")
FORECAST_DAYS  = 30    # predict 30 days ahead
EPOCHS         = 50
BATCH_SIZE     = 32
CONV_FILTERS   = 64    # paper: "convolutional layer: 64"
CONV_KERNEL    = 5     # paper: "convolutional kernel: 5"
LSTM_UNITS     = 75    # paper: "lstm layer: 75"
DENSE_UNITS    = 16    # paper: "dense layer: 16"
LEARNING_RATE  = 1e-4  # paper: "learning rate: 1×10⁻⁴"
TRAIN_SPLIT    = 0.80  # paper: "first 80% training, last 20% test"
CONFIDENCE     = 0.85  # LSTM intervals are empirical (lower than Prophet's 0.95)


# ─────────────────────────────────────────────────────────────────────────────
#  Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_features(asset: str) -> pd.DataFrame:
    """Load processed feature CSV produced by feature_engineering.py"""
    path = os.path.join(PROCESSED_DIR, f"{asset}_features.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No processed features found for '{asset}' at {path}. "
            f"Run: python features/feature_engineering.py --asset {asset}"
        )
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"[INFO] Loaded {len(df):,} rows for {asset.upper()}")
    return df


def apply_differencing(prices: np.ndarray):
    """
    First-order differencing to achieve stationarity.
    Murray et al. (2023): "we apply the differencing transformation...
    y'(t) = y(t) - y(t-1)"
    Returns differenced series and the last original price (needed to
    reconstruct actual prices from predictions).
    """
    differenced  = np.diff(prices)        # length = len(prices) - 1
    last_price   = prices[-1]             # save for inverse transform
    return differenced, last_price


def inverse_differencing(differenced_preds: np.ndarray, last_known_price: float):
    """Reconstruct actual prices from differenced predictions."""
    prices = [last_known_price]
    for d in differenced_preds:
        prices.append(prices[-1] + d)
    return np.array(prices[1:])           # drop seed value


def build_sequences(series: np.ndarray, seq_len: int):
    """
    Convert 1-D series into (X, y) supervised sequences.
    X shape: (n_samples, seq_len, 1)
    y shape: (n_samples,)
    """
    X, y = [], []
    for i in range(seq_len, len(series)):
        X.append(series[i - seq_len : i])
        y.append(series[i])
    return np.array(X), np.array(y)


# ─────────────────────────────────────────────────────────────────────────────
#  Model builders
# ─────────────────────────────────────────────────────────────────────────────

def build_keras_lstm(seq_len: int) -> "Sequential":
    """
    Architecture from Murray et al. (2023), Table A1:
        Conv1D(64, kernel=5, relu) → LSTM(75) → Dense(16, relu) → Dense(1)
    learning rate: 1e-4

    This architecture ranked #1 across BTC, ETH, LTC, XMR, XRP
    (RMSE=0.0222, MAE=0.0173, MAPE=3.86%, R²=0.735).
    """
    model = Sequential([
        Input(shape=(seq_len, 1)),
        Conv1D(filters=CONV_FILTERS, kernel_size=CONV_KERNEL,
               activation="relu", padding="same"),
        LSTM(LSTM_UNITS, return_sequences=False),
        Dense(DENSE_UNITS, activation="relu"),
        Dense(1),
    ])
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE),
        loss="mean_squared_error",
        metrics=["mae"],
    )
    return model


def build_sklearn_fallback():
    """Fallback when TensorFlow is unavailable."""
    from sklearn.ensemble import GradientBoostingRegressor
    return GradientBoostingRegressor(
        n_estimators=300, learning_rate=0.05,
        max_depth=4, subsample=0.8, random_state=42,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Training
# ─────────────────────────────────────────────────────────────────────────────

def train(asset: str):
    print(f"\n{'='*55}")
    print(f"  AltInvest LSTM — Training on {asset.upper()}")
    print(f"  Architecture: Murray et al. (2023)")
    print(f"{'='*55}\n")

    # 1. Load data ─────────────────────────────────────────────────────────────
    df     = load_features(asset)
    prices = df["price"].values.astype(float)

    # 2. Differencing (Murray et al. 2023, Section 2.3) ────────────────────────
    # "We apply the differencing transformation... to achieve stationarity"
    differenced, last_price = apply_differencing(prices)
    print(f"[INFO] Applied first-order differencing (stationarity)")

    # 3. Train/test split 80/20 (paper: "first 80% training, last 20% test") ───
    split_idx  = int(len(differenced) * TRAIN_SPLIT)
    train_data = differenced[:split_idx]
    test_data  = differenced[split_idx:]

    # 4. Min-Max normalisation on training data only (avoid leakage) ───────────
    scaler     = MinMaxScaler(feature_range=(0, 1))
    train_norm = scaler.fit_transform(train_data.reshape(-1, 1)).flatten()
    test_norm  = scaler.transform(test_data.reshape(-1, 1)).flatten()
    full_norm  = scaler.transform(differenced.reshape(-1, 1)).flatten()
    print(f"[INFO] Normalised (fit on training data only to avoid leakage)")

    # 5. Build sequences (30-day window) ───────────────────────────────────────
    X_train, y_train = build_sequences(train_norm, SEQUENCE_LEN)
    X_test,  y_test  = build_sequences(test_norm,  SEQUENCE_LEN)
    print(f"[INFO] Train sequences : {len(X_train):,}")
    print(f"[INFO] Test  sequences : {len(X_test):,}")

    # 6. Train model ───────────────────────────────────────────────────────────
    if TF_AVAILABLE:
        X_train_3d = X_train.reshape(*X_train.shape, 1)
        X_test_3d  = X_test.reshape(*X_test.shape, 1)

        model = build_keras_lstm(SEQUENCE_LEN)
        model.summary()

        callbacks = [
            EarlyStopping(monitor="val_loss", patience=8,
                          restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                              patience=6, verbose=1),   # was 4 — increased to prevent premature LR decay
        ]

        model.fit(
            X_train_3d, y_train,
            epochs          = EPOCHS,
            batch_size      = BATCH_SIZE,
            validation_data = (X_test_3d, y_test),
            callbacks       = callbacks,
            verbose         = 1,
        )

        test_loss, test_mae = model.evaluate(X_test_3d, y_test, verbose=0)
        print(f"\n[RESULT] Test MSE (normalised differenced): {test_loss:.6f}")
        print(f"[RESULT] Test MAE (normalised differenced): {test_mae:.6f}")

    else:
        model = build_sklearn_fallback()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        rmse   = np.sqrt(np.mean((y_pred - y_test) ** 2))
        print(f"[RESULT] Fallback RMSE (normalised differenced): {rmse:.6f}")

    # 7. Generate 30-day forecast ──────────────────────────────────────────────
    # Seed with last SEQUENCE_LEN values of the normalised differenced series
    last_sequence = full_norm[-SEQUENCE_LEN:]
    diff_preds    = []

    for _ in range(FORECAST_DAYS):
        if TF_AVAILABLE:
            seq_in     = last_sequence[-SEQUENCE_LEN:].reshape(1, SEQUENCE_LEN, 1)
            next_diff  = model.predict(seq_in, verbose=0)[0][0]
        else:
            seq_in     = last_sequence[-SEQUENCE_LEN:].reshape(1, -1)
            next_diff  = model.predict(seq_in)[0]

        diff_preds.append(next_diff)
        last_sequence = np.append(last_sequence, next_diff)

    # 8. Inverse-transform: un-normalise then un-difference ────────────────────
    diff_preds_orig = scaler.inverse_transform(
        np.array(diff_preds).reshape(-1, 1)
    ).flatten()

    pred_prices   = inverse_differencing(diff_preds_orig, prices[-1])
    final_price   = float(pred_prices[-1])
    current_price = float(prices[-1])

    # Uncertainty: empirical rolling std of returns (paper uses MAPE as metric)
    recent_returns = df["return_1d"].dropna().tail(30).values
    daily_std      = np.std(recent_returns) * current_price
    margin         = daily_std * np.sqrt(FORECAST_DAYS) * 1.645

    lower = max(0.0, final_price - margin)
    upper = final_price + margin

    print(f"\n[FORECAST] {asset.upper()} in {FORECAST_DAYS} days:")
    print(f"  Current price : ${current_price:,.2f}")
    print(f"  Predicted     : ${final_price:,.2f}")
    print(f"  Lower bound   : ${lower:,.2f}")
    print(f"  Upper bound   : ${upper:,.2f}")
    print(f"  Confidence    : {CONFIDENCE}")

    # 9. Save artifacts ────────────────────────────────────────────────────────
    if TF_AVAILABLE:
        keras_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm.keras")
        model.save(keras_path)
        print(f"\n[SAVED] Keras model → {keras_path}")
    else:
        pkl_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm_fallback.pkl")
        with open(pkl_path, "wb") as f:
            pickle.dump(model, f)
        print(f"\n[SAVED] Fallback model → {pkl_path}")

    scaler_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"[SAVED] Scaler        → {scaler_path}")

    pct_change = round(((final_price - current_price) / current_price) * 100, 2)
    result = {
        "asset"           : asset.upper(),
        "model"           : "lstm" if TF_AVAILABLE else "lstm_fallback",
        "architecture"    : "Conv1D(64)+LSTM(75)+Dense(16) — Murray et al. 2023",
        "predicted_price" : round(final_price, 2),
        "prediction_30d"  : pct_change,    # % change from current price
        "lower_bound"     : round(lower, 2),
        "upper_bound"     : round(upper, 2),
        "confidence"      : CONFIDENCE,
        "timestamp"       : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    report_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm_report.json")
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[SAVED] Report        → {report_path}")

    print(f"\n✅ LSTM training complete for {asset.upper()}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Inference (called by prediction_service.py)
# ─────────────────────────────────────────────────────────────────────────────

def predict(asset: str) -> dict:
    """
    Load saved LSTM model + scaler and run a fresh 30-day forecast.
    Same JSON output as Prophet forecaster — Person B's API contract unchanged.
    """
    scaler_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm_scaler.pkl")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"No LSTM artifacts for '{asset}'. "
            f"Run: python models/lstm.py --asset {asset}"
        )

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    keras_path    = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm.keras")
    fallback_path = os.path.join(ARTIFACTS_DIR, f"{asset}_lstm_fallback.pkl")

    if TF_AVAILABLE and os.path.exists(keras_path):
        model, use_keras = load_model(keras_path), True
    elif os.path.exists(fallback_path):
        with open(fallback_path, "rb") as f:
            model = pickle.load(f)
        use_keras = False
    else:
        raise FileNotFoundError(f"No trained LSTM model found for '{asset}'.")

    df            = load_features(asset)
    prices        = df["price"].values.astype(float)
    differenced, last_price = apply_differencing(prices)
    full_norm     = scaler.transform(differenced.reshape(-1, 1)).flatten()

    last_sequence = full_norm[-SEQUENCE_LEN:]
    diff_preds    = []

    for _ in range(FORECAST_DAYS):
        if use_keras:
            seq_in    = last_sequence[-SEQUENCE_LEN:].reshape(1, SEQUENCE_LEN, 1)
            next_diff = model.predict(seq_in, verbose=0)[0][0]
        else:
            seq_in    = last_sequence[-SEQUENCE_LEN:].reshape(1, -1)
            next_diff = model.predict(seq_in)[0]
        diff_preds.append(next_diff)
        last_sequence = np.append(last_sequence, next_diff)

    diff_preds_orig = scaler.inverse_transform(
        np.array(diff_preds).reshape(-1, 1)
    ).flatten()

    pred_prices   = inverse_differencing(diff_preds_orig, prices[-1])
    final_price   = float(pred_prices[-1])
    current_price = float(prices[-1])
    daily_std     = float(df["return_1d"].dropna().tail(30).std() * current_price)
    margin        = daily_std * np.sqrt(FORECAST_DAYS) * 1.645

    pct_change = round(((final_price - current_price) / current_price) * 100, 2)
    return {
        "asset"           : asset.upper(),
        "model"           : "lstm" if use_keras else "lstm_fallback",
        "predicted_price" : round(final_price, 2),
        "prediction_30d"  : pct_change,    # % change from current price
        "lower_bound"     : round(max(0.0, final_price - margin), 2),
        "upper_bound"     : round(final_price + margin, 2),
        "confidence"      : CONFIDENCE,
        "timestamp"       : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AltInvest LSTM Forecaster")
    parser.add_argument("--asset", type=str, default="btc",
                        help="Asset to train on (btc, eth, sol, …)")
    args = parser.parse_args()

    result = train(args.asset.lower())
    print("\n── Final Output (API contract) ──")
    print(json.dumps(result, indent=2))