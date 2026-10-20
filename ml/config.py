"""Project constants. The ONLY place for constants (docs/ARCHITECTURE.md, AGENTS rule 6)."""

import os
from pathlib import Path

# Asset id -> Binance spot symbol (docs/DATA.md). The single source of truth for the asset list.
ASSET_SYMBOLS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}

# Assets served in phases 1-7 (docs/REQUIREMENTS.md, D4). Lowercase ids; the API uppercases them.
ASSETS = tuple(ASSET_SYMBOLS)

# Forecast horizon in daily bars (D3).
HORIZON_DAYS = 30

# Chronological split fractions of the full series (docs/DATA.md "Splits", D11, D16).
SPLIT_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}

# Gap between consecutive splits, equal to the horizon, cut from the end of the earlier split (D16).
EMBARGO_DAYS = HORIZON_DAYS

# Rows dropped at the start of the feature table: the longest trailing window (30 bars) plus one (D18).
WARMUP_ROWS = 30

# Label thresholds, fitted on train only (D19). Percentiles in 0-100.
DIRECTION_FLAT_PERCENTILE = 40          # of |fwd_return_30d|
RISK_PERCENTILES = (33, 67)             # of fwd_vol_30d

# Walk-forward (D21): each fold trains on at least MIN_TRAIN_ROWS rows; a new origin every WALKFORWARD_STEP rows.
MIN_TRAIN_ROWS = 730
WALKFORWARD_STEP = 30

# Annualisation for Sharpe and volatility: sqrt(365) (docs/EVALUATION.md rule 5).
ANNUALISATION_DAYS = 365

# Signals the service may emit (D7: no STRONG_* without backtest evidence).
SIGNALS = ("BUY", "HOLD", "SELL", "UNCERTAIN")

# Whether a direction model is served per asset. All False: signal UNCERTAIN, confidence null (D33).
DIRECTION_SERVED = {"btc": False, "eth": False, "sol": False}  # D33

# Backtest (D34): cost per side on each change of position; random-signal baseline settings.
BACKTEST_FEE_PER_SIDE = 0.001  # D34
RANDOM_BASELINE_RUNS = 1000  # D34
RANDOM_BASELINE_P_BUY = 0.5  # D34
RANDOM_BASELINE_SEED = 0  # D34

# Serving (Phase 6a). A response gets a staleness note when the latest bar closed more than this many hours ago.
STALE_DATA_HOURS = 48  # CONTRACT.md 'note' rule (no D-number yet)
SHARPE_WINDOW_DAYS = 365  # D37: trailing daily log returns used for sharpe_ratio on /risk
MODEL_VERSION_PRICE = "baseline-last-value"  # D35: no price model approved
MODEL_VERSION_RISK = "persistence-pooled-pct"  # D36 (persistence vol_30d, D27; pooled percentile mapping)

# Data directories (D40). The evaluation snapshot is ml/data/raw + ml/reports/data as of 2026-10-17; splits are
# derived from n (D16, D18), so these files must not grow. Loader, validate, the serving gate and the refresh read
# ML_RAW_DIR / ML_VALIDATION_DIR, taken once from the environment. Unset, they are the snapshot directories.
EVALUATION_RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
EVALUATION_VALIDATION_DIR = Path(__file__).resolve().parent / "reports" / "data"
ML_RAW_DIR = Path(os.environ.get("ML_RAW_DIR") or EVALUATION_RAW_DIR)
ML_VALIDATION_DIR = Path(os.environ.get("ML_VALIDATION_DIR") or EVALUATION_VALIDATION_DIR)

# Daily refresh of the serving data, UTC "HH:MM" (D40).
REFRESH_UTC = "00:05"  # D40
