# PLAN — one phase at a time. Update docs/STATUS.md after each.

| # | Deliverable | Done when (testable) | How to verify |
|---|---|---|---|
| 0 | Scaffold: config.py, requirements.txt, tests/, .gitignore (data, pkl) | `pytest` runs; `python -c "import ml.config"` works | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 1 | data/fetch.py + validate.py for BTC | BTC daily CSV exists; validation.json shows no gaps (or listed), kurtosis > 1, |r| autocorr > 0 | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 1b | Same for ETH, SOL | same checks | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 2 | features + labels + splits | Leakage tests pass: shuffling future rows never changes features at t; labels equal future price ratios; splits have 30-day embargo | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 3 | Baselines + metric functions | reports/{asset}/baselines.json written; unit tests for each metric | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 4a | Risk model (regression on log fwd 30d realised vol, D24; class metrics with fold thresholds) | walkforward_risk.json per asset: Spearman and class metrics vs trailing-vol baseline, approval verdict per D25; pytest passes | "How to verify Phase 4a yourself" in docs/STATUS.md |
| 4b | Price model | compared vs baselines by walk-forward (D21, D28); report written even if it loses | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 4c | Direction model | calibration + baseline comparison reported, evaluated by walk-forward (D21) | "How to verify Phase 4c yourself" in docs/STATUS.md |
| 5 | signal_logic.generate_signal + non-overlapping backtest | backtest.json with baselines and bootstrap CI; API/backtest import the same function | "How to verify Phase 5b yourself" in docs/STATUS.md |
| 6 | FastAPI :8001 (/predict, /risk, /health, /debug/...) | contract test validates real responses against CONTRACT.md schemas for all assets | 6a: "How to verify Phase 6a yourself" in docs/STATUS.md. 6b (Docker/compose, daily refresh): filled in when completed |
| 7 | Backend integration (Person B) | backend calls ML over HTTP end to end | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 8 | NFTs | separate PLAN_NFT.md, started only after 7 | Filled in docs/STATUS.md when the phase is completed (AGENTS rule 15) |
| 9 | Forecasting v2 (price, price range, risk, direction at 30 and 7 days; D41-D47): steps 9.0-9.8 in docs/PLAN_FORECAST.md, each with a planner checkpoint | Every part has a walk-forward report with a D44 verdict; the sealed test ran once (test_final.json); served fields pass the contract test; parts that lost keep their baselines | "How to verify Phase 9 yourself" in docs/STATUS.md (step 9.8) |
| 10 | NFTs (Phase 8 plan, run as Phase 10): collection floor history and volatility cone, liquidity, collection risk, item fair value; steps 10.0-10.9 in docs/PLAN_NFT.md with review amendments A1-A10 (D53-D62), each with a planner checkpoint | Every part has a walk-forward report with a D44-style verdict (D59, D60); the sealed test ran once (10.8); snapshots are hashed (D62); NFT endpoints validate against CONTRACT.md | "How to verify Phase 10 yourself" in docs/STATUS.md (step 10.9) |

## Order rationale
Evaluation before models, so every model is judged against baselines from day one.
