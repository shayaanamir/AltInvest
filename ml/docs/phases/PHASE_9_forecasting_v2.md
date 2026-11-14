# Phase 9: Forecasting v2 (price, range, risk, direction)

## 1. Goal
Test stronger models (Prophet, LSTM, LightGBM, GARCH, EWMA) honestly against the simple baselines, at 30 and 7 days, and serve only the parts that win. It comes after Phase 7, once the backend reads the ML service. "Nothing won" was an allowed result.

## 2. What we did
1. Wrote the rules first (D41-D49): return targets, embargo = step = horizon, at most 4 configs per model, approval by a paired 95% CI on the last 40% of walk-forward folds (D44).
2. Added 7-day labels, an EWMA volatility function and a training environment (`ml/requirements-train.txt`).
3. Ran price (9.2), range (9.3), risk (9.4) and direction (9.5) in walk-forward. Fixed one protocol defect along the way: Prophet had been fitted without the prices known on the day (D48).
4. Wrote the sealed-test rules (D50), then ran the [sealed test](../GLOSSARY.md) once (9.6).
5. Served the one winner, EWMA risk, for all assets (D51, 9.7).

## 3. Files
- `ml/evaluation/run_walkforward_{price_v2,range,risk_v2,direction_v2}.py`, `run_sealed_test.py`: the evaluations; reports in `ml/reports/{asset}/`.
- `ml/models/{price_v2,lstm,range_v2,risk_v2,direction_v2}.py`: the candidates.
- `ml/evaluation/approval.py`, `walkforward_history.py`, `walkforward_pooled.py`, `interval_metrics.py`, `part_runner.py`: shared logic.
- `ml/serving/responses.py`: now serves EWMA risk.

## 4. How it works
- **EWMA** volatility updates every day: today's variance = 0.94 x yesterday's + 0.06 x today's squared return. Recent days count more than in a plain 30-day average.
- **QLIKE** scores a volatility forecast; lower is better and 0 is perfect. Example (made-up numbers): forecast vol 0.02, actual 0.03 gives ratio s/p = 2.25 and QLIKE = 2.25 - ln 2.25 - 1 = 0.44.
- The **D36 risk_score** is 100 x (1 - percentile of today's EWMA vol among all three assets' EWMA history), so a higher score means safer.

## 5. Results
102 trials in total (`ml/reports/test_final_summary.json`): price 60, range 18, risk 12, direction 12.

| Part | Walk-forward result (source report) | Sealed test | Served? |
|---|---|---|---|
| Price | 0 of 60 approved; corrected Prophet about level with last value (`walkforward_price_v2.json`) | not run | No (D35) |
| Range | 0 of 12 approved; the baseline band itself is mis-calibrated (`walkforward_range.json`) | baseline band coverage 0.70-0.75, lower tail misses 0.16-0.17 | No |
| Risk | EWMA approved for BTC and ETH at 30 and 7 days; SOL tie; GARCH 0 (`walkforward_risk_v2.json`) | EWMA QLIKE lower for all; BTC 30d gain +0.0915 [-0.0020, 0.2439] | **Yes, all assets (D51)** |
| Direction | ETH logreg approved but its backtest is below buy-and-hold; LightGBM 0 (`walkforward_direction_v2.json`) | not run | No (D33) |

Range was not served because no candidate beat the vol_30d band, and the band itself fails the 75-85% coverage rule on the sealed test for every asset (`test_final.json`).

## 6. Decisions
- D41-D47: horizons, candidates, metrics, approval, consistency, monitoring, 7-day field.
- D48: inputs known at t may be used; only labels need the embargo.
- D49: shorter plan v2. D50: sealed-test configs and the "not worse" rule. D51: serve EWMA risk for all assets.

## 7. Limits
- Many trials (102) with small confirmation sets (n_effective about 28 at 30 days), so one or two "wins" could be luck. The sealed test has an n_effective of only 10-16 at 30 days.
- BTC passes the test only as "not worse": its CI includes 0.
- Live scoring needs at least 6 non-overlapping 30-day windows (about 6 months) before it can raise an alert.

## 8. Verify and next
- Verify: see "How to verify Phase 9 yourself" in ml/docs/STATUS.md.
- Next: Person B checks the new risk_score values and note text (the fields are unchanged); the live scorecard starts scoring on 2026-11-30.

## Later change (Phase 10 step 10.9, 2026-11-14)
EWMA risk is no longer served. The owner replaced D49's per-model-type confirmation with top-only selection (D81). Re-reading the logged Phase 9 results that way (`ml/reports/d49_audit_risk.json`, nothing re-run): GARCH ranks first for every asset and horizon, and its confirmation CI includes 0, so no risk config is approved. Crypto risk serves persistence vol_30d again, and the price chart's cone uses it (D82). The ETH direction approval still stands under top-only, but it is not served (D33).
