# PLAN — one phase at a time. Update docs/STATUS.md after each.

| # | Deliverable | Done when (testable) |
|---|---|---|
| 0 | Scaffold: config.py, requirements.txt, tests/, .gitignore (data, pkl) | `pytest` runs; `python -c "import ml.config"` works |
| 1 | data/fetch.py + validate.py for BTC | BTC daily CSV exists; validation.json shows no gaps (or listed), kurtosis > 1, |r| autocorr > 0 |
| 1b | Same for ETH, SOL | same checks |
| 2 | features + labels + splits | Leakage tests pass: shuffling future rows never changes features at t; labels equal future price ratios; splits have 30-day embargo |
| 3 | Baselines + metric functions | reports/{asset}/baselines.json written; unit tests for each metric |
| 4a | Price model | compared vs baselines on validation; report written even if it loses |
| 4b | Risk model (fwd 30d realised vol terciles, thresholds from train only) | Spearman and accuracy vs trailing-vol baseline reported |
| 4c | Direction model | calibration + baseline comparison reported |
| 5 | signal_logic.generate_signal + non-overlapping backtest | backtest.json with baselines and bootstrap CI; API/backtest import the same function |
| 6 | FastAPI :8001 (/predict, /risk, /health, /debug/...) | contract test validates real responses against CONTRACT.md schemas for all assets |
| 7 | Backend integration (Person B) | backend calls ML over HTTP end to end |
| 8 | NFTs | separate PLAN_NFT.md, started only after 7 |

## Order rationale
Evaluation before models, so every model is judged against baselines from day one.
