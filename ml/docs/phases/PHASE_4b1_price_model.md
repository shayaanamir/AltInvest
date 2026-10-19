# Phase 4b-1: Price model (Ridge and gradient boosting)

## 1. Goal
Test whether simple models can predict the 30-day return better than **last-value** ("the price will not change"), the strongest price baseline so far. The approval rule was fixed before any model ran (D25, D28), so the result cannot be steered. Prophet and LSTM come later in 4b-2.

## 2. What we did
1. Declared exactly 3 model configs and 2 baselines in code.
2. Ran them all through the Phase 4.0 walk-forward harness; the test split stayed sealed.
3. Ranked the configs on the first 60% of folds by return MAE, then compared the winner with last-value on the last 40% using a paired bootstrap.
4. Wrote 12 tests on hand-made fixtures (not market data). `python -m pytest ml` gives 97 passed (ml/docs/STATUS.md).

## 3. Files
- `ml/models/price.py`: the 3 configs and 2 baselines; features standardised using the training fold only.
- `ml/evaluation/run_walkforward_price.py`: runs, ranks, confirms and writes the verdict.
- `ml/tests/test_price_model.py`: the tests.
- `ml/reports/{btc,eth,sol}/walkforward_price.json`: tracked evidence.

## 4. How it works
- **Target**: the 30-day log return. Errors are measured in return units (D28), so a 10% miss counts the same in 2019 and 2025. USDT errors are a secondary view.
- **Configs**: Ridge on all 10 features with alpha 100 and alpha 1000 (strong regularisation pulls predictions towards the average), and a small gradient-boosted tree model (depth 2, 50 trees).
- **Approval**: the best config on the first 60% must have a lower MAE than last-value on the last 40%, with the 95% CI of MAE(last-value) minus MAE(model) above 0.
- Example: an MAE of 0.15 means the predicted 30-day log return misses by 0.15 on average, about 16% in price.

## 5. Results
From `ml/reports/{asset}/walkforward_price.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Return MAE on all folds: last-value / best config | 0.149519 / 0.151327 | 0.194302 / 0.19767 | 0.233252 / 0.239465 |
| Best config on the first 60% | ridge_all_a1000 | hgb_d2 | ridge_all_a1000 |
| Last 40%: n_effective | 27.7 | 27.7 | 14.8 |
| Last 40%: MAE(last-value) - MAE(top) [95% CI] | 0.001055 [-0.00794, 0.009353] | -0.000785 [-0.010447, 0.008863] | -0.004377 [-0.023187, 0.020063] |
| Verdict | not approved | not approved | not approved |

- No config beats last-value. Over all folds, every model has negative skill vs last-value (for example BTC ridge_all_a1000: -0.012096).
- The confirmation sets are small (n_effective 27.7, 27.7 and 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.

## Power check
How big a gain could the confirmation step have detected? From `ml/reports/{asset}/power_check.json`, which reads the paired CIs in the walk-forward reports:

| | BTC | ETH | SOL |
|---|---|---|---|
| n_effective (last 40%) | 27.7 | 27.7 | 14.8 |
| Price: CI half-width (return MAE) | 0.008646 | 0.009655 | 0.021625 |
| Price: half-width as % of last-value MAE | 7.733277 | 7.074245 | 12.106436 |
| Risk: CI half-width (Spearman) | 0.214335 | 0.152608 | 0.237515 |

- A price model would need to cut last-value's error by roughly 7-12% before the protocol could show it. A risk model would need a Spearman about 0.15-0.24 higher than persistence. These are labelled "smallest difference the protocol can reliably detect (approximate)".
- Approximate, and optimistic: a gain exactly this size is detected only about half the time. Reliable (80%) detection needs about 1.43x these values.
- D29: a negative verdict means "no demonstrated gain", not "no skill".

## 6. Decisions
- D28: return-space target and errors; approval against last-value on the last 40% of folds.
- D25: configs declared before running; rank on the first 60%, confirm on the last 40%.
- D27: until a risk model is approved, /risk uses persistence. The price fallback is open for Person B.

## 7. Limits
- Only the existing 10 features; no new inputs were tried.
- 30-day crypto returns are very noisy, so even a real small edge would be hard to detect with about 28 independent observations.
- Directional accuracy of the models is close to 0.5 (BTC 0.516002 for ridge_all_a1000), i.e. near chance.

## 8. Verify and next
- Verify: see "How to verify Phase 4b-1 yourself" in ml/docs/STATUS.md.
- Next: 4b-2 (Prophet/LSTM candidates) or 4c (direction model), on the same harness and protocol.
