# PLAN_FORECAST — Phase 9: forecasting v2 (price, price range, risk, direction)

Planner: Claude (planning chat). Executor: the agent. The user relays reports between the two.
Status: APPROVED by the user on 2026-11-02 as the plan; each checkpoint below still needs the planner's OK.
Precondition: Phase 7 is closed in STATUS.md, or the user explicitly allows Phase 9 to run in parallel.

## Goal
Test Prophet, LSTM, LightGBM, GARCH and EWMA honestly against the current baselines, at 30 days and 7 days,
and serve every part that wins: predicted price, price range, risk score, signal. A part that does not win keeps
its baseline. "No model won" is a valid, reportable result (LEARNINGS.md).

## Fixed rules for this phase (on top of ml/AGENTS.md)
1. Targets are RETURNS (log return), never price levels. A price is derived only at serving time:
   predicted_price = last close x exp(predicted log return). prediction_30d is a percent (rule 12).
2. Approval is unchanged (D25): candidates declared in code before any run, at most 4 configs per model type,
   rank on the first 60% of walk-forward folds, confirm on the last 40% with a paired 95% CI of the improvement
   that excludes 0. NO extra minimum-margin rule (power is already low, D29/D30). Do NOT use a plain
   Diebold-Mariano test (overlapping windows); keep the existing paired CI.
3. Gap (embargo) = horizon: 30 rows for 30-day models (already D16), 7 rows for 7-day models.
   Walk-forward step = horizon (non-overlapping windows).
4. The sealed test split is used ONCE, in step 9.6, only on the configs chosen in 9.2-9.5. Never for tuning,
   early stopping, thresholds or selection.
5. Every report records: trial count (configs x assets x horizons), date ranges, git commit, n_effective.
6. Retrain every asset together after any code change; never serve a mix of old and new models.
7. Time boxes: when a step's box runs out, write the result as it stands and move on. Two-attempt rule applies.
8. Evaluation runs on the snapshot only (D40 guard, require_snapshot). The snapshot files must not change.
9. confidence stays null unless it is a calibrated probability (reliability check in the report).

## Steps

