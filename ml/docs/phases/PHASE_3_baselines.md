# Phase 3: Baselines and metrics

## 1. Goal
Before building any model, measure how well simple fixed rules (**baselines**) do, and write the scoring functions (**metrics**) every later model will use. A model is only worth shipping if it beats these numbers (docs/EVALUATION.md). No models are trained here.

## 2. What we did
1. Added D20 to docs/DECISIONS.md: because validation and test are mostly FLAT and low risk, every report shows balanced accuracy and macro-F1 next to accuracy, ranks risk with Spearman, and states n_effective.
2. Wrote the metrics, the baseline rules and a runner script.
3. Wrote 19 metric tests on hand-made fixtures (not market data). `python -m pytest ml` gives 52 passed (ml/docs/STATUS.md).
4. Ran the baselines for BTC, ETH and SOL.

## 3. Files
- `ml/evaluation/metrics.py`: all scoring functions; returns null when a metric is undefined.
- `ml/evaluation/baselines.py`: the fixed rules, fitted on train only.
- `ml/evaluation/run_baselines.py`: scores the baselines on validation and test and writes the report.
- `ml/tests/test_metrics.py`: the metric tests.
- `ml/reports/{btc,eth,sol}/baselines.json`: tracked evidence.

## 4. How it works
- **Price**: last-value predicts "no change"; drift predicts the train average 30-day return. Error is measured in price (MAE, RMSE).
- **Direction**: always the train majority (FLAT), always UP, or **momentum** (the last 30 days' move, classified with the same threshold as the labels).
- **Risk**: always the train majority (medium), or **persistence** (today's 30-day volatility, classified with the train thresholds). Persistence is also scored as a ranking with **Spearman**.
- **Strategy**: buy-and-hold or stay in cash, over **non-overlapping** 30-day windows.
- **Balanced accuracy** is the average of per-class recall. Example: always predicting FLAT when the classes are 60/20/20 gives accuracy 0.6, but balanced accuracy only 1/3.
- **n_effective** = labelled rows / 30. Neighbouring days share 29 of their 30 future days, so 468 rows carry about as much evidence as 15.6 independent ones.

## 5. Results
Test split, from `ml/reports/{asset}/baselines.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| n_effective | 15.6 | 15.6 | 10.166667 |
| Price MAE: last-value / drift | 8095.51 / 8571.00 | 439.12 / 442.61 | 13.82 / 16.42 |
| Direction always-FLAT: accuracy / balanced accuracy | 0.655983 / 0.3333 | 0.566239 / 0.3333 | 0.704918 / 0.3333 |
| Direction momentum MCC | -0.225872 | -0.107569 | -0.192356 |
| Risk persistence Spearman | 0.006854 | -0.113481 | -0.191428 |
| Buy-and-hold mean per 30-day window (windows) | -0.0079 (16) | 0.0207 (16) | -0.0009 (11) |

- Always-FLAT has high accuracy but is useless, as balanced accuracy 1/3 shows. Models must beat it on balanced accuracy and macro-F1, not only accuracy.
- Momentum and trailing volatility do not predict the next 30 days here: MCC is negative and Spearman is near 0.
- Last-value is the price baseline to beat; drift is worse on most splits.

## 6. Decisions
- D20: balanced accuracy, macro-F1, Spearman and n_effective in every report; majority class from train.
- D19: baselines use the train thresholds, never refitted.
- Test is reported but never used to choose anything (docs/EVALUATION.md rule 2).

## 7. Limits
- n_effective is only about 10-16 per split, so confidence intervals are wide. Many differences are not significant.
- SOL test has no high-risk rows, so its high-risk scores are null (with a note).
- Baselines give hard classes only, so ROC-AUC and calibration are null until a model gives probabilities.
- The random-signal strategy baseline (docs/EVALUATION.md) is left for Phase 5.

## Sanity check: risk persistence
Because trailing volatility barely ranked forward volatility on test, we checked the alignment.
- A new test confirms that forward volatility shifted 30 days equals trailing volatility (`ml/tests/test_leakage.py`), so both use the same 30 returns.
- Spearman(vol_30d, fwd_vol_30d), from `risk_persistence_check` in `ml/reports/{asset}/baselines.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Train | 0.465702 | 0.464212 | 0.523997 |
| Validation | -0.167378 | 0.082533 | 0.297256 |
| Test | 0.006854 | -0.113481 | -0.191428 |
| Full series, every 30th row (points) | 0.520186 (110) | 0.445547 (110) | 0.563747 (74) |

- Verified: the alignment is correct; over the full history, volatility does persist.
- Hypothesis (not proven): validation and test (2024 onwards) are a calmer period with a narrow range of volatility, which makes ranking harder; the samples are also small.
- Spread of forward volatility (VERIFIED numbers, `fwd_vol_30d_spread` in `ml/reports/{asset}/baselines.json`). Std, train vs test: BTC 0.015606 vs 0.006979, ETH 0.018985 vs 0.009042, SOL 0.024828 vs 0.009178. IQR, train vs test: BTC 0.015899 vs 0.007573, ETH 0.021384 vs 0.01207, SOL 0.027889 vs 0.009948. So the test spread is clearly narrower than train: about 36-56% of the train value on both measures. The trailing predictor `vol_30d` shrinks the same way (test std BTC 0.007028, ETH 0.008733, SOL 0.009605). HYPOTHESIS: with less spread, small noisy changes decide the ranking, so Spearman falls even if volatility still persists. This fits the near-zero test values but does not prove the cause.

## 8. Verify and next
- Verify: see "How to verify Phase 3 yourself" in ml/docs/STATUS.md.
- Next: Phase 4a (price model), compared against these baselines on validation.
