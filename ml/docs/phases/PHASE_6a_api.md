# Phase 6a: The API (serving baselines)

## 1. Goal
Run the ML service the backend calls: `GET /predict/{asset}` and `GET /risk/{asset}` on port 8001, plus `/health` and `/debug/{asset}`. No model beat its baseline in Phases 4-5, so the service serves the **baselines** (simple rules every model is compared against), and it says so in a `note`. Docker and the daily data refresh come in Phase 6b.

## 2. What we did
1. Added two medians to the backtest's random baseline and re-ran it. Every earlier number stayed the same.
2. Wrote down D35 (price fallback), D36 (how volatility becomes risk_score) and D37 (Sharpe on /risk).
3. Wrote the response builders, the FastAPI app and a read-only check of D36.
4. Wrote 24 tests. One of them, the **contract test**, calls the real service on the real data for BTC, ETH and SOL. `python -m pytest ml` gives 160 passed (ml/docs/STATUS.md).

## 3. Files
- `ml/serving/responses.py`: builds each response body. It reads features only, never labels.
- `ml/api/contract.py`: reads the two JSON schemas from docs/CONTRACT.md and checks bodies against them.
- `ml/api/service.py`: the FastAPI app (`python -m uvicorn ml.api.service:app --port 8001`).
- `ml/evaluation/risk_mapping_check.py`: writes `ml/reports/{asset}/risk_mapping_check.json` (report only).

## 4. How it works
- **/predict** (D35): `prediction_30d` = 0 (the "no change" forecast), `predicted_price` null, signal UNCERTAIN and confidence null (D33), all from `generate_signal`.
- **/risk**: `volatility` = today's 30-day volatility x sqrt(365). `sharpe_ratio` covers the past 365 days (D37).
- **risk_score** (D36): rank today's 30-day volatility among all BTC, ETH and SOL values up to today. Example: today 0.02, pool [0.01, 0.03, 0.02, 0.02, 0.05, 0.04]. 1 value is below and 2 are tied (each counts half), so p = 2/6 and risk_score = 100 x (1 - 1/3) = 66.7. Calm = high score = safer.
- Every body is checked against CONTRACT.md before it is sent. An unknown asset gets 404; data that failed validation gets 503.

## 5. Results
| | BTC | ETH | SOL |
|---|---|---|---|
| Served risk_score (from /risk) | 91.06 | 86.19 | 64.73 |
| D36 ranking of future volatility (sign flipped), risk_mapping_check.json | 0.288 | 0.507 | 0.204 |
| Raw vol_30d ranking (persistence), walkforward_baselines.json | 0.347 | 0.515 | 0.211 |

- SOL is the most volatile today, so it gets the lowest score.
- The pooled score ranks future volatility almost as well as raw volatility. BTC is 0.06 lower.

## 6. Decisions
- D35: price fallback (0% change, no price). D36: pooled percentile risk_score. D37: Sharpe over 365 days.
- D27 and D33 still apply: risk uses persistence, and direction is served as UNCERTAIN.

## 7. Limits
- Every response says "data stale" for now: the data ends 2026-10-17. The Phase 6b refresh fixes this.
- Adding an asset changes every risk_score (D36).
- If one asset fails validation, all three return 503.
- The date-time check needs the `rfc3339-validator` package. It is installed here but not pinned in requirements.txt.

## 8. Verify and next
- Verify: see "How to verify Phase 6a yourself" in ml/docs/STATUS.md.
- Next: Phase 6b (Dockerfile, compose service, daily data refresh). Then Phase 7: the backend calls this service.
