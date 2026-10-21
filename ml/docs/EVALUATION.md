# EVALUATION

## Rules
1. Metrics only on held-out data. Never on train.
2. Test set is never used for early stopping, thresholds, or model choice. Use validation.
3. Embargo = horizon (30 days) between splits.
4. Backtest uses NON-OVERLAPPING 30-day windows (step = 30 days).
5. Sharpe annualisation uses sqrt(365). Volatility = daily std * sqrt(365).
6. Thresholds are fixed before looking at test results and recorded in DECISIONS.md.
7. Every report is written by code to reports/{asset}/*.json. Nothing hand-typed.
8. Any Prophet/model used for a historical cutoff t is fit only on data <= t.

## Baselines (computed first, Phase 3)
- Price: last-value (0% change), drift (mean historical return)
- Direction: majority class, always-up
- Risk: trailing 30-day realised vol as the predictor
- Strategy: buy-and-hold, always-HOLD, random signal (seeded, many runs)

## Metrics
| Output | Metrics |
|---|---|
| Price | MAE, RMSE, MAPE, skill vs last-value (1 - MAE/MAE_naive), directional accuracy |
| Interval | empirical coverage vs nominal, mean width |
| Direction | accuracy vs majority baseline, balanced accuracy, macro-F1, per-class P/R, confusion matrix, MCC, ROC-AUC, Brier, calibration bins |
| Risk | accuracy, macro-F1, confusion matrix, Spearman(risk_score, realised forward vol), Brier |
| Backtest | hit rate, trades, % HOLD, cum return, Sharpe, max drawdown, vs baselines, bootstrap CI |

Also report per asset. Per regime only after a regime detector exists.

## Ship rule
A model is "approved" for an asset only if it beats its baseline on validation AND the gap is confirmed on test.
Otherwise the API returns signal UNCERTAIN/HOLD, low confidence, and a `note` explaining it.

## Confidence
confidence = measured quantity (e.g. rolling directional accuracy or interval coverage from backtest), stored in artifact metadata.
Never a constant like 0.95.
