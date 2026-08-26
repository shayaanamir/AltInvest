# AltInvest ML Pipeline — End-to-End Flow

> A complete walkthrough of how raw price data becomes a live prediction API.

---

## Folder Map

```
ml/
├── data/
│   ├── raw/                        ← Raw hourly price CSVs (source of truth)
│   │   ├── btc_prices.csv          ← 17,521 rows, hourly, Jan 2024–Dec 2025
│   │   ├── eth_prices.csv
│   │   └── sol_prices.csv
│   ├── processed/                  ← Feature-engineered snapshots (not used by pipeline)
│   │   └── btc_features.csv        ← Snapshot only — pipeline builds features in-memory
│   ├── btc_mock.csv                ← Unused leftover — ignore
│   └── generate_mock_data.py       ← Script that generated the raw CSVs
│
├── features/
│   └── feature_engineering.py      ← Step 2: Transforms raw → feature DataFrame
│
├── models/
│   ├── forecaster.py               ← Step 3a: Prophet price forecaster
│   ├── classifier.py               ← Step 3b: RandomForest risk classifier
│   ├── lstm.py                     ← Step 3c: LSTM deep learning forecaster
│   └── artifacts/                  ← Saved trained models (.pkl / .keras)
│       ├── btc_prophet.pkl
│       ├── btc_rf_classifier.pkl
│       ├── btc_lstm.keras
│       ├── btc_lstm_scaler.pkl
│       ├── btc_lstm_report.json
│       └── btc_training_report.json
│
├── training/
│   └── train.py                    ← Step 3: Orchestrates full training pipeline
│
└── api/
    └── prediction_service.py       ← Step 4: FastAPI server — serves predictions
```

---

## End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRAINING PHASE                           │
│                                                                 │
│   data/raw/btc_prices.csv                                       │
│          │  (17,521 rows · hourly · asset, price, volume, ts)   │
│          │                                                       │
│          ▼  load_raw_csv("btc")                                 │
│   ┌──────────────────────────────┐                              │
│   │  feature_engineering.py      │                              │
│   │  build_features(df)          │                              │
│   │                              │                              │
│   │  · return_1h/1d/7d/30d       │  log returns                │
│   │  · volatility_14d            │  rolling std of return_1h   │
│   │  · ma_7d, ma_30d             │  price moving averages      │
│   │  · ma_cross                  │  +1 bullish / -1 bearish    │
│   │  · volume_change_pct         │  volume % change            │
│   │                              │                              │
│   │  dropna() → 16,801 rows      │  (720h warmup dropped)      │
│   └──────────────┬───────────────┘                              │
│                  │ feature DataFrame (in-memory)                │
│          ┌───────┼────────────────┐                             │
│          ▼       ▼                ▼                             │
│   ┌───────────┐ ┌─────────────┐ ┌──────────────┐              │
│   │forecaster │ │classifier   │ │  lstm.py      │              │
│   │.py        │ │.py          │ │  (separate    │              │
│   │           │ │             │ │   script)     │              │
│   │ Prophet   │ │ RandomForest│ │               │              │
│   │ daily     │ │ n=300       │ │ Conv1D(64)    │              │
│   │ resample  │ │ max_depth=8 │ │ +LSTM(75)     │              │
│   │ 30d ahead │ │ fwd 7d vol  │ │ +Dense(16)    │              │
│   │           │ │ risk label  │ │               │              │
│   └─────┬─────┘ └──────┬──────┘ └──────┬───────┘              │
│         │              │               │                        │
│         ▼              ▼               ▼                        │
│   btc_prophet.pkl  btc_rf_         btc_lstm.keras              │
│                    classifier.pkl  btc_lstm_scaler.pkl          │
│                                    btc_lstm_report.json         │
│                    btc_training_report.json                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        SERVING PHASE                            │
│                                                                 │
│   uvicorn api.prediction_service:app --port 8001               │
│          │                                                       │
│          ▼  startup (lifespan)                                  │
│   Loads artifacts into ModelCache (once, not per request)       │
│     · btc_prophet.pkl         → ProphetForecaster               │
│     · btc_rf_classifier.pkl   → RiskClassifier                 │
│     · btc_lstm_report.json    → LSTM cached report              │
│     · builds features live from btc_prices.csv                 │
│                                                                 │
│   GET /prediction/btc                                           │
│       1. Prophet.predict()    → predicted_price, prediction_30d │
│       2. RF.predict_latest()  → risk_score (P(high)×100)       │
│       3. LSTM report          → lstm_30d for agreement check    │
│       4. Agreement signal:                                       │
│          · Same direction?    → agreement = True                │
│          · trend: Bullish / Bearish / Neutral                   │
│          · signal: STRONG_BUY / STRONG_SELL / UNCERTAIN         │
│          · boosted_confidence: 0.95 (agree) or 0.60 (disagree)  │
│       5. Ensemble price:                                         │
│          · weighted avg of Prophet + LSTM by confidence         │
│       6. Risk score inversion: contract_score = 100 - internal  │
│       → Returns PredictionResponse JSON                         │
│                                                                 │
│   GET /risk/btc                                                 │
│       1. RF.predict_latest()  → risk_score                      │
│       2. compute_sharpe_ratio() → from return_1d column        │
│       → Returns RiskResponse JSON                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Breakdown