| Step | Box | Work | Done when |
|---|---|---|---|
| 9.0 Decisions | 1 day | Write D41+ in DECISIONS.md: horizons (30 and 7), candidates and configs below, metrics below, approval rule (rule 2), consistency rules (9.7), monitoring rule (9.7). Ask the user to get Person B's answer on a 7-day API field; if no answer, plan without it (7-day results stay in reports and /debug). Add a Phase 9 row to PLAN.md. | DECISIONS.md and PLAN.md updated; **CHECKPOINT: send the D-entries to the planner and wait.** |
| 9.1 Setup | 2-3 days | `ml/requirements-train.txt` (prophet, torch CPU, lightgbm, arch) separate from serving requirements; `ml/Dockerfile.train`. 7-day labels (fwd_return_7d, fwd_vol_7d) through the same labels module; horizon passed as a parameter, default 30 so nothing existing changes. EWMA vol (lambda 0.94) as a feature/baseline function. Leakage tests for the 7-day labels and EWMA. | `python -m pytest ml -q` passes; all existing reports byte-identical (SHA-256); `python -c "import ml.config"` works without the training libraries installed. |
| 9.2 Price | 7 days (LSTM max 3 of them) | Target: fwd log return at h = 30 and 7. Candidates (each type max 4 configs): **Prophet** on log close, refit each fold, return = forecast log price at t+h minus log close at t (configs: changepoint_prior_scale 0.05 / 0.5, yearly seasonality off); **LightGBM** (num_leaves 7 / 15, 200 trees, lr 0.03, min_data_in_leaf 50); **LSTM pooled over BTC+ETH+SOL by default** (1 layer, hidden 16 / 32, lookback 60, early stopping on the last 15% of each fold's TRAIN rows); current Ridge as reference. Optional pooled LightGBM counts toward its 4. Metric: MAE of log return vs last-value (0). | `reports/{asset}/walkforward_price_v2.json` per asset with both horizons, verdict, trial count; **CHECKPOINT: send the verdict table to the planner.** |
| 9.3 Range | 4 days | 80% interval for the h-day return. Candidates: quantile LightGBM (q 0.10, 0.90); EWMA band (EWMA vol x sqrt(h) x normal or empirical quantiles). Baselines: trailing vol_30d band (current rule), EWMA band. Metrics: interval (Winkler) score, coverage overall, lower-tail misses and upper-tail misses separately (each should be about 10%), coverage in the top-third volatility periods. Approved only if interval score beats the best baseline (paired CI) AND overall coverage is within 75-85% AND neither tail misses more than 15%. | `walkforward_range.json` per asset; **CHECKPOINT.** |
| 9.4 Risk | 4 days | Target: log fwd 30d realised vol (D24); also 7d. Candidates: **GARCH(1,1) Student-t** (arch, refit per fold), **LightGBM**, current Ridge/HAR. Baselines: persistence vol_30d (served today) AND **EWMA**. Metrics: QLIKE (primary) and Spearman (existing). If no model beats EWMA but EWMA beats persistence, serve EWMA (new D-number), mapped through the same pooled percentile (D36). | `walkforward_risk_v2.json` per asset; **CHECKPOINT.** |
| 9.5 Direction | 3 days | Add LightGBM classifier (2 configs) next to logistic regression. Metrics: log loss vs prior (approval) and the D34 backtest after 0.1% fees. ETH logreg stays unserved unless it also passes 9.6 AND the backtest beats always-hold and buy-and-hold after fees. | `walkforward_direction_v2.json`, `backtest_v2.json`; **CHECKPOINT.** |
| 9.6 Sealed test | 1 day | Run the sealed test ONCE on the chosen configs only (one per part per asset per horizon). Record whatever comes out. A part is served only if it is approved in walk-forward AND not worse than its baseline on test. | `test_final.json` per asset; scorecard regenerated; **CHECKPOINT: planner decides what gets served.** |
| 9.7 Serving | 4 days | Train final models in the training image; save small artifacts with metadata.json (rule 10): LightGBM text model, GARCH parameters JSON, Prophet via its JSON serializer, LSTM as ONNX (onnxruntime in the serving image only if LSTM is served). Serving image must not install prophet or torch. Fill predicted_price, lower_bound, upper_bound, prediction_30d, signal, confidence, model_version only for served parts. Consistency rules: predicted_price is clipped into [lower_bound, upper_bound]; BUY only if prediction_30d > 0 and SELL only if < 0, else HOLD/UNCERTAIN; risk_score identical on /predict and /risk. Monthly retrain job (ml-refresh style). Monitoring: live_score compares each served part with its baseline; it raises an ALERT in /debug/live-scorecard and STATUS, it never switches models automatically. | Contract test passes for all assets; `docker compose up -d --build ml ml-refresh` serves the approved fields; serving image size recorded; scorecard shows served = yes for each winner. |
| 9.8 Close | 1 day | STATUS.md "How to verify Phase 9 yourself" block; `docs/phases/PHASE_9_forecasting_v2.md`; GLOSSARY terms (EWMA, GARCH, QLIKE, pinball/interval score, coverage, LSTM, Prophet). | Rules 15 and 16 met; planner signs off. |

Total: about 5-6 weeks. Expected outcome (not a target): range likely passes, risk maybe (EWMA), price at 7 days
possible, direction unlikely. Report every result, including losses.

## Checkpoint report format (what the agent sends back)
1. What ran (commands) and what changed (files).
2. The verdict table copied from the JSON report: part, asset, horizon, best config, model metric, baseline metric,
   paired CI, approved yes/no, trial count. No hand-typed numbers.
3. `python -m pytest ml -q` result and the snapshot hash check.
4. Anything that broke the rules above, and open questions.
