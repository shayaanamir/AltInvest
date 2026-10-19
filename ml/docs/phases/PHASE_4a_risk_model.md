# Phase 4a: Risk model

## 1. Goal
Build the first real model: predict how volatile the next 30 days will be, and check whether it ranks future volatility better than the simple **persistence** baseline ("next month's volatility = this month's"). The rules for approving it were fixed before any model ran (D25), so the result cannot be steered. No price or direction models yet.

## 2. What we did
1. Declared exactly 4 candidate model configurations in code (D25: at most 4, no searching).
2. Ran all 4 plus persistence through the Phase 4.0 walk-forward harness; the test split stayed sealed.
3. Ranked the configs on the first 60% of folds, then confirmed the winner on the last 40% with a **paired bootstrap**.
4. Wrote 16 leakage and protocol tests on hand-made fixtures (not market data). `python -m pytest ml` gives 85 passed (ml/docs/STATUS.md).

## 3. Files
- `ml/models/risk.py`: the 4 configs; features are standardised using the training fold only.
- `ml/evaluation/run_walkforward_risk.py`: runs, ranks, confirms and writes the verdict.
- `ml/tests/test_risk_model.py`: the tests.
- `ml/reports/{btc,eth,sol}/walkforward_risk.json`: tracked evidence.

## 4. How it works
- **Target**: log of next-30-day volatility (D24). Taking the log makes the very calm and very wild months less lopsided.
- **Configs**: (1) **HAR-style** Ridge on the log of 7-day and 30-day volatility; (2) **Ridge** on all 10 features, alpha 1; (3) the same with alpha 10 (stronger **regularisation**); (4) a small **gradient-boosted tree** model.
- **Standardising**: each feature is shifted and scaled using the training fold's mean and std, never later data.
- **Scoring**: Spearman of the prediction against actual volatility, plus low/medium/high classes from each fold's own thresholds.
- **Approval** (D25): the best config on the first 60% of folds must beat persistence on the last 40%, and the 95% CI of the Spearman difference must be above 0.

## 5. Results
From `ml/reports/{asset}/walkforward_risk.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Best config on the first 60% | ridge_all_a10 | hgb_d3 | ridge_all_a10 |
| Spearman on all folds: best config / persistence | 0.46241 / 0.347215 | 0.542037 / 0.515039 | 0.211227 / 0.210949 |
| Last 40%: n_effective | 27.7 | 27.7 | 14.8 |
| Last 40%: Spearman difference vs persistence [95% CI] | 0.056201 [-0.1805, 0.2482] | -0.137621 [-0.24, 0.0652] | -0.221018 [-0.4605, 0.0145] |
| Verdict | not approved | not approved | not approved |

- No config is approved for any asset. Over all folds the models look somewhat better than persistence on BTC, but on the last 40% the difference is not clear. On ETH and SOL it is even negative.
- The confirmation sets are small (n_effective 27.7, 27.7 and 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.

## 6. Decisions
- D24: the target is log forward volatility; mapping it to a 0-100 risk score is deferred.
- D25: 4 configs declared up front; rank on the first 60% of folds, confirm on the last 40%.
- D23: the test split was partly seen in Phase 3 but never used for choices. D26: risk is 4a, price 4b.

## 7. Limits
- The confirmation sets are small, so a real but modest improvement could be missed.
- Only the existing 10 features were allowed; no new inputs were tried.
- Pooling folds from different years mixes calm and wild periods, which pushes Spearman on all folds above the first-60% and last-40% values.
- Until a model is approved, the risk output should fall back to persistence (docs/EVALUATION.md ship rule).

## 8. Verify and next
- Verify: see "How to verify Phase 4a yourself" in ml/docs/STATUS.md.
- Next: Phase 4b (price model) uses the same harness and approval protocol.
