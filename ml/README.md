# AltInvest ML service (v2)

FastAPI service on port 8001 for BTC, ETH and SOL. The backend calls it over HTTP. It owns only
`/predict/{asset}` and `/risk/{asset}`; the AAI score is the backend's job.

## What it serves (and why)

No model beat its simple baseline on held-out data (ml/docs/STATUS.md), so the service serves the baselines
and says so in `note`:

- **Price** (D35): `prediction_30d = 0` (the "no change" forecast). `predicted_price`, `lower_bound` and
  `upper_bound` are null, and `model_version` is `"baseline-last-value"`.
- **Signal** (D33): always `"UNCERTAIN"`, with `confidence` null.
- **Risk** (D36): `risk_score` 0-100, higher = safer. It is today's 30-day volatility ranked against all
  BTC, ETH and SOL values up to today, so scores compare across assets. It is the same number on both routes.
- `volatility` is annualised (x sqrt(365)). `sharpe_ratio` covers the past 365 days (D37).
- Stale data (D38): if the latest daily bar closed more than 48 h ago, `note` ends with `data stale: last bar <date>`.

## Routes

| Route | Returns |
|---|---|
| `GET /predict/{asset}` | PredictionResponse (ml/docs/CONTRACT.md) |
| `GET /risk/{asset}` | RiskResponse (ml/docs/CONTRACT.md) |
| `GET /health` | `{"status": "ok", "model_version": {...}, "data_last_bar": {...}}` |
| `GET /debug/{asset}` | the inputs behind a response (not part of the contract) |

- `asset` is case-insensitive.
- An asset we do not cover returns **404**.
- A covered asset whose data is missing, failed validation, or does not match its validation report returns
  **503** (D40). Treat 503 as "keep your last good value".

## Run it

In Docker (from the repo root), with the rest of the stack or alone:

```powershell
docker compose up -d --build ml ml-refresh
curl.exe -s http://localhost:8001/health
```

- `ml` fetches and validates its own data into the `ml-data` volume at startup, then serves it.
- `ml-refresh` refreshes the data daily at 00:05 UTC. If a refresh fails, the previous data stays in use (D40).
- Inside the compose network the backend reaches the service at `http://ml:8001`.

Locally (Python 3.10-3.12, from the repo root):

```powershell
pip install -r ml/requirements.txt
python -m uvicorn ml.api.service:app --port 8001
```

Locally, the service reads the evaluation snapshot in `ml/data/raw` (git-ignored; fetched once in Phase 1).
`python -m ml.data.refresh` refuses to overwrite it unless given `--force`, because growing those files would
move the sealed test split (D40). To refresh into other folders, set `ML_RAW_DIR` and `ML_VALIDATION_DIR`.

## Tests and docs

- Tests: `python -m pytest ml` from the repo root. `ml/tests/test_contract.py` checks real responses against
  the schemas in ml/docs/CONTRACT.md.
- Start with ml/AGENTS.md. Then ml/docs/STATUS.md (what ran, how to verify), ml/docs/DECISIONS.md (D-numbers),
  ml/docs/CONTRACT.md (the API contract) and ml/docs/phases/ (one short explanation per phase).
