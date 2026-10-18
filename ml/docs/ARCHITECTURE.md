# ARCHITECTURE

## Layout
```
ml/
  AGENTS.md
  config.py                # assets, horizon, split dates, thresholds: the ONLY place for constants
  data/                    # git-ignored. fetch script is tracked, data is not
    fetch.py               # Binance public klines -> data/raw/{asset}_1d.csv
    validate.py            # writes data/raw/{asset}_validation.json
    raw/
  features/features.py     # backward-looking features only
  labels/labels.py         # forward-looking targets (training/eval only)
  evaluation/              # splits, metrics, baselines, backtest
  models/                  # price.py, risk.py, direction.py
  signal/signal_logic.py   # the ONE generate_signal()
  api/service.py           # FastAPI :8001, validates against CONTRACT.md
  artifacts/{asset}/       # model files + metadata.json (git-ignored files, metadata tracked)
  reports/{asset}/         # baselines.json, models.json, backtest.json (tracked)
  tests/
```

## Data flow
raw daily OHLCV -> features (backward) + labels (forward) -> chronological split with embargo
-> baselines -> models -> evaluation reports -> signal -> API.

## Principles
- Daily bars. Horizon = 30 rows (config.HORIZON_DAYS).
- Features use data <= t. Labels use data > t. Labels exist only in training/evaluation code, never in CSVs.
- API reads artifacts + the latest data. It never trains. Training is a CLI: `python -m ml.training.run --asset btc`.
- `generate_signal()` is the only signal logic; API and backtest both import it.
- Confidence/interval come from measured backtest coverage, stored in artifact metadata. Nothing hard-coded.
- Metrics endpoint (if any) reads report JSON.
- Debug extras (probabilities, regime) only at `/debug/...`.
