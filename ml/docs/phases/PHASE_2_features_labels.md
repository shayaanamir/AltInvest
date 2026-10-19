# Phase 2: Features, labels and splits

## 1. Goal
Turn the validated price data into what a model will need: **features** (inputs built only from the past), **labels** (the answers, built from the next 30 days) and **splits** (train, validation, test in time order). The main job is to make **leakage** impossible, because v1-style leakage makes any later result meaningless. No models are built yet.

## 2. What we did
1. Added D18 (how splits are counted) and D19 (thresholds from train only) to docs/DECISIONS.md.
2. Wrote the features, labels and splits modules, plus a summary script.
3. Wrote 23 leakage tests on hand-made fixtures (not market data). `python -m pytest ml` gives 33 passed (ml/docs/STATUS.md).
4. Ran the summary for BTC, ETH and SOL, which wrote three JSON reports.

## 3. Files
- `ml/features/features.py`: 10 features from trailing windows; drops the first 30 rows (warm-up); refuses data with gaps.
- `ml/labels/labels.py`: 30-day forward return and volatility, and the class thresholds.
- `ml/evaluation/splits.py`: the D18 split rule.
- `ml/data/dataset_summary.py`: builds everything for one asset and writes the report.
- `ml/tests/test_leakage.py`: the leakage tests.
- `ml/reports/data/{btc,eth,sol}_dataset_summary.json`: tracked evidence.

## 4. How it works
- **Features** look back only. Example: `ret_7d` on day t = ln(close[t] / close[t-7]). A test cuts the series at day t and checks the features up to t are identical, so nothing after t was used.
- **Labels** look forward 30 days: `fwd_return_30d` = ln(close[t+30] / close[t]). The last 30 days have no label yet.
- **Splits** (D18), with n feature rows: b1 = floor(0.70n), b2 = floor(0.85n). Train = rows 0 to b1-31, validation = b1 to b2-31, test = b2 to the end. The 30-row gap (**embargo**) means a train label never peeks into validation, and a validation label never peeks into test.
- **Classes** (D19), using **percentile thresholds** from train only. Direction: FLAT if the 30-day move is smaller than the 40th percentile of train moves, otherwise UP or DOWN. Risk: low, medium or high by the 33rd and 67th percentiles (**terciles**) of train volatility.

## 5. Results
From `ml/reports/data/{asset}_dataset_summary.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Feature rows | 3319 | 3319 | 2229 |
| Train / validation / test rows | 2293 / 468 / 498 | 2293 / 468 / 498 | 1530 / 304 / 335 |
| Labelled test rows | 468 | 468 | 305 |
| Test period | 2025-06-07 to 2026-10-17 | same | 2025-11-17 to 2026-10-17 |
| Test direction DOWN / FLAT / UP % | 20.94 / 65.6 / 13.46 | 21.58 / 56.62 / 21.79 | 16.07 / 70.49 / 13.44 |
| Test risk low / medium / high % | 92.74 / 1.07 / 6.2 | 66.03 / 27.78 / 6.2 | 90.16 / 9.84 / 0.0 |

- In train the classes are about 40% FLAT and one third per risk class, as designed.
- In validation and test, markets were calmer than 2017-2023, so most rows are FLAT and low risk. That is the real market, not a bug.

## 6. Decisions
- D18: split sizes are counted after the 30 warm-up rows.
- D19: thresholds are fitted on train only and stored in the report, never refitted.
- D16/D17: a 30-row embargo, cut from the end of the earlier split.
- No scaling and no filling of missing values.

## 7. Limits
- Unbalanced test classes mean high accuracy can be fake: always predicting "low risk" scores 92.74% on BTC test. Phase 3 baselines must include "always the most common class".
- SOL test has no "high risk" rows, so high-risk recall cannot be measured on SOL test.
- Features use row windows, which equal day windows only because the data has no gaps.

## 8. Verify and next
- Verify: see "How to verify Phase 2 yourself" in ml/docs/STATUS.md.
- Next: Phase 3 builds baselines and metric functions on these splits.
