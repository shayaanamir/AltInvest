# PLAN — one phase at a time. Update docs/STATUS.md after each.

| # | Deliverable | Done when (testable) | How to verify |
|---|---|---|---|
| 0 | Scaffold: config.py, requirements.txt, tests/, .gitignore (data, pkl) | `pytest` runs; `python -c "import ml.config"` works | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 1 | data/fetch.py + validate.py for BTC | BTC daily CSV exists; validation.json shows no gaps (or listed), kurtosis > 1, |r| autocorr > 0 | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 1b | Same for ETH, SOL | same checks | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 2 | features + labels + splits | Leakage tests pass: shuffling future rows never changes features at t; labels equal future price ratios; splits have 30-day embargo | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 3 | Baselines + metric functions | reports/{asset}/baselines.json written; unit tests for each metric | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 4a | Price model | compared vs baselines on validation; report written even if it loses | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 4b | Risk model (fwd 30d realised vol terciles, thresholds from train only) | Spearman and accuracy vs trailing-vol baseline reported | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 4c | Direction model | calibration + baseline comparison reported | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 5 | signal_logic.generate_signal + non-overlapping backtest | backtest.json with baselines and bootstrap CI; API/backtest import the same function | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 6 | FastAPI :8001 (/predict, /risk, /health, /debug/...) | contract test validates real responses against CONTRACT.md schemas for all assets | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 7 | Backend integration (Person B) | backend calls ML over HTTP end to end | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 8 | NFTs | separate PLAN_NFT.md, started only after 7 | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |

## Order rationale
Evaluation before models, so every model is judged against baselines from day one.
