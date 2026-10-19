"""Project constants. The ONLY place for constants (docs/ARCHITECTURE.md, AGENTS rule 6)."""

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
