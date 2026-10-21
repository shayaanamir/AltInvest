# Phase 4c: Direction model

## 1. Goal
Test whether a model can give better **probabilities** for the next 30 days' direction (DOWN, FLAT or UP) than the simplest honest guess: the **class prior**, which repeats how often each class happened in training. The approval rule was written down before any model ran (D31), including the expected result ("not approved").

## 2. What we did
1. Declared exactly 2 model configs and the prior baseline in code.
2. Ran them through the Phase 4.0 walk-forward harness; the test split stayed sealed.
3. Ranked the configs on the first 60% of folds by **log loss**, then compared the winner with the prior on the last 40% using a paired bootstrap.
4. Wrote 15 tests on hand-made fixtures (not market data). `python -m pytest ml` gives 115 passed (ml/docs/STATUS.md).

## 3. Files
- `ml/models/direction.py`: the 2 configs, the prior, probability clipping (EPS = 1e-6) and the convergence-warning counter.
- `ml/evaluation/prob_metrics.py`: log loss per row and ECE.
- `ml/evaluation/run_walkforward_direction.py`: runs, ranks, confirms and writes the verdict.
- `ml/reports/{btc,eth,sol}/walkforward_direction.json`: tracked evidence.

## 4. How it works
- **Model**: **multinomial logistic regression** on the 10 features (standardised with the training fold only), with C = 0.1 (stronger regularisation) and C = 1.
- **Log loss**: -ln of the probability given to what actually happened. Example: always saying 1/3 each scores ln 3 = 1.0986; lower is better.
- **Approval**: the paired 95% CI of logloss(prior) minus logloss(model) on the last 40% must be above 0.
- The hard Phase 3 baselines (always FLAT, always UP, momentum) are shown for context only.

## 5. Results
Last 40% of folds, from `ml/reports/{asset}/walkforward_direction.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| n_effective | 27.7 | 27.7 | 14.8 |
| Log loss prior / top config (logreg_c0.1) | 1.017508 / 1.030682 | 1.03113 / 0.995226 | 1.055915 / 1.048813 |
| Difference prior - top [95% CI] | -0.013174 [-0.045709, 0.017069] | 0.035904 [0.003531, 0.060357] | 0.007102 [-0.026359, 0.037926] |
| Balanced accuracy of the top config | 0.299088 | 0.358145 | 0.358599 |
| Verdict | not approved | approved | not approved |

- ETH passes the rule, against the expectation written in D31. But the same model was worse than the prior on ETH's first 60% of folds (1.169426 vs 1.084441) and over all folds (1.098151 vs 1.062628), and the CI lower bound is only just above 0. This is a fragile result.
- BTC and SOL: no demonstrated gain (D29, D30).

## 6. Decisions
- D31: log loss vs the class prior; 2 configs; rank on the first 60%, confirm on the last 40%.
- D30: a gain equal to the CI half-width (here about 0.03) is confirmed only about half the time.
- D7: without an approved model, Phase 5 serves signal UNCERTAIN/HOLD with confidence null.

## 7. Limits
- Small confirmation sets (n_effective 14.8-27.7); three assets were tested, so one pass by luck is possible.
- Balanced accuracy is near chance (1/3) for all assets, so even the approved ETH model is only slightly better calibrated, not a reliable signal.
- No convergence warnings occurred (0 of 68 folds for BTC/ETH, 0 of 37 for SOL).

## 8. Verify and next
- Verify: see "How to verify Phase 4c yourself" in ml/docs/STATUS.md.
- Next: the user decides how to treat the ETH approval before Phase 5 (signal logic and backtest).
