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

# Annualisation for Sharpe and volatility: sqrt(365) (docs/EVALUATION.md rule 5).
ANNUALISATION_DAYS = 365