### Step 1 — Raw Data (`data/raw/`)

| File | Rows | Granularity | Date Range |
|---|---|---|---|
| `btc_prices.csv` | 17,521 | Hourly | Jan 2024 – Dec 2025 |
| `eth_prices.csv` | 17,521 | Hourly | Jan 2024 – Dec 2025 |
| `sol_prices.csv` | 17,521 | Hourly | Jan 2024 – Dec 2025 |

Columns: `asset`, `price`, `volume`, `timestamp`

Generated by `data/generate_mock_data.py`. When Person A's MongoDB is ready, only `load_raw_csv()` needs to be swapped — everything downstream stays unchanged.

---

### Step 2 — Feature Engineering (`features/feature_engineering.py`)

**Input**: raw DataFrame (17,521 rows)
**Output**: feature DataFrame (16,801 rows after 720h warmup dropped)

| Feature | Formula | Window |
|---|---|---|
| `return_1h` | `ln(price_t / price_{t-1})` | 1 hour |
| `return_1d` | `ln(price_t / price_{t-24})` | 24 hours |
| `return_7d` | `ln(price_t / price_{t-168})` | 7 days |
| `return_30d` | `ln(price_t / price_{t-720})` | 30 days |
| `volatility_14d` | rolling std of `return_1h` | 14 days (336h) |
| `ma_7d` | rolling mean of price | 7 days (168h) |
| `ma_30d` | rolling mean of price | 30 days (720h) |
| `ma_cross` | +1 bullish / -1 bearish / 0 neutral | based on ma_7d vs ma_30d |
| `volume_change_pct` | `(vol_t - vol_{t-1}) / vol_{t-1} × 100` | 1 hour |

> **Why 16,801 rows instead of 17,521?**
> The 30-day MA needs 720 hours of warmup. The first 720 rows are NaN and dropped via `dropna()`.

---

### Step 3a — Prophet Forecaster (`models/forecaster.py`)

**Model**: Facebook Prophet (multiplicative seasonality — handles crypto non-linearity)

**Internal steps**:
1. Resample hourly data → daily OHLC
2. Add extra regressors: `volatility_14d`, `ma_cross`, `volume_change_pct`
3. Fit Prophet on historical daily prices
4. Forecast 30 days forward
5. Extract `yhat`, `yhat_lower`, `yhat_upper` for day 30
6. Compute confidence from uncertainty interval width

**Output**:
```json
{
  "asset": "btc",
  "predicted_price": 106152.16,
  "prediction_30d": 12.5,
  "lower_bound": 103476.59,
  "upper_bound": 108942.28,
  "confidence": 0.95,
  "timestamp": "2026-05-18T14:00:00Z"
}
```

**Saved to**: `models/artifacts/btc_prophet.pkl`

---

### Step 3b — Risk Classifier (`models/classifier.py`)

**Model**: RandomForest (n=300, max_depth=8)

**Forward-looking target** (no circularity):

The label is based on **forward realized volatility over the next 7 days**
(168 hours), strictly after each observation row:

```
Risk_t = Std(return_1h_{t+1}, ..., return_1h_{t+168})
```

This does NOT overlap with the trailing `volatility_14d` feature, which
looks backward. The forward target is a genuinely predictive signal.

**Labeling strategy** (thresholds from training data only):
```
1. Compute forward realized vol for every row
2. Drop final ~168 rows (no future data available)
3. Chronological 80/20 split with 168-hour embargo
4. Compute 33rd/67th percentile thresholds from TRAINING split only
5. Apply those fixed thresholds to label both train and test:

   low    = below 33rd percentile of training forward vol
   medium = 33rd–67th percentile
   high   = above 67th percentile
```

The 168-hour embargo prevents training rows near the split boundary from
having forward labels that leak into the test period.

Cross-validation uses `TimeSeriesSplit(n_splits=5, gap=168)` to maintain
temporal ordering and prevent overlap between training forward-label
windows and validation periods.

**At inference**: `risk_score = P(high) × 100` → continuous 0–100 signal
interpreted as: "Probability that the asset will experience high realized
volatility during the next 7 days."

