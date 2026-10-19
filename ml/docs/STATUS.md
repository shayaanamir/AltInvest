# STATUS

Current phase: 4b-1 (price model: Ridge/HGB) DONE for BTC, ETH, SOL (2026-10-19). Verdict: NOT APPROVED for all three (D28).
Next: Phase 4b-2 (Prophet/LSTM price candidates) or 4c (direction). Not started; waiting on the user's go-ahead.

## Power check (2026-10-19, no new models)

- Started from a clean tree: HEAD 00d09a0. Re-ran run_walkforward_price once per asset; only generated_at, git_commit and git_dirty (true -> false) changed.
- `ml/evaluation/power_check.py` reads the paired 95% CIs already in walkforward_price.json and walkforward_risk.json and writes `ml/reports/{asset}/power_check.json`. It runs no models and no bootstrap. Its sources have `git_dirty` false.
- `ml/tests/test_power_check.py`: 3 tests. `python -m pytest ml` -> `100 passed`.
- D29 added. No decision on Prophet/LSTM.

| power_check.json (last-40% set)  | BTC      | ETH      | SOL       |
| -------------------------------- | -------- | -------- | --------- |
| n_effective                      | 27.7     | 27.7     | 14.8      |
| price CI half-width (return MAE) | 0.008646 | 0.009655 | 0.021625  |
| ... as % of last-value MAE       | 7.733277 | 7.074245 | 12.106436 |
| risk CI half-width (Spearman)    | 0.214335 | 0.152608 | 0.237515  |

- These are approximate: a true gain equal to the half-width is detected about half the time. About 80% power needs roughly 1.43x the half-width (price 11.0 / 10.1 / 17.3% of MAE; risk 0.31 / 0.22 / 0.34 Spearman).

## Phase 4b-1 (price model): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD 88d4a79, `git_dirty` False.
- Step 0a: re-ran run_walkforward_risk once per asset. Only generated_at, git_commit and git_dirty (true -> false) changed.
- Step 0b: D27 (risk fallback = persistence) and D28 (price target, approval rule) added to DECISIONS.md. PLAN.md 4b/4c "Done when" now says walk-forward (D21).
- New modules:
  - `ml/models/price.py`: the 3 declared configs and 2 declared baselines; target fwd_return_30d; features standardised on train-fold mean/std.
  - `ml/evaluation/run_walkforward_price.py`: writes `ml/reports/{asset}/walkforward_price.json`.
- No changes to earlier modules. Reused: harness, `load_dev`, `run_metadata`, `split_folds`, `price_metrics` (USDT view), `paired_bootstrap_ci`.
- `ml/tests/test_price_model.py`: 12 tests. `python -m pytest ml` -> `97 passed`.
- `python -m ml.evaluation.run_walkforward_price --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (code not yet committed; not re-run).
- Test rows untouched: `rows_built` [0, b2) and `max_label_row_reached` b2-1, as in Phase 4.0.
- Cross-check: last-value USDT MAE equals the Phase 4.0 report (BTC 5456.61, ETH 346.78, SOL 22.56).
- Last-value was the best baseline on the first 60% for every asset (`best_baseline`), so comparing against it is consistent with D22.

| walkforward_price.json                     | BTC                           | ETH                             | SOL                             |
| ------------------------------------------ | ----------------------------- | ------------------------------- | ------------------------------- |
| top config (first 60%)                     | ridge_all_a1000               | hgb_d2                          | ridge_all_a1000                 |
| last-40% n_pooled / n_effective            | 831 / 27.7                    | 831 / 27.7                      | 444 / 14.8                      |
| paired MAE(last-value) - MAE(top) [95% CI] | 0.001055 [-0.00794, 0.009353] | -0.000785 [-0.010447, 0.008863] | -0.004377 [-0.023187, 0.020063] |
| verdict                                    | not approved                  | not approved                    | not approved                    |

- The confirmation sets are small (n_effective 27.7, 27.7, 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.
- Price API fallback is open for Person B (D28).

## Phase 4a (risk model): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD aeddd75, `git_dirty` False. Step 0 and Step 1 were not redone.
- Approved plan changes applied:
  - The blocking test was replaced by tests (i) and (ii).
  - PLAN.md table renamed (4a risk, 4b price, 4c direction), plus D26.
  - Class metrics use exp(prediction) with each fold's thresholds; Spearman uses the raw predicted log-vol.
- New modules:
  - `ml/models/risk.py`: the 4 declared configs; features standardised on train-fold mean/std; target log(fwd_vol_30d).
  - `ml/evaluation/run_walkforward_risk.py`: writes `ml/reports/{asset}/walkforward_risk.json`.
- Reuse change: `run_walkforward.py` gained `run_metadata()`, pulled out of `run()`. In-memory output is unchanged vs the committed reports (generated_at and git fields excluded) for all three assets.
- `ml/tests/test_risk_model.py`: 16 tests (config count, scaling on train only, (i), (ii), never an index >= b2, 60/40 split, fold-threshold classes). `python -m pytest ml` -> `85 passed`.
- `python -m ml.evaluation.run_walkforward_risk --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (Phase 4a code not yet committed; not re-run, as instructed).
- Test rows untouched: `rows_built` [0, b2) and `max_label_row_reached` b2-1, the same as Phase 4.0.

