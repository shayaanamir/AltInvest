# AltInvest ML Pipeline

> **Person C — `dev-shail` branch**  
> FastAPI prediction service on **port 8001** · Prophet + RandomForest + LSTM  
> Supports BTC and ETH · All artifacts pre-trained and committed

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Prerequisites & Installation](#prerequisites--installation)
4. [Step-by-Step: Running the Pipeline](#step-by-step-running-the-pipeline)
   - [Step 1 — Generate Mock Data](#step-1--generate-mock-data)
   - [Step 2 — Train Prophet + Risk Classifier](#step-2--train-prophet--risk-classifier)
   - [Step 3 — Train LSTM Model (optional)](#step-3--train-lstm-model-optional)
   - [Step 4 — Start the API Server](#step-4--start-the-api-server)
5. [API Endpoints Reference](#api-endpoints-reference)
   - [GET /](#get-)
   - [GET /health](#get-health)
   - [GET /assets](#get-assets)
   - [GET /prediction/{asset}](#get-predictionasset)
   - [GET /risk/{asset}](#get-riskasset)
   - [GET /models/{asset}](#get-modelsasset)
   - [POST /retrain/{asset}](#post-retrainasset)
6. [Callable Python Functions (No HTTP Required)](#callable-python-functions-no-http-required)
7. [Backend Integration Guide](#backend-integration-guide)
8. [Risk Score Contract Explained](#risk-score-contract-explained)
9. [Artifacts Reference](#artifacts-reference)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Raw CSV Data
    │
    ▼
feature_engineering.py   ←── returns, volatility, MAs, volume signals
    │
    ├──▶ forecaster.py   (Prophet)       ──▶ 30-day price forecast
    ├──▶ classifier.py   (RandomForest)  ──▶ risk label + score + Sharpe ratio
    └──▶ lstm.py         (LSTM / GBM)    ──▶ deep-learning price forecast
    │
    ▼
training/train.py        ──▶ orchestrates everything, saves .pkl / .keras artifacts
    │
    ▼
api/prediction_service.py  ──▶  FastAPI  :8001
    ├── GET /prediction/{asset}    (main backend contract)
    ├── GET /risk/{asset}          (dedicated risk + Sharpe endpoint)
    ├── GET /models/{asset}        (Prophet vs LSTM A/B comparison)
    ├── GET /health
    ├── GET /assets
    └── POST /retrain/{asset}
```

---

## Directory Structure

```
ml/
├── api/
│   └── prediction_service.py   # FastAPI app — all endpoints + callable functions
├── data/
│   ├── generate_mock_data.py   # GBM-based synthetic data generator
│   └── raw/
│       ├── btc_prices.csv      # ✅ Already generated
│       └── eth_prices.csv      # ✅ Already generated
├── features/
│   └── feature_engineering.py  # Returns, volatility, MAs, volume features
├── models/
│   ├── forecaster.py           # ProphetForecaster class
│   ├── classifier.py           # RiskClassifier class + compute_sharpe_ratio()
│   ├── lstm.py                 # LSTM / GBM fallback model
│   └── artifacts/              # ✅ Pre-trained — all .pkl and .keras files present
│       ├── btc_prophet.pkl
│       ├── btc_rf_classifier.pkl
│       ├── btc_lstm.keras
│       ├── btc_lstm_report.json
│       ├── btc_training_report.json
│       ├── eth_prophet.pkl
│       ├── eth_rf_classifier.pkl
│       ├── eth_lstm.keras
│       ├── eth_lstm_report.json
│       └── eth_training_report.json
├── training/
│   └── train.py                # End-to-end training orchestrator (CLI)
├── requirements.txt
└── README.md
```

---

## Prerequisites & Installation

### Python Version
Python **3.10 or 3.11** recommended (TensorFlow constraint).

### Install dependencies

```bash
# From the ml/ directory
pip install -r requirements.txt
```

Key packages:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥ 0.111 | API framework |
| `uvicorn[standard]` | ≥ 0.29 | ASGI server |
| `prophet` | ≥ 1.1.5 | 30-day forecasting |
| `scikit-learn` | ≥ 1.4 | RandomForest classifier |
| `tensorflow` | ≥ 2.16 | LSTM model (optional) |
| `xgboost` | ≥ 2.0 | LSTM fallback model |
| `pandas` / `numpy` | latest | Data processing |

> **TensorFlow is optional.** If not installed, `lstm.py` automatically falls back to a Gradient Boosting model with the same output contract.

---

## Step-by-Step: Running the Pipeline

> **Note:** All commands below are run from **inside the `ml/` directory**.

### Step 1 — Generate Mock Data

> ⚠️ **Skip this step** — `btc_prices.csv` and `eth_prices.csv` are already present in `ml/data/raw/`. Only run this if you need to regenerate fresh data.

```bash
python data/generate_mock_data.py
```

Generates `ml/data/raw/btc_prices.csv` and `ml/data/raw/eth_prices.csv` using Geometric Brownian Motion with regime shifts. Schema:

```
asset, price, volume, timestamp
btc, 42150.23, 1532.8, 2024-01-01T00:00:00Z
...
```

---

### Step 2 — Train Prophet + Risk Classifier

> ⚠️ **Skip this step** — artifacts are already committed in `ml/models/artifacts/`. Only run this if you need to retrain.

```bash
# Train both models for BTC
python training/train.py --asset btc

# Train both models for ETH
python training/train.py --asset eth
```

This runs the full pipeline:
1. Loads `data/raw/{asset}_prices.csv`
2. Runs `feature_engineering.build_features()`
3. Fits `ProphetForecaster` → saves `artifacts/{asset}_prophet.pkl`
4. Fits `RiskClassifier` → saves `artifacts/{asset}_rf_classifier.pkl`
5. Writes `artifacts/{asset}_training_report.json`

Optional flags:
```bash
python training/train.py --asset btc --dry-run   # skip saving artifacts
```

---

### Step 3 — Train LSTM Model (optional)

> ⚠️ **Skip this step** — LSTM `.keras` artifacts are already committed. Only run if retraining.

```bash
# Train LSTM for BTC
python models/lstm.py --asset btc

# Train LSTM for ETH
python models/lstm.py --asset eth
```

Saves:
- `artifacts/{asset}_lstm.keras` (or `_lstm_fallback.pkl` if no TensorFlow)
- `artifacts/{asset}_lstm_report.json`
- `artifacts/{asset}_lstm_scaler.pkl`

---

### Step 4 — Start the API Server

```bash
# From ml/ directory
uvicorn api.prediction_service:app --port 8001 --reload
```

Expected startup output:
```
INFO  AltInvest Prediction Service — starting up
INFO  [BTC] Prophet loaded from artifact.
INFO  [BTC] Classifier loaded from artifact.
INFO  [BTC] LSTM report loaded from artifact.
INFO  [ETH] Prophet loaded from artifact.
INFO  [ETH] Classifier loaded from artifact.
INFO  [ETH] LSTM report loaded from artifact.
INFO  Startup complete. Loaded assets: ['btc', 'eth']
INFO  Uvicorn running on http://0.0.0.0:8001
```

Interactive API docs: **http://127.0.0.1:8001/docs**  
ReDoc: **http://127.0.0.1:8001/redoc**

---

## API Endpoints Reference

All endpoints are served at `http://127.0.0.1:8001`

---

### GET /

Quick liveness check.

```bash
curl http://127.0.0.1:8001/
```

```json
{
  "service": "AltInvest ML Prediction Service",
  "status": "running",
  "port": 8001
}
```

---

### GET /health

Detailed health check — shows which assets have models loaded.

```bash
curl http://127.0.0.1:8001/health
```

```json
{
  "status": "healthy",
  "loaded_assets": ["btc", "eth"],
  "artifacts_dir": "/path/to/ml/models/artifacts",
  "supported_assets": ["btc", "eth"]
}
```

| `status` value | Meaning |
|---|---|
| `"healthy"` | At least one asset loaded |
| `"degraded"` | No assets loaded (training not run yet) |

---

### GET /assets

Lists all supported assets and their model readiness.

```bash
curl http://127.0.0.1:8001/assets
```

```json
{
  "supported": ["btc", "eth"],
  "ready": ["btc", "eth"],
  "not_ready": []
}
```

---

### GET /prediction/{asset}

**Primary endpoint consumed by the backend.** Returns 30-day Prophet price forecast + risk classification.

```bash
# BTC
curl http://127.0.0.1:8001/prediction/btc

# ETH
curl http://127.0.0.1:8001/prediction/eth
```

**Response:**
```json
{
  "asset": "BTC",
  "predicted_price": 106152.16,
  "prediction_30d": 12.5,
  "lower_bound": 103476.59,
  "upper_bound": 108942.28,
  "confidence": 0.95,
  "risk_label": "high",
  "risk_score": 32.8,
  "timestamp": "2026-05-18T14:00:00Z"
}
```

**Field definitions:**

| Field | Type | Description |
|---|---|---|
| `asset` | string | Asset ticker (`"BTC"` or `"ETH"`) |
| `predicted_price` | float | Absolute price forecast in USD (30 days out) |
| `prediction_30d` | float | % price change from today's price |
| `lower_bound` | float | 80% prediction interval lower bound |
| `upper_bound` | float | 80% prediction interval upper bound |
| `confidence` | float | Model confidence 0–1 (derived from interval width) |
| `risk_label` | string | `"low"` \| `"medium"` \| `"high"` |
| `risk_score` | float | **Contract score 0–100 where HIGHER = LOWER risk** |
| `timestamp` | string | UTC ISO-8601 time of prediction |

> ⚠️ **Risk score note:** `risk_score` here is the **inverted** contract score. A score of `32.8` means HIGH risk (high internal probability → low contract score). See [Risk Score Contract Explained](#risk-score-contract-explained).

**Error responses:**

| Code | Reason |
|---|---|
| `404` | Asset not in `["btc", "eth"]` |
| `503` | Models not loaded — run training first |
| `500` | Prediction pipeline error |

---

### GET /risk/{asset}

**Dedicated risk endpoint** — returns risk score, volatility, and Sharpe ratio. Separate from the prediction endpoint as per backend contract.

```bash
# BTC
curl http://127.0.0.1:8001/risk/btc

# ETH
curl http://127.0.0.1:8001/risk/eth
```

**Response:**
```json
{
  "asset": "BTC",
  "risk_score": 32.8,
  "volatility": 0.018432,
  "sharpe_ratio": 1.4012,
  "timestamp": "2026-05-18T14:00:00Z"
}
```

**Field definitions:**

| Field | Type | Description |
|---|---|---|
| `asset` | string | Asset ticker |
| `risk_score` | float | Contract score [0–100] — **HIGHER = LOWER risk (better)** |
| `volatility` | float | Most recent 14-day rolling std of 1-hour log returns |
| `sharpe_ratio` | float | Annualised Sharpe ratio: `mean(return_1d) / std(return_1d) × √252` |
| `timestamp` | string | UTC ISO-8601 time of calculation |

---

### GET /models/{asset}

**A/B comparison** — returns Prophet and LSTM predictions side-by-side for evaluation.

```bash
curl http://127.0.0.1:8001/models/btc
```

**Response:**
```json
{
  "asset": "btc",
  "prophet": {
    "asset": "BTC",
    "predicted_price": 106152.16,
    "prediction_30d": 12.5,
    "lower_bound": 103476.59,
    "upper_bound": 108942.28,
    "confidence": 0.95,
    "timestamp": "2026-05-18T14:00:00Z"
  },
  "lstm": {
    "asset": "btc",
    "model": "lstm",
    "architecture": "Conv1D(64)+LSTM(75)+Dense(16) — Murray et al. 2023",
    "prediction_30d": 78770.95,
    "lower_bound": 48152.15,
    "upper_bound": 109389.76,
    "confidence": 0.85,
    "timestamp": "2026-05-18T14:00:00Z"
  }
}
```

> If LSTM has not been trained, the `"lstm"` field is `null`.

---

### POST /retrain/{asset}

Triggers full retraining for an asset **without restarting the server**. Hot-reloads the model cache.

```bash
# Retrain BTC models
curl -X POST http://127.0.0.1:8001/retrain/btc

# Retrain ETH models
curl -X POST http://127.0.0.1:8001/retrain/eth
```

**Response:**
```json
{
  "asset": "btc",
  "status": "success",
  "message": "Models retrained and reloaded for BTC.",
  "duration_sec": 8.42
}
```

> This is a synchronous operation (~5–15 seconds). Use it when new data arrives from the data engineering team.

---

## Callable Python Functions (No HTTP Required)

The service exposes two importable functions that **do not require the HTTP server to be running**. Person B can call these directly from Python:

```python
from ml.api.prediction_service import get_prediction, get_risk
```

### `get_prediction(asset: str) → dict`

Mirrors `GET /prediction/{asset}` exactly.

```python
from ml.api.prediction_service import get_prediction

result = get_prediction("BTC")
print(result)
# {
#   "asset":           "BTC",
#   "predicted_price": 106152.16,
#   "prediction_30d":  12.5,
#   "lower_bound":     103476.59,
#   "upper_bound":     108942.28,
#   "confidence":      0.95,
#   "risk_label":      "high",
#   "risk_score":      32.8,       # contract score (higher = lower risk)
#   "timestamp":       "2026-05-18T14:00:00Z"
# }
```

### `get_risk(asset: str) → dict`

Mirrors `GET /risk/{asset}` exactly.

```python
from ml.api.prediction_service import get_risk

result = get_risk("BTC")
print(result)
# {
#   "asset":        "BTC",
#   "risk_score":   32.8,
#   "volatility":   0.018432,
#   "sharpe_ratio": 1.4012,
#   "timestamp":    "2026-05-18T14:00:00Z"
# }
```

**Both functions:**
- Are **synchronous** (no `await` needed)
- **Lazy-load** model artifacts on first call (no manual setup)
- Raise `ValueError` for unsupported assets
- Raise `RuntimeError` if artifacts are missing

---

## Backend Integration Guide

### Option A — HTTP (recommended for production)

The backend (Node.js / FastAPI on port 8000) calls the ML service at port 8001 via HTTP.

```
Backend :8000  ──────────────────────▶  ML Service :8001
                GET /prediction/btc
                GET /risk/btc
```

**Example (Python `httpx` / `requests`):**

```python
import httpx

ML_BASE = "http://127.0.0.1:8001"

def fetch_prediction(asset: str) -> dict:
    resp = httpx.get(f"{ML_BASE}/prediction/{asset}", timeout=10)
    resp.raise_for_status()
    return resp.json()

def fetch_risk(asset: str) -> dict:
    resp = httpx.get(f"{ML_BASE}/risk/{asset}", timeout=10)
    resp.raise_for_status()
    return resp.json()
```

**Example (Node.js `fetch`):**

```javascript
const ML_BASE = "http://127.0.0.1:8001";

async function fetchPrediction(asset) {
  const res = await fetch(`${ML_BASE}/prediction/${asset}`);
  if (!res.ok) throw new Error(`ML service error: ${res.status}`);
  return res.json();
}

async function fetchRisk(asset) {
  const res = await fetch(`${ML_BASE}/risk/${asset}`);
  if (!res.ok) throw new Error(`ML service error: ${res.status}`);
  return res.json();
}
```

---

### Option B — Direct Python Import (no HTTP server)

Useful for testing, Jupyter notebooks, or tightly coupled Python services.

```python
import sys
sys.path.insert(0, "/path/to/AltInvest/ml")

from ml.api.prediction_service import get_prediction, get_risk

prediction = get_prediction("BTC")
risk       = get_risk("ETH")
```

---

### Running Both Services Together

Start both services in separate terminals:

**Terminal 1 — ML Service:**
```bash
cd ml/
uvicorn api.prediction_service:app --port 8001 --reload
```

**Terminal 2 — Backend:**
```bash
cd backend/
# your backend start command here
```

**Verify connection:**
```bash
curl http://127.0.0.1:8001/health
```

---

## Risk Score Contract Explained

This is a critical detail to avoid integration bugs.

| Context | Score range | Meaning of HIGH score |
|---|---|---|
| **Internal classifier** (`classifier.py`) | 0–100 | HIGH score = HIGH risk (P(high) × 100) |
| **API contract** (`/prediction`, `/risk`) | 0–100 | HIGH score = LOW risk (BETTER) |

The conversion applied at the API boundary:

```python
contract_risk_score = 100 - internal_risk_score
```

**Example:**

```
Internal:  BTC risk_score = 67.2  →  label = "HIGH"
Contract:  BTC risk_score = 32.8  →  lower number = more dangerous
```

So when the backend sees `risk_score = 10`, that means **very high risk**. When it sees `risk_score = 90`, that means **very safe**.

---

## Artifacts Reference

All artifacts live in `ml/models/artifacts/`. Both BTC and ETH are pre-trained.

| File | Description | Size |
|---|---|---|
| `btc_prophet.pkl` | Trained Prophet forecaster | ~116 KB |
| `btc_rf_classifier.pkl` | Trained RandomForest classifier | ~6.9 MB |
| `btc_lstm.keras` | Trained LSTM model (TensorFlow) | ~545 KB |
| `btc_lstm_scaler.pkl` | MinMaxScaler for LSTM inputs | ~1 KB |
| `btc_lstm_report.json` | LSTM performance summary | — |
| `btc_training_report.json` | Prophet + RF training summary | — |
| `eth_*` | Same set for ETH | — |

---

## Troubleshooting

### `ModuleNotFoundError` when starting the API
Run uvicorn from inside the `ml/` directory, not from the repo root:
```bash
cd ml/
uvicorn api.prediction_service:app --port 8001 --reload
```

### `503 Model not loaded`
Artifacts are missing. Run training:
```bash
python training/train.py --asset btc
python training/train.py --asset eth
```

### Port 8001 already in use
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <pid> /F

# macOS / Linux
lsof -ti:8001 | xargs kill
```

### TensorFlow not installed (LSTM fallback)
The LSTM endpoint still works — it uses an XGBoost Gradient Boosting fallback automatically. The `lstm` field in `/models/{asset}` will show `"model": "lstm_fallback"`.

### Retrain without restarting
After new data arrives, use the retrain endpoint instead of restarting:
```bash
curl -X POST http://127.0.0.1:8001/retrain/btc
```
