# Phase 4.0: Walk-forward harness

## 1. Goal
Build the testing machine every model will go through. Phase 3 scored baselines on one validation split with only 10-16 independent observations, which is too few to trust. **Walk-forward** repeatedly trains on the past and predicts the next 30 days, using all history before the test split. The test split stays **sealed**: it is used once, at the very end. No models are trained yet; the baselines are run through the machine to set the bar.

## 2. What we did
1. Added D21 (walk-forward rules) and D22 (how a model gets approved) to docs/DECISIONS.md.
2. Wrote the harness and a runner, and connected the Phase 3 baselines to it.
3. Wrote 7 tests on hand-made fixtures (not market data). `python -m pytest ml` gives 66 passed (ml/docs/STATUS.md).
4. Ran it for BTC, ETH and SOL.

## 3. Files
- `ml/evaluation/walkforward.py`: makes the folds and runs any model on them; refuses any test row.
- `ml/evaluation/run_walkforward.py`: builds the data without test rows and writes the report.
- `ml/evaluation/baselines.py`: the Phase 3 baselines wrapped in the harness's fit/predict interface.
- `ml/tests/test_walkforward.py`: the tests.
- `ml/reports/{btc,eth,sol}/walkforward_baselines.json`: tracked evidence.

## 4. How it works
- Each **fold** has an **origin** t. It trains on rows before t-30 and predicts rows t to t+29. The 30-row gap means no training label sees the predicted period.
- **Expanding window**: the first fold trains on 730 rows (2 years), and each later fold adds 30 more rows.
- Thresholds (D19) and baseline settings are refit inside every fold, from that fold's training rows only.
- Predictions from all folds are **pooled** and scored together with the Phase 3 metrics.
- Example (BTC, from the report): 68 folds, origins from 2019-10-16 to 2025-04-17, 2031 pooled rows.

## 5. Results
Pooled walk-forward, from `ml/reports/{asset}/walkforward_baselines.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Folds / pooled rows / n_effective | 68 / 2031 / 67.7 | 68 / 2031 / 67.7 | 37 / 1104 / 36.8 |
| Price MAE: last-value / drift | 5456.61 / 5583.06 | 346.78 / 361.15 | 22.56 / 23.34 |
| Direction balanced accuracy: momentum | 0.3162 | 0.3649 | 0.326 |
| Risk persistence balanced accuracy | 0.4378 | 0.468 | 0.329 |
| Risk persistence Spearman [95% CI] | 0.347 [0.161, 0.514] | 0.515 [0.333, 0.659] | 0.211 [0.020, 0.442] |

- n_effective is 4 to 7 times larger than one validation split, so the confidence intervals are narrower.
- Last-value stays the price baseline to beat. Momentum is about chance (balanced accuracy near 1/3).
- Over the longer history, trailing volatility does rank future volatility (all CIs above 0). That is the risk bar a model must clear.

## 6. Decisions
- D21: expanding walk-forward on rows before the test split, origin every 30 rows, thresholds refit per fold.
- D22: a model is approved only if it beats the best baseline AND a paired bootstrap CI of the difference excludes 0.
- The first fold trains on exactly 730 rows (origin at row 760).

## 7. Limits
- The baselines produce no probabilities, so ROC-AUC and calibration are still null.
- The last fold is shorter (21 rows for BTC/ETH, 24 for SOL), because predictions must stop 30 rows before the test split.
- Neighbouring pooled rows overlap, so the CIs use 30-row blocks; true dependence may last up to about 60 rows, so the CIs may be slightly too narrow.
- Per-fold thresholds mean a row's "actual" class depends on its fold.

## 8. Verify and next
- Verify: see "How to verify Phase 4.0 yourself" in ml/docs/STATUS.md.
- Next: Phase 4a plugs a price model into the same harness and compares it with these numbers under D22.