| walkforward_risk.json                        | BTC                      | ETH                     | SOL                      |
| -------------------------------------------- | ------------------------ | ----------------------- | ------------------------ |
| top config (first 60%)                       | ridge_all_a10            | hgb_d3                  | ridge_all_a10            |
| last-40% n_pooled / n_effective              | 831 / 27.7               | 831 / 27.7              | 444 / 14.8               |
| paired Spearman diff vs persistence [95% CI] | 0.0562 [-0.1805, 0.2482] | -0.1376 [-0.24, 0.0652] | -0.221 [-0.4605, 0.0145] |
| verdict                                      | not approved             | not approved            | not approved             |

- The confirmation sets are small (n_effective 27.7, 27.7, 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.

## Phase 4a (risk model): stopped at pre-flight (2026-10-19, resolved the same day)

- Done before the stop:
  - Step 0a: re-ran run_baselines and run_walkforward once each from clean HEAD 8763086. All 6 reports changed only in generated_at, git_commit and git_dirty (true -> false); `git_dirty` False.
  - Step 0b: D23, D24, D25 added to DECISIONS.md.
  - Step 1: `paired_bootstrap_ci` in metrics.py plus 3 tests (`test_metrics.py`: 22 passed).
- Blocking problem: the required test "predictions for a fold do not change when rows at or after the origin are altered" cannot pass for a correct model. The fold predicts rows [t, t+30), and each row's features are trailing windows ending at that row's own price. So altering prices at or after t changes the predicted rows' inputs, and their predictions must change.
- Proposed replacement (needs approval): (i) the model fitted for fold k is unchanged when raw rows at or after origin_k are altered (compare its predictions on the original inputs); (ii) the prediction at any row r is unchanged when only rows after r are altered.
- Not started: ml/models/risk.py, run_walkforward_risk.py, test_risk_model.py, runs, phase doc.
  Done: branch ml-v2, v1 archived at tag archive/ml-v1, docs, Phase 0 scaffold, Phase 1 (BTC), Phase 1b (ETH, SOL), Phase 2, Phase 3, Phase 4.0.
  Blocked: nothing.

## Phase 4.0 (walk-forward harness): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD a934f10, `git_dirty` False.
- Docs: D21 (walk-forward, sealed test) and D22 (selection rule) added to DECISIONS.md. config.py: `MIN_TRAIN_ROWS = 730`, `WALKFORWARD_STEP = 30`.
- Interpretation recorded in D21: first origin = MIN_TRAIN_ROWS + 30 = row 760, so the first fold trains on exactly 730 rows. The last fold is cut at b2-30 (BTC/ETH 21 rows, SOL 24 rows).
- New modules:
  - `ml/evaluation/walkforward.py`: `make_folds`, `run_folds`, `Spec(fit, predict)`, `SealedTestError`. Raises on any row >= b2, and on a data frame longer than b2. Predict inputs are features + close only (no labels).
  - `ml/evaluation/run_walkforward.py`: builds features/labels only from raw rows before the first test row, then writes `ml/reports/{asset}/walkforward_baselines.json`.
- Reuse changes to Phase 3 code (no output change: in-memory `run_baselines.run()` still equals the committed reports, metadata excluded, for all three assets):
  - `run_baselines.py`: extracted `price_metrics`, `class_metrics`, `ranking_metrics` (each gained a `block_size` argument, default 30) and `strategy_stats` from the section functions.
  - `baselines.py`: added `walkforward_specs()` adapters that call the existing rules unchanged.
- `ml/tests/test_walkforward.py`: 7 tests (required a-f plus "predict inputs have no labels"). `python -m pytest ml` -> `66 passed`.
- `python -m ml.evaluation.run_walkforward --asset btc|eth|sol` -> exit 0, all four sections. `git_dirty: true` with a stderr warning (Phase 4.0 code not yet committed).
- Test rows never touched (from each report's metadata): `rows_built` = [0, b2); `max_label_row_reached` = b2-1 (BTC/ETH 2820, SOL 1893); `sealed_test_first_date` (BTC/ETH 2025-06-07, SOL 2025-11-17) equals the Phase 2 test start. Phase 3's reports already contain test metrics; this phase did not read or recompute them.

| Pooled walk-forward                                 | BTC                       | ETH                       | SOL                       |
| --------------------------------------------------- | ------------------------- | ------------------------- | ------------------------- |
| n_folds / n_pooled / n_effective                    | 68 / 2031 / 67.7          | 68 / 2031 / 67.7          | 37 / 1104 / 36.8          |
| price MAE last-value / drift                        | 5456.61 / 5583.06         | 346.78 / 361.15           | 22.56 / 23.34             |
| direction bal. acc. majority / always-UP / momentum | 0.3333 / 0.3333 / 0.3162  | 0.3333 / 0.3333 / 0.3649  | 0.3333 / 0.3333 / 0.326   |
| risk persistence bal. acc.                          | 0.4378                    | 0.468                     | 0.329                     |
| risk persistence Spearman [95% CI]                  | 0.347215 [0.1611, 0.5143] | 0.515039 [0.3326, 0.6591] | 0.210949 [0.0204, 0.4424] |

## Phase 3 (baselines + metrics): what ran (from repo root, 2026-10-19)

- Docs: D20 (evaluation on unbalanced classes) added to DECISIONS.md.
- Small refactors, output unchanged (re-ran dataset_summary: only `generated_at` differed, reverted):
  - `labels.py`: `direction_class` / `risk_class` split out of `apply_thresholds`, so baselines use the exact same class rule.
  - `dataset_summary.py`: `prepare(asset)` and `require_validated(asset)`, reused by run_baselines.
- New modules:
  - `ml/evaluation/metrics.py`: price, classification, risk ranking, interval, calibration, strategy metrics and a moving-block bootstrap. Undefined values return None.
  - `ml/evaluation/baselines.py`: fixed rules fitted on train only.
  - `ml/evaluation/run_baselines.py`: writes `ml/reports/{asset}/baselines.json` (tracked; not git-ignored).
- `ml/tests/test_metrics.py`: 19 tests. `python -m pytest ml` -> `52 passed`.
- `python -m ml.evaluation.run_baselines --asset btc|eth|sol` -> exit 0; all four sections present for validation and test.
- Report details:
  - Majority classes fitted on train: direction FLAT, risk medium (all assets). Drift log return: BTC 0.030048, ETH 0.027303, SOL 0.086301.
  - Classification `brier_one_hot` treats hard predictions as one-hot probabilities. `roc_auc_ovr` and `calibration` are null with a note (no probabilities).
  - `accuracy_ci95` and `mae_price_ci95` use a block bootstrap (block 30, 1000 resamples, seed 0). Strategy `mean_window_return_ci95` uses block 1, since windows do not overlap.
  - SOL test has no high-risk rows: high recall/precision are null with a note; balanced accuracy averages over low and medium only.
  - `git_dirty: true` in metadata because Phase 3 was not committed when the reports ran. Re-run after committing to record a clean commit.
- Findings (all from `ml/reports/{asset}/baselines.json`):
  - Direction: train-majority (always FLAT) has the highest test accuracy (BTC 0.655983, ETH 0.5662, SOL 0.7049), but balanced accuracy 0.3333. Momentum has negative MCC on every split.
  - Risk: trailing vol barely ranks forward vol (test Spearman BTC 0.006854, ETH -0.113481, SOL -0.191428; every 95% CI contains 0).
  - Price: drift beats last-value only on BTC validation (skill 0.018417); last-value is the price baseline to beat elsewhere.
  - n_effective is only 15.6 (BTC, ETH) and about 10.1 (SOL) per split, so all CIs are wide.

## Phase 3 sanity check: risk persistence (2026-10-19, no new features or models)

- Std definitions match: both `vol_30d` (features.py:50) and `fwd_vol_30d` (labels.py:25) use pandas `.std()`, ddof=1. Windows: r[t-29..t] and r[t+1..t+30].
- New test `test_fwd_vol_shifted_equals_trailing_vol` (test_leakage.py): fwd_vol_30d.shift(30) == vol_30d, rtol 1e-12. Passes. `python -m pytest ml` -> `53 passed`.
  - First run failed on my own row-count line (expected n-60, correct is n-30: the shift fills the 30 unlabelled end rows). Corrected the count, still exact; the tolerance check was not changed.
  - On real BTC data the max difference is 1.05e-15 over 3289 rows (one-off console check).
- New `risk_persistence_check` block in `ml/reports/{asset}/baselines.json`. Re-ran all three assets: exit 0, `git_dirty: true` (this task is uncommitted; HEAD a78f98f).

| Spearman(vol_30d, fwd_vol_30d) [95% CI] | BTC                        | ETH                         | SOL                        |
| --------------------------------------- | -------------------------- | --------------------------- | -------------------------- |
| train                                   | 0.465702 [0.2883, 0.6063]  | 0.464212 [0.2702, 0.6199]   | 0.523997 [0.2979, 0.6695]  |
| validation                              | -0.167378 [-0.4355, 0.159] | 0.082533 [-0.447, 0.3315]   | 0.297256 [-0.1375, 0.5979] |
| test                                    | 0.006854 [-0.3887, 0.3615] | -0.113481 [-0.3712, 0.2169] | -0.191428 [-0.5972, 0.172] |
| full labelled (n)                       | 0.505931 (3289)            | 0.463487 (3289)             | 0.585925 (2199)            |
| non-overlapping every 30th row (points) | 0.520186 (110)             | 0.445547 (110)              | 0.563747 (74)              |

- VERIFIED: alignment is correct (identity test passes; train Spearman positive with CIs above 0).
- HYPOTHESIS: the near-zero/negative validation and test values reflect a regime effect (calmer, narrower-range volatility since 2024), plus small samples (n_effective 10-16). Not proven.
- Reproducibility fix: `ml/gitinfo.py` now holds the git metadata for every report writer. `git_dirty` ignores ml/reports/ and git-ignored files, and warns on stderr when true. `ml/tests/test_gitinfo.py` adds 6 tests on a temporary fixture repo. `python -m pytest ml` -> `59 passed`.
- Follow-up: added `fwd_vol_30d_spread` and `vol_30d_spread` (n, min, p5-p95, max, std, IQR per split, labelled rows) to baselines.json. VERIFIED: test std and IQR of fwd_vol_30d are 36-56% of train for all three assets (numbers in the verify block, step 6). The explanation stays a HYPOTHESIS.

## How to verify the power check yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Tests (hand-made numbers, offline)
python -m pytest ml/tests/test_power_check.py -q

# 2. Re-build (reads the existing walkforward_price.json and walkforward_risk.json; runs no models)
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.power_check --asset $a; "$a exit: $LASTEXITCODE" }

# 3. n_effective, price half-width and % of last-value MAE, risk half-width (Spearman)
python -c "import json; [print(a, (p:=(d:=json.load(open(f'ml/reports/{a}/power_check.json')))['price'])['n_effective'], p['ci_half_width'], p['half_width_pct_of_last_value_mae'], d['risk']['ci_half_width_spearman']) for a in ('btc','eth','sol')]"

# 4. Cross-check one value by hand from the source report: (high - low) / 2
python -c "import json; c=json.load(open('ml/reports/btc/walkforward_risk.json'))['confirmation_last_40pct']['paired_diff_spearman_top_minus_persistence']; print((c['high']-c['low'])/2)"
```

Expected (observed 2026-10-19):

1. `3 passed`.
2. `wrote ...power_check.json` and `exit: 0` for each asset.
3. Output:
   - `btc 27.7 0.008646 7.733277 0.214335`
   - `eth 27.7 0.009655 7.074245 0.152608`
   - `sol 14.8 0.021625 12.106436 0.237515`
4. `0.214335`, the same as the BTC risk half-width in step 3.

## How to verify Phase 4b-1 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the price model tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_price_model.py -q

# 2. Re-run (needs ml/data/raw/*.csv). WARNING appears only if code outside ml/reports/ is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward_price --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Config count, best baseline, top config, confirmation size, paired MAE difference, verdict, sealing
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_price.json')))['configs_declared']['count'], d['ranking_first_60pct']['best_baseline'], (c:=d['confirmation_last_40pct'])['top_config'], c['n_effective'], round((x:=c['paired_diff_mae_last_value_minus_top'])['estimate'],6), round(x['low'],6), round(x['high'],6), d['verdict']['approved'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 4. Pooled return MAE of every predictor on all folds
python -c "import json; [print(a, {k: v['return']['mae_return'] for k, v in json.load(open(f'ml/reports/{a}/walkforward_price.json'))['all_folds'].items()}) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `97 passed`; the price model file shows `12 passed`.
2. `wrote ...walkforward_price.json` and `exit: 0` for each asset.
3. Output:
   - `btc 3 last_value ridge_all_a1000 27.7 0.001055 -0.00794 0.009353 False 2820`
   - `eth 3 last_value hgb_d2 27.7 -0.000785 -0.010447 0.008863 False 2820`
   - `sol 3 last_value ridge_all_a1000 14.8 -0.004377 -0.023187 0.020063 False 1893`
4. Output:
   - `btc {'ridge_all_a100': 0.153931, 'ridge_all_a1000': 0.151327, 'hgb_d2': 0.156496, 'last_value': 0.149519, 'drift': 0.149914}`
   - `eth {'ridge_all_a100': 0.202902, 'ridge_all_a1000': 0.198734, 'hgb_d2': 0.19767, 'last_value': 0.194302, 'drift': 0.197344}`
   - `sol {'ridge_all_a100': 0.245028, 'ridge_all_a1000': 0.239465, 'hgb_d2': 0.248905, 'last_value': 0.233252, 'drift': 0.235037}`

- Ridge and HGB are deterministic (random_state=0), so a re-run on the same data reproduces these values.

## How to verify Phase 4a yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the risk model tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_risk_model.py -q

# 2. Re-run (needs ml/data/raw/*.csv; takes under a minute per asset). WARNING appears only if code is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward_risk --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Config count, top config, confirmation size, paired difference and verdict
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_risk.json')))['configs_declared']['count'], (c:=d['confirmation_last_40pct'])['top_config'], c['n_effective'], c['paired_diff_spearman_top_minus_persistence']['estimate'], round(c['paired_diff_spearman_top_minus_persistence']['low'],4), round(c['paired_diff_spearman_top_minus_persistence']['high'],4), d['verdict']['approved'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 4. Pooled Spearman of every predictor on all folds
python -c "import json; [print(a, {k: v['spearman'] for k, v in json.load(open(f'ml/reports/{a}/walkforward_risk.json'))['all_folds'].items()}) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `85 passed`; the risk model file shows `16 passed`.
2. `wrote ...walkforward_risk.json` and `exit: 0` for each asset.
3. Output:
   - `btc 4 ridge_all_a10 27.7 0.056201 -0.1805 0.2482 False 2820`
   - `eth 4 hgb_d3 27.7 -0.137621 -0.24 0.0652 False 2820`
   - `sol 4 ridge_all_a10 14.8 -0.221018 -0.4605 0.0145 False 1893`
4. Output:
   - `btc {'har_ridge_a1': 0.407905, 'ridge_all_a1': 0.457404, 'ridge_all_a10': 0.46241, 'hgb_d3': 0.383628, 'persistence': 0.347215}`
   - `eth {'har_ridge_a1': 0.522056, 'ridge_all_a1': 0.515135, 'ridge_all_a10': 0.517704, 'hgb_d3': 0.542037, 'persistence': 0.515039}`
   - `sol {'har_ridge_a1': 0.168541, 'ridge_all_a1': 0.211465, 'ridge_all_a10': 0.211227, 'hgb_d3': 0.082843, 'persistence': 0.210949}`

- HGB and Ridge are deterministic (random_state=0), so a re-run on the same data reproduces these values exactly.

## How to verify Phase 4.0 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the walk-forward tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_walkforward.py -v

# 2. Re-run (needs ml/data/raw/*.csv). A WARNING line appears only if code outside ml/reports/ is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Counts, sealing evidence and key pooled numbers
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_baselines.json')))['price']['pooled']['n_folds'], d['price']['pooled']['n_pooled'], d['metadata']['rows_built'], d['metadata']['max_label_row_reached'], d['metadata']['sealed_test_first_date'], round(d['price']['pooled']['last_value']['mae_price'],2), d['risk']['pooled']['persistence_ranking']['spearman']) for a in ('btc','eth','sol')]"

# 4. The fold geometry by hand (D21): BTC/ETH b2=2821 -> 68 folds, origins 760..2770
python -c "from ml.evaluation.walkforward import make_folds; f=make_folds(3319, 2821); print(len(f), f[0].origin, f[-1].origin, len(f[0].train), f[-1].predict)"
```

Expected (observed 2026-10-19):

1. `66 passed`; the walk-forward file shows 7 passed.
2. `wrote ...walkforward_baselines.json` and `exit: 0` for each asset.
3. Output:
   - `btc 68 2031 [0, 2821] 2820 2025-06-07 5456.61 0.347215`
   - `eth 68 2031 [0, 2821] 2820 2025-06-07 346.78 0.515039`
   - `sol 37 1104 [0, 1894] 1893 2025-11-17 22.56 0.210949`
4. `68 760 2770 730 range(2770, 2791)`

- `max_label_row_reached` must stay below the b2 shown in `rows_built`. If raw data is re-fetched, n and b2 grow and these numbers change.

## How to verify Phase 3 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests (offline, hand-made fixtures; test_gitinfo uses a temporary fixture git repo)
python -m pytest ml -q

# 2. Re-run the baselines (needs ml/data/raw/*.csv; rewrites generated_at and git fields only).
#    git_dirty = uncommitted changes OUTSIDE ml/reports/ (tracked or untracked, git-ignored files excluded).
#    Changed report files never make it true. If true, a one-line WARNING goes to stderr; the run still completes.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_baselines --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Sections present + key test numbers
python -c "import json; [print(a, all(set((d:=json.load(open(f'ml/reports/{a}/baselines.json')))[s])=={'validation','test'} for s in ('price','direction','risk','strategy')), round(d['price']['test']['last_value']['mae_price'],2), d['direction']['test']['train_majority']['accuracy'], d['risk']['test']['persistence_ranking']['spearman'], d['strategy']['test']['n_windows']) for a in ('btc','eth','sol')]"

# 4. A null with a note (SOL test has no high-risk rows)
python -c "import json; r=json.load(open('ml/reports/sol/baselines.json'))['risk']['test']['persistence']; print(r['per_class']['high']); print(r['note'][:60])"

# 5. Sanity check: identity test, then the risk persistence Spearman values
python -m pytest ml -q -k fwd_vol_shifted
python -c "import json; [print(a, *[(k, (c:=json.load(open(f'ml/reports/{a}/baselines.json'))['risk_persistence_check'])[k]['spearman']) for k in ('train','validation','test','full_labelled','full_non_overlapping')]) for a in ('btc','eth','sol')]"

# 6. Volatility spread per split (std and IQR of fwd_vol_30d), and the git state recorded in the report
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/baselines.json')))['metadata']['git_dirty'], *[(s, v['std'], v['iqr']) for s, v in d['fwd_vol_30d_spread'].items()]) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `66 passed` (59 at the end of Phase 3; Phase 4.0 added 7).
2. `wrote ...baselines.json` and `exit: 0` for each asset, with no WARNING line on a committed tree.
3. Output:
   - `btc True 8095.51 0.655983 0.006854 16`
   - `eth True 439.12 0.566239 -0.113481 16`
   - `sol True 13.82 0.704918 -0.191428 11`
4. `{'precision': None, 'recall': None, 'support': 0, 'predicted': 0}`, then `class(es) ['high'] never occur in the actual labels: their r`.
5. `1 passed, 65 deselected`, then:
   - `btc ('train', 0.465702) ('validation', -0.167378) ('test', 0.006854) ('full_labelled', 0.505931) ('full_non_overlapping', 0.520186)`
   - `eth ('train', 0.464212) ('validation', 0.082533) ('test', -0.113481) ('full_labelled', 0.463487) ('full_non_overlapping', 0.445547)`
   - `sol ('train', 0.523997) ('validation', 0.297256) ('test', -0.191428) ('full_labelled', 0.585925) ('full_non_overlapping', 0.563747)`
6. Output (git_dirty is `False` when everything outside ml/reports/ is committed, even after step 2 rewrote the reports):
   - `btc False ('train', 0.015606, 0.015899) ('validation', 0.00643, 0.00882) ('test', 0.006979, 0.007573)`
   - `eth False ('train', 0.018985, 0.021384) ('validation', 0.009016, 0.013563) ('test', 0.009042, 0.01207)`
   - `sol False ('train', 0.024828, 0.027889) ('validation', 0.012379, 0.015975) ('test', 0.009178, 0.009948)`

- If raw data is re-fetched later, test numbers shift; validation numbers stay the same unless n changes the split boundaries.

## Phase 2 (features, labels, splits): what ran (from repo root, 2026-10-19)

- Docs: D18 (split n after warm-up) and D19 (train-only thresholds) added to DECISIONS.md.
- config.py: added `WARMUP_ROWS = 30`, `DIRECTION_FLAT_PERCENTILE = 40`, `RISK_PERCENTILES = (33, 67)`.
- New modules:
  - `ml/features/features.py`: `build_features(df)`, 10 trailing-window columns, first 30 rows dropped. Refuses data with gaps (row windows equal day windows only without gaps).
  - `ml/labels/labels.py`: `fwd_return_30d`, `fwd_vol_30d`, `build_labels`, `fit_thresholds` (D19), `apply_thresholds`. Direction: UP if r > t, DOWN if r < -t, else FLAT. Risk: low if vol <= p33, high if vol > p67, else medium.
  - `ml/evaluation/splits.py`: `make_splits(n)` (D18, exact fractions so 0.70n has no float error), `split_dates`.
  - `ml/data/dataset_summary.py`: refuses an asset whose validation report did not pass; writes `ml/reports/data/{asset}_dataset_summary.json`.
- `ml/tests/test_leakage.py`: required tests a-g plus thresholds-to-classes, warm-up/no-NaN and gap-refusal tests.
- `python -m pytest ml` -> `33 passed`.
  - First run: 1 failure in test d at n=200. Not leakage: n=200 gives b2-30 = b1 = 140, so validation is empty and `make_splits` correctly raises. Moved n=200 to the "too small raises" test and used n=250 in test d. No assertion was weakened.
- `python -m ml.data.dataset_summary --asset btc|eth|sol` -> exit 0 for all three; `feature_nan_count` 0.

|                                | BTC                                  | ETH                 | SOL                                  |
| ------------------------------ | ------------------------------------ | ------------------- | ------------------------------------ |
| feature rows n                 | 3319                                 | 3319                | 2229                                 |
| train rows (dates)             | 2293 (2017-09-16 to 2023-12-26)      | 2293 (same)         | 1530 (2020-09-10 to 2024-11-17)      |
| validation rows (dates)        | 468 (2024-01-26 to 2025-05-07)       | 468 (same)          | 304 (2024-12-18 to 2025-10-17)       |
| test rows / labelled (dates)   | 498 / 468 (2025-06-07 to 2026-10-17) | 498 / 468 (same)    | 335 / 305 (2025-11-17 to 2026-10-17) |
| direction flat threshold \|r\| | 0.108207                             | 0.134363            | 0.172938                             |
| risk vol thresholds p33 / p67  | 0.027831 / 0.037694                  | 0.035513 / 0.049568 | 0.04593 / 0.061528                   |

- Finding to carry into Phase 3: class balance shifts a lot after train, because recent markets were calmer than 2017-2023. Example: BTC test risk is 92.74% low, 6.2% high; SOL test risk has 0.0% high (all from `{asset}_dataset_summary.json`). This is expected with train-only thresholds (D19), not a bug, but accuracy on test must be compared against a majority-class baseline.

## How to verify Phase 2 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the leakage tests (offline, hand-made fixtures)
python -m pytest ml -q
python -m pytest ml/tests/test_leakage.py -v

# 2. Re-build the summaries (needs ml/data/raw/*.csv; rewrites generated_at only)
foreach ($a in 'btc','eth','sol') { python -m ml.data.dataset_summary --asset $a | Out-Null; "$a exit: $LASTEXITCODE" }

# 3. Key numbers from the tracked reports
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/data/{a}_dataset_summary.json')))['n_feature_rows'], d['feature_nan_count'], {k: (s['rows'], s['labelled_rows'], s['first_date'][:10]) for k, s in d['splits'].items()}) for a in ('btc','eth','sol')]"

# 4. The split rule by hand (D18): n=3319 -> b1=2323, b2=2821
python -c "from ml.evaluation.splits import make_splits; print(make_splits(3319))"
```

Expected (observed 2026-10-19):

1. `33 passed`; the leakage file shows 23 passed test cases.
2. `btc exit: 0`, `eth exit: 0`, `sol exit: 0`.
3. Output:
   - `btc 3319 0 {'train': (2293, 2293, '2017-09-16'), 'validation': (468, 468, '2024-01-26'), 'test': (498, 468, '2025-06-07')}`
   - `eth 3319 0 {'train': (2293, 2293, '2017-09-16'), 'validation': (468, 468, '2024-01-26'), 'test': (498, 468, '2025-06-07')}`
   - `sol 2229 0 {'train': (1530, 1530, '2020-09-10'), 'validation': (304, 304, '2024-12-18'), 'test': (335, 305, '2025-11-17')}`
4. `{'train': range(0, 2293), 'validation': range(2323, 2791), 'test': range(2821, 3319)}`

- If you re-fetch raw data later, n grows and the test end date moves; thresholds and balances shift slightly.

## Phase 1b (ETH, SOL): what ran (from repo root, 2026-10-18)

- No code changed: fetch.py, loader.py and validate.py already take `--asset`.
- `python -m ml.data.fetch --asset eth`: 4 pages, 3350 bars received, 3349 written, 1 unclosed dropped.
- `python -m ml.data.fetch --asset sol`: 3 pages, 2260 bars received, 2259 written, 1 unclosed dropped.
- No HTTP 403/451 and no retries. Both `validate` runs exited 0 with `passed: true`.
- `python -m pytest ml` -> `10 passed` (no new tests).
- Reports: `ml/reports/data/eth_validation.json`, `sol_validation.json` (tracked, D15).

| Field                         | BTC        | ETH        | SOL        |
| ----------------------------- | ---------- | ---------- | ---------- |
| rows                          | 3349       | 3349       | 2259       |
| first bar                     | 2017-08-17 | 2017-08-17 | 2020-08-11 |
| last bar                      | 2026-10-17 | 2026-10-17 | 2026-10-17 |
| missing days                  | 0          | 0          | 0          |
| excess kurtosis (> 1)         | 16.0117    | 12.1349    | 8.4565     |
| lag-1 autocorr of \|r\| (> 0) | 0.1769     | 0.1689     | 0.2698     |

- Done-when met: pytest passes; both reports have kurtosis > 1 and autocorr > 0; missing days listed (none).
- BTC files untouched. Phase 1b explanation: docs/phases/PHASE_1b_eth_sol_data.md.

## How to verify Phase 1b yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Unit tests (offline)
python -m pytest ml -q

# 2. The tracked evidence reports
Get-Content ml\reports\data\eth_validation.json
Get-Content ml\reports\data\sol_validation.json

# 3. The raw files
python -c "import pandas as pd; [print(a, len(d:=pd.read_csv(f'ml/data/raw/{a}_1d.csv')), d.timestamp.iloc[0], d.timestamp.iloc[-1]) for a in ('eth','sol')]"

# 4. Re-validate the same files: same numbers expected (this rewrites the report's validated_at only)
python -m ml.data.validate --asset eth | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'
python -m ml.data.validate --asset sol | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'
```

Expected (observed 2026-10-18):

1. `10 passed`.
2. ETH: `"rows": 3349`, `"missing_days": []`, `"excess_kurtosis": 12.1349`, `"abs_return_lag1_autocorr": 0.1689`, `"passed": true`. SOL: `"rows": 2259`, `"missing_days": []`, `"excess_kurtosis": 8.4565`, `"abs_return_lag1_autocorr": 0.2698`, `"passed": true`.
3. `eth 3349 2017-08-17T00:00:00Z 2026-10-17T00:00:00Z` and `sol 2259 2020-08-11T00:00:00Z 2026-10-17T00:00:00Z`.
4. The same rows, kurtosis, autocorr and `passed` values as in 2.

- If you re-fetch later, rows grow by one per day and kurtosis/autocorr move slightly (still > 1 and > 0).

## Phase 1 (BTC): what ran (from repo root)

- `python -m pytest ml` -> `10 passed`.
  - The tests use hand-made fixtures, not market data, and make no network calls.
- `python -m ml.data.fetch --asset btc`
  - Fetched at 2026-10-18T11:07:30Z: 4 pages, 3350 bars received, 3349 written.
  - 1 bar dropped because it had not closed yet.
  - No HTTP 403/451 and no retries needed.
- `python -m ml.data.validate --asset btc` -> exit 0, `passed: true`. Observed values:

  | Field                                | Value                   |
  | ------------------------------------ | ----------------------- |
  | rows                                 | 3349                    |
  | first / last bar                     | 2017-08-17 / 2026-10-17 |
  | missing days                         | 0                       |
  | duplicates                           | 0                       |
  | non-positive prices                  | 0                       |
  | OHLC-inconsistent rows               | 0                       |
  | close min                            | 3189.02 (2017-09-14)    |
  | close max                            | 124658.54 (2025-10-06)  |
  | excess kurtosis of daily log returns | 16.0117 (> 1)           |
  | lag-1 autocorr of \|log returns\|    | 0.1769 (> 0)            |

- Done-when met: pytest passes; kurtosis > 1; \|r\| autocorr > 0; missing days listed (none).

## Phase 1 (BTC): files

- `ml/data/__init__.py`
- `ml/data/loader.py`: the one raw loader (`load_raw`, path helpers).
- `ml/data/fetch.py`
  - Binance /api/v3/klines, 1d, startTime=0, limit=1000 pages.
  - Retries with backoff on network errors and 5xx; obeys Retry-After on 418/429.
  - Stops immediately on 403/451 (`FetchBlocked`).
  - Drops bars whose close_time has not passed.
  - Writes prices exactly as Binance returns them.
- `ml/data/validate.py`
  - Pure check functions plus `validate(df)`.
  - Writes `ml/reports/data/btc_validation.json`. Exits 1 if any check fails.
  - Log returns are computed only between consecutive calendar days, so a gap never becomes a fake 2-day return.
  - Too few returns gives `null` instead of NaN, so the JSON stays valid.
- `ml/tests/test_validate.py`: 9 tests.
- Data files:
  - `ml/data/raw/btc_1d.csv` and `btc_1d.fetch.json` (fetch time and source) are git-ignored.
  - `ml/reports/data/btc_validation.json` is tracked (D15).
- Extra checks beyond the task list, reported but not part of done-when: `ohlc_inconsistent_rows`, `n_returns`, `validated_at`.
- Docs:
  - D17 added.
  - AGENTS rule 15 added.
  - PLAN.md has a "How to verify" column.

## Documentation task (2026-10-18, docs only; no code, data or tests changed)

- AGENTS rule 16 and a Docs list added.
- Created docs/GLOSSARY.md, docs/phases/TEMPLATE.md, PHASE_0_scaffold.md, PHASE_1_btc_data.md.
- Open "UNCLEAR: ask the author" items are in section 7 of the Phase 0 and Phase 1 files.
- Phase 1b must also ship docs/phases/PHASE*1b*<name>.md before it counts as done.

## How to verify Phase 0 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest
python -c "import ml.config as c; print(c.ASSETS, c.ASSET_SYMBOLS, c.HORIZON_DAYS, c.SPLIT_FRACTIONS, c.EMBARGO_DAYS, c.ANNUALISATION_DAYS)"
git check-ignore -q ml/data/raw/x.csv;               "data/raw ignored:          $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/data/fetch.py;                "fetch.py ignored:          $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/artifacts/btc/model.pkl;      "artifact model ignored:    $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/artifacts/btc/metadata.json;  "artifact metadata ignored: $($LASTEXITCODE -eq 0)"
```

Expected:

- `('btc', 'eth', 'sol') {'btc': 'BTCUSDT', 'eth': 'ETHUSDT', 'sol': 'SOLUSDT'} 30 {'train': 0.7, 'validation': 0.15, 'test': 0.15} 30 365`
- Then `True`, `False`, `True`, `False`.

## How to verify Phase 1 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Unit tests (offline)
python -m pytest ml -q

# 2. The tracked evidence report
Get-Content ml\reports\data\btc_validation.json

# 3. The raw file
python -c "import pandas as pd; d=pd.read_csv('ml/data/raw/btc_1d.csv'); print('rows', len(d)); print('first', d.timestamp.iloc[0], d.close.iloc[0]); print('last ', d.timestamp.iloc[-1], d.close.iloc[-1]); print('columns', list(d.columns))"

# 4. Re-validate the same file: must reproduce the same numbers
python -m ml.data.validate --asset btc | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'

# 5. Optional, needs network: re-fetch, then re-validate
python -m ml.data.fetch --asset btc
python -m ml.data.validate --asset btc; "exit code: $LASTEXITCODE"
```

Expected (observed 2026-10-18):

1. `10 passed`.
2. `"passed": true`, `"missing_days": []`, `"excess_kurtosis": 16.0117`, `"abs_return_lag1_autocorr": 0.1769`, `"rows": 3349`.
3. Output:
   - `rows 3349`
   - `first 2017-08-17T00:00:00Z 4285.08`
   - `last  2026-10-17T00:00:00Z 81491.04`
   - `columns ['asset', 'timestamp', 'open', 'high', 'low', 'close', 'volume']`
4. The same four values as in 2.
5. After a re-fetch:
   - `first` stays 2017-08-17 and the first close stays 4285.08.
   - rows = 3349 + one per day since 2026-10-17.
   - The last timestamp is yesterday (UTC); today's open bar is dropped.
   - Kurtosis and autocorr move only slightly (still > 1 and > 0).
   - `exit code: 0`.
   - If the exit code is 1, a check failed: look at `checks` in the JSON.

## Open questions for the user

1. Backend host/CORS needs for the ML service?
2. Does Person A's MongoDB need to be the live price source later? (loader stays swappable)
3. Which extra assets after BTC/ETH/SOL? (WBTC treated as BTC for now)
4. `ml/wbtc_validation_model.csv` is an untracked file in ml/, left over from v1. I did not touch it. Delete it or move it out of ml/?

## Resolved (2026-10-18)

- D14: Python 3.10-3.12.
- D15: validation reports tracked in reports/data/.
- D16 and D17: embargo cut from the end of the earlier split. Validation and labelled test each have about 0.15n-30 rows; only the test date range is exact.
- ASSET_SYMBOLS in config.py.