**Saved to**: `models/artifacts/btc_rf_classifier.pkl`

---

### Step 3c — LSTM (`models/lstm.py`)

**Model**: Conv1D(64) + LSTM(75) + Dense(16) + Dense(1)
Based on Murray et al. (2023) — same architecture that achieved RMSE=0.0222 on crypto.

**Pre-processing**:
1. First-order differencing (removes trend → stationarity)
2. MinMax normalisation (fit on train only, prevents data leakage)
3. Sliding window of 30 days as input sequence

**Run separately** (not part of `train.py`):
```bash
python models/lstm.py --asset btc
```

**Saved to**:
- `models/artifacts/btc_lstm.keras` — trained model weights
- `models/artifacts/btc_lstm_scaler.pkl` — MinMax scaler
- `models/artifacts/btc_lstm_report.json` — cached prediction result

---

### Step 3 — Training Orchestrator (`training/train.py`)

Runs Steps 1 + 2 + 3a + 3b in one command:

```bash
python training/train.py --asset btc
```

**Sequence**:
```
LOAD raw CSV from data/raw/btc_prices.csv
    ↓
BUILD features in-memory (build_features)
    ↓
FIT Prophet → save btc_prophet.pkl
    ↓
FIT RandomForest → save btc_rf_classifier.pkl
    ↓
WRITE btc_training_report.json
```

> LSTM is trained separately: `python models/lstm.py --asset btc`

---

### Step 4 — Prediction API (`api/prediction_service.py`)

**Start**:
```bash
uvicorn api.prediction_service:app --port 8001 --reload
```

**Startup**: loads all `.pkl` + `.json` artifacts into `ModelCache` once — not per request.

#### All Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /` | GET | Health ping |
| `GET /health` | GET | Lists loaded assets + service status |
| `GET /assets` | GET | Shows which assets are ready vs not trained |
| `GET /prediction/{asset}` | GET | **Main endpoint** — 30d price forecast + risk + signals |
| `GET /risk/{asset}` | GET | Risk score + volatility + Sharpe ratio |
| `GET /models/{asset}` | GET | A/B comparison: Prophet vs LSTM side by side |
| `GET /metrics/{asset}` | GET | Model evaluation metrics (MAE, RMSE, MAPE, R²) |
| `POST /retrain/{asset}` | POST | Re-runs training, reloads cache without restart |

#### `/prediction/{asset}` Response Fields

| Field | Description |
|---|---|
| `predicted_price` | Absolute USD price Prophet forecasts after 30 days |
| `prediction_30d` | % change from current price |
| `lower_bound` / `upper_bound` | 80% prediction interval |
| `confidence` | Prophet model confidence (0–1) |
| `risk_score` | 0–100 where **higher = safer** (inverted from internal) |
| `trend` | `Bullish` (>5%) / `Bearish` (<-5%) / `Neutral` |
| `agreement` | `true` if Prophet + LSTM predict the same direction |
| `signal` | `STRONG_BUY` / `STRONG_SELL` / `UNCERTAIN` |
| `boosted_confidence` | 0.95 if models agree, 0.60 if they disagree |
| `ensemble_price` | Confidence-weighted average of Prophet + LSTM prices |

---

## Run Everything From Scratch

```bash
# 1. (Optional) Regenerate raw data
python data/generate_mock_data.py

# 2. Train Prophet + RandomForest
python training/train.py --asset btc
python training/train.py --asset eth
python training/train.py --asset sol

# 3. Train LSTM separately
python models/lstm.py --asset btc
python models/lstm.py --asset eth
python models/lstm.py --asset sol

# 4. Start the API
uvicorn api.prediction_service:app --port 8001 --reload

# 5. Test
curl http://localhost:8001/prediction/btc
curl http://localhost:8001/risk/btc
curl http://localhost:8001/health
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| Models loaded once at startup | Fast inference (~10ms), no cold start per request |
| Prophet + LSTM ensemble | Two different model families reduce overfitting bias |
| Forward 7d realized-vol risk target | Genuinely predictive — no circularity with input features |
| 168h embargo in train/test split | Prevents training forward-label windows from leaking into test period |
| Thresholds from training data only | Prevents look-ahead bias in Low/Medium/High label assignment |
| TimeSeriesSplit CV with gap=168 | Temporal ordering + gap prevents forward-label overlap |
| `load_raw_csv()` isolated | Swap CSV → MongoDB without touching any downstream code |
| LSTM trained separately | TensorFlow optional; pipeline works without it (Prophet-only fallback) |
| Risk score inverted at API boundary | Internal: higher = riskier. Contract: higher = safer (user-friendly) |
| Features built in-memory | No dependency on `btc_features.csv` — always fresh from raw source |

