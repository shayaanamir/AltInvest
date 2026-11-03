# PLAN_FORECAST — Phase 9: forecasting v2 (short version)

Planner: Claude (planning chat). Executor: the agent. The user relays reports.
Version 2 (2026-11-03): shortened after 9.2. Same goals and rules, fewer stops, less setup.

## Goal
Test better models against the baselines and serve only the parts that win. "Nothing won" is a valid result.

## Done
- 9.0 decisions (D41-D47), 9.1 setup, 9.2 price + D48 re-run.
- Price result: 0 of 60 trials approved. Corrected Prophet is about level with last value. **Price stays on the
  baseline (D35). Prophet and LSTM are finished: no more price work, and neither will be served.**

## Rules (unchanged in substance)
1. Return targets. Embargo = step = horizon (30 and 7).
2. Approval = D25 paired CI on the last 40% of folds; at most 4 configs per model type, declared before running.
3. Inputs known at t may be used (D48); labels after the embargo may not.
4. Sealed test used once (step 9.6), only on the chosen configs.
5. Each report records trial count, git commit, n_effective. Snapshot files never change (hash check).
6. Time box per step; if it runs out, report what you have and move on.

## How to run (simpler)
- Run evaluation in ONE pinned venv, not Docker:
  `python -m venv .venv-train` then `pip install -r ml/requirements.txt -r ml/requirements-train.txt`.
  Record `pip freeze` in the step report once. Do not use or repair the host Python.
- The git_dirty flag on the 9.2 reports is a known false positive (fixed in b2054c3). No re-run.
- 7-day results go in reports and /debug only. The API stays 30-day unless Person B adds a field later.

## Remaining steps
The agent runs 9.3 -> 9.4 -> 9.5 WITHOUT stopping in between. It stops only where marked STOP.
Stop earlier only if a rule question comes up that this plan does not answer.

| Step | Box | Work | Pass rule |
|---|---|---|---|
| 9.3 Range | 2 days | 80% interval for the h-day return. Candidates: EWMA band (lambda 0.94, normal quantiles), quantile LightGBM (q 0.10/0.90, 2 configs). Baseline: vol_30d band. Metric: interval (Winkler) score; also coverage, lower and upper tail misses, coverage in the top-third vol periods. | Beats the baseline (paired CI) AND coverage 75-85% AND each tail at most 15%. |
| 9.4 Risk | 2 days | Target: log fwd realised vol (D24). Candidates: EWMA, GARCH(1,1) Student-t (fit on fold train, recursion through t, D48). Baseline: persistence vol_30d. Metric: QLIKE (primary), Spearman. | Beats persistence (paired CI). If both pass, the better one wins. Served through the same pooled percentile (D36). |
| 9.5 Direction | 1 day | Add LightGBM classifier (2 configs) next to the existing logreg. Metric: log loss vs prior. | Approved in walk-forward AND the D34 backtest beats hold and buy-and-hold after 0.1% fees. |
| **STOP A** | | One report for 9.3-9.5 (format below). Planner picks the configs for the sealed test. | |
| 9.6 Sealed test | 1 day | Run once, chosen configs only. | Served only if approved AND not worse than baseline on test. |
| **STOP B** | | Report test results. Planner decides what gets served. | |
| 9.7 Serving | 2-3 days | Only for parts that won. Save small artifacts + metadata.json. Fill only the won fields; keep consistency rules (price inside range, BUY only if return > 0, same risk_score on /predict and /risk). Alert-only monitoring in live_score. Code + tests by the agent; the `docker compose up` check can be done by the teammate. | Contract test passes; existing endpoints unchanged for fields that did not win. |
| 9.8 Close | 1 day | STATUS.md verify block, `docs/phases/PHASE_9_forecasting_v2.md`, glossary terms. | Rules 15 and 16; planner signs off. |

About 2 weeks left. Likely outcome: range passes, risk maybe (EWMA), direction unlikely.

## Report format (STOP A and STOP B)
1. Commands run, files changed, commits.
2. Verdict table printed by code from the JSON: part, asset, h, best config, model metric, baseline metric,
   paired CI, approved, trials. (Range: add coverage and tail misses.)
3. pytest result and hash check.
4. Rule breaks and questions. Keep it under one page.
