"""Project constants. The ONLY place for constants (docs/ARCHITECTURE.md, AGENTS rule 6)."""

import os
from pathlib import Path

# Asset id -> Binance spot symbol (docs/DATA.md). The single source of truth for the asset list.
ASSET_SYMBOLS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}

# Assets served in phases 1-7 (docs/REQUIREMENTS.md, D4). Lowercase ids; the API uppercases them.
ASSETS = tuple(ASSET_SYMBOLS)

# Forecast horizon in daily bars (D3). The served horizon, and the default of every horizon parameter.
HORIZON_DAYS = 30

# Phase 9 horizons in daily bars (D41). For each h: embargo = walk-forward step = h rows.
FORECAST_HORIZONS = (30, 7)

# EWMA (RiskMetrics) volatility decay, sigma2[t] = lambda x sigma2[t-1] + (1 - lambda) x r[t]^2 (D41).
EWMA_LAMBDA = 0.94

# Range (9.3, D43, D49): an 80% interval of the h-day log return, scored with the interval (Winkler) score at
# alpha = 1 - RANGE_COVERAGE. Pass also needs coverage within RANGE_COVERAGE_BOUNDS and each tail <= the max.
RANGE_COVERAGE = 0.80
RANGE_QUANTILES = (0.10, 0.90)
RANGE_COVERAGE_BOUNDS = (0.75, 0.85)  # D44
RANGE_TAIL_MISS_MAX = 0.15  # D44

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
MODEL_VERSION_RISK = "ewma-pooled-pct"  # D51 (EWMA vol, lambda EWMA_LAMBDA; D36 pooled percentile mapping)
RISK_MODEL_SERVED = True  # D51: EWMA risk served for every asset (was persistence vol_30d, D27)
RISK_VOL_COLUMN = "ewma_vol"  # D51: the served volatility measure (ml.features.features.ewma_vol)
LIVE_ALERT_MIN_WINDOWS = 6  # D46/D51: non-overlapping scored windows per asset before live_score may ALERT

# Data directories (D40). The evaluation snapshot is ml/data/raw + ml/reports/data as of 2026-10-17; splits are
# derived from n (D16, D18), so these files must not grow. Loader, validate, the serving gate and the refresh read
# ML_RAW_DIR / ML_VALIDATION_DIR, taken once from the environment. Unset, they are the snapshot directories.
EVALUATION_RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
EVALUATION_VALIDATION_DIR = Path(__file__).resolve().parent / "reports" / "data"
ML_RAW_DIR = Path(os.environ.get("ML_RAW_DIR") or EVALUATION_RAW_DIR)
ML_VALIDATION_DIR = Path(os.environ.get("ML_VALIDATION_DIR") or EVALUATION_VALIDATION_DIR)

# Daily refresh of the serving data, UTC "HH:MM" (D40).
REFRESH_UTC = "00:05"  # D40

# Live tracking (Phase 6d), files in ML_VALIDATION_DIR: what the API served each day, and how it turned out.
PREDICTION_LOG_FILE = "prediction_log.jsonl"
LIVE_SCORECARD_FILE = "live_scorecard.json"

# ---- Phase 10: NFT collections (docs/PLAN_NFT.md, D53-D62) ----
# OpenSea slugs, all ERC-721 on Ethereum (D54). Changing the list changes every pooled score: new D-number.
NFT_SLUGS = ("boredapeyachtclub", "mutant-ape-yacht-club", "pudgypenguins", "lilpudgys", "azuki",
             "doodles-official", "milady")
NFT_FLOOR_MAX_AGE_HOURS = 48  # D55: the as-of 00:00 UTC floor point may be at most this old, else the day is a gap
NFT_FLOOR_SPIKE_FACTOR = 2.0  # D66: a floor more than this factor away from the last accepted floor needs a second day
NFT_SALES_START = "2024-11-10"  # D56: sales window starts here (24 months before the 10.0 investigation)
NFT_PAYMENT_SYMBOLS = ("ETH", "WETH", "BETH")  # D56: other payment tokens are dropped and counted
NFT_SEAPORT_ADDRESSES = (  # D56: protocol_address of an OpenSea (Seaport 1.1, 1.4, 1.5, 1.6) sale
    "0x00000000006c3852cbef3e08e8df289169ede581", "0x00000000000001ad428e4906ae43d8f9852d0dd6",
    "0x00000000000000adc04c56bf30ac9d3c0aaf14dc", "0x0000000000000068f116a894984e2db1123eb395")
NFT_MARKETPLACES_LABEL = "Sales on OpenSea and Blur, as reported by OpenSea"  # D56 (A10)
NFT_WASH_ROUNDTRIP_DAYS = 30  # D57 R2
NFT_WASH_PRICE_BOUNDS = (0.10, 20.0)  # D57 R3: allowed sale price as a multiple of the floor of the sale date
NFT_ILLIQUID_MIN_SALES_7D = 10  # D58: illiquid if fewer wash-filtered sales in the last 7 days
NFT_LIQUIDITY_LABEL_BOUNDS = (33.0, 67.0)  # D58: Low < 33 <= Medium < 67 <= High
NFT_MIN_TRAIN_ROWS = 180  # D59: MIN_TRAIN_ROWS = 730 is longer than the floor history (786 days)
NFT_MIN_CONE_DAYS = 60  # D55: fewer days of floor history than this and no volatility is served
NFT_RISK_VOL_COLUMN = "vol_30d"  # D73: persistence served (the 10.3 EWMA approval was withdrawn by the D72 check)
MODEL_VERSION_NFT_RISK = "nft-persistence-pooled-pct"  # D59, D73: persistence floor vol, separate NFT pool
NFT_MODEL_FLOOR_COLUMN = "floor_eth_asof"  # D73: served floor series and liquidity R3 (D66 guard withdrawn)
NFT_REFRESH_UTC = "00:10"  # after the price refresh (00:05), before the backend pull (00:15, D61)

# NFT data directories (D62). Evaluation reads only the frozen snapshot under NFT_SNAPSHOT_ROOT; collectors,
# the refresh and serving read and write ML_NFT_DIR (the env var in Docker, ml/data/nft/live on the host).
NFT_DATA_DIR = Path(__file__).resolve().parent / "data" / "nft"
NFT_SNAPSHOT_ROOT = NFT_DATA_DIR / "snapshots"
NFT_SNAPSHOT_DATE = "2026-11-10"  # D64: the frozen evaluation snapshot (its last floor date); never rewritten
NFT_ITEM_SNAPSHOT = "2026-11-10-items"  # D68: traits and tokens with the missing metadata filled; never rewritten
ML_NFT_DIR = Path(os.environ.get("ML_NFT_DIR") or NFT_DATA_DIR / "live")
NFT_ITEM_SNAPSHOT_V2 = "2026-11-10-items-v2"  # D70: cleaned item sales, floor point before each sale; never rewritten
NFT_FV_SEALED_START = "2026-02-01"  # D71: sealed cutoff T for fair value (computed from the clean sales; freeze checks it)
