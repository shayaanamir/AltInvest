# Phase 5a: Direction mechanism check and serving decisions

## 1. Goal
Phase 4c approved one direction model (ETH) by the walk-forward rule, against the expectation written down in advance. Before any signal or backtest code exists, this step checks *what kind* of information that model has, and records how direction is served (D33) and how the backtest will work (D34), before the test split is ever opened.

## 2. What we did
1. Re-ran the 4c reports on a clean commit: the numbers were identical.
2. Recomputed the 4c predictions in memory and measured three rank correlations, report only.
3. Recorded D32 (fragility of the ETH approval), D33 (serving rule) and D34 (backtest protocol).
4. Wrote 2 tests on hand-made fixtures (not market data). `python -m pytest ml` gives 117 passed (ml/docs/STATUS.md).

## 3. Files
- `ml/evaluation/direction_mechanism.py`: recomputes the 4c predictions and writes the checks.
- `ml/tests/test_direction_mechanism.py`: the tests.
- `ml/reports/{btc,eth,sol}/direction_mechanism.json`: tracked evidence.

## 4. How it works
Three Spearman correlations on the model's probabilities:
1. P(FLAT) vs trailing 30-day volatility: does the model say "flat" when markets are calm?
2. P(FLAT) vs the size of the next 30-day move: **move-vs-no-move skill**.
3. P(UP) - P(DOWN) vs the next 30-day return: **up/down skill**, which BUY or SELL would need.

## 5. Results
ETH, last 40% of folds (n_effective 27.7), from `ml/reports/eth/direction_mechanism.json`:

| Check | Spearman [95% CI] |
|---|---|
| 1. P(FLAT) vs vol_30d | -0.52739 [-0.66579, -0.3105] |
| 2. P(FLAT) vs size of move | -0.045538 [-0.245999, 0.209584] |
| 3. P(UP)-P(DOWN) vs return | 0.014782 [-0.154854, 0.137813] |

- Only check 1 is clear: the model raises P(FLAT) when trailing volatility is low.
- Checks 2 and 3 have CIs containing 0: no demonstrated move-vs-no-move or up/down skill (D29, D30).

## 6. Decisions
- D32: the ETH approval stands but is fragile. From Phase 5 on, a model must also beat its baseline on the first 60% of folds.
- D33: BTC, ETH and SOL serve signal UNCERTAIN with confidence null, whatever the test later shows.
- D34: the backtest protocol is fixed before any backtest code exists.

## 7. Limits
- Small samples (n_effective 14.8-27.7), so "not demonstrated" does not mean "absent".
- The checks are report-only; nothing was tuned on them.

## 8. Verify and next
- Verify: see "How to verify Phase 5a" in ml/docs/STATUS.md.
- Next: 5b builds `generate_signal()` and the backtest under D33 and D34.
