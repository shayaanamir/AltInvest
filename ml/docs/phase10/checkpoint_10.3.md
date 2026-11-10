# Checkpoint 10.3: Collection risk and liquidity

Date: 2026-11-11. Branch `phase-10-nft`. Plan step 10.3; D59 (amended), D65, D66.

## 1. What ran and what changed

- Code: e00a905 (runner, pooled date-block approval, candidates) and 262dfe9 (D66 floor series plus the declared sensitivity run). D66 was committed (cd82f32) before this run.
- `python -m ml.evaluation.run_nft_risk` ran **once**, at 4ee833d with a clean tree (`git_dirty` false), on the frozen snapshot 2026-11-10 (`require_snapshot("floor")` re-hashed the file against the manifest).
  - It wrote `ml/reports/nft/walkforward_risk.json`.
  - Log: `logs/10.3_run_nft_risk.log`, with no warnings and no convergence messages.
- Liquidity (D58, rule-based, no model) comes from `ml/reports/nft/liquidity.json`, written in 10.2.
- No test rows were built: per collection, rows [0, b2) only. The maximum label row reached is b2 - 1, and the sealed test starts on 2026-07-20.

## 2. Verdict table (from walkforward_risk.json by a script, `logs/10.3_tables.md`)

report commit 4ee833d, git_dirty False, snapshot 2026-11-10, manifest sha256 90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af
floor column floor_eth_model; trials 2 {'ewma': 1, 'garch': 1}; winner ewma; served ewma

| Scope | Model | Config | Model QLIKE | Persistence QLIKE | Diff (persistence - model) | 95% CI | Spearman model / persistence | Approved | Winner |
|---|---|---|---|---|---|---|---|---|---|
| pooled (all collections) | ewma | ewma | 0.6929 | 0.9333 | 0.2404 | [0.0668, 0.5855] |  | True | True |
| azuki | ewma | ewma | 1.1656 | 1.4800 | 0.3144 | [0.0479, 0.8297] | 0.016 / -0.045 | (True, alone; reported only) |  |
| boredapeyachtclub | ewma | ewma | 0.3996 | 0.4819 | 0.0823 | [0.0149, 0.1581] | -0.353 / -0.282 | (True, alone; reported only) |  |
| doodles-official | ewma | ewma | 1.3509 | 1.8534 | 0.5026 | [0.0290, 1.3996] | -0.007 / -0.101 | (True, alone; reported only) |  |
| lilpudgys | ewma | ewma | 0.1274 | 0.1513 | 0.0239 | [0.0054, 0.0479] | 0.104 / 0.080 | (True, alone; reported only) |  |
| milady | ewma | ewma | 0.2317 | 0.2899 | 0.0582 | [-0.0319, 0.1281] | 0.131 / -0.146 | (False, alone; reported only) |  |
| mutant-ape-yacht-club | ewma | ewma | 0.8099 | 1.2744 | 0.4645 | [0.0748, 1.2632] | -0.155 / -0.183 | (True, alone; reported only) |  |
| pudgypenguins | ewma | ewma | 0.7651 | 1.0021 | 0.2370 | [0.0509, 0.6514] | -0.041 / -0.066 | (True, alone; reported only) |  |
| pooled (all collections) | garch | garch_normal | 0.8073 | 0.9333 | 0.1260 | [-0.5088, 1.2341] |  | False | False |
| azuki | garch | garch_normal | 0.5315 | 1.4800 | 0.9484 | [-0.1240, 2.8594] | 0.118 / -0.045 | (False, alone; reported only) |  |
| boredapeyachtclub | garch | garch_normal | 0.3006 | 0.4819 | 0.1813 | [0.0487, 0.3990] | -0.034 / -0.282 | (True, alone; reported only) |  |
| doodles-official | garch | garch_normal | 1.3662 | 1.8534 | 0.4872 | [-1.3171, 3.6953] | 0.190 / -0.101 | (False, alone; reported only) |  |
| lilpudgys | garch | garch_normal | 1.2134 | 0.1513 | -1.0621 | [-1.2559, -0.8560] | 0.113 / 0.080 | (False, alone; reported only) |  |
| milady | garch | garch_normal | 0.5962 | 0.2899 | -0.3062 | [-0.6456, -0.0529] | -0.324 / -0.146 | (False, alone; reported only) |  |
| mutant-ape-yacht-club | garch | garch_normal | 0.5119 | 1.2744 | 0.7625 | [0.0427, 2.2740] | 0.268 / -0.183 | (True, alone; reported only) |  |
| pudgypenguins | garch | garch_normal | 1.1314 | 1.0021 | -0.1293 | [-1.0757, 1.6054] | -0.002 / -0.066 | (False, alone; reported only) |  |

- pooled ewma: confirmation ['2026-01-10', '2026-06-19'], n_pooled 1127, n_dates 161, n_eff (rows/30) 37.6, n_eff (dates/30) 5.4; ranking n_pooled 1680; every collection not worse: True; per collection diff {azuki: 0.3144, boredapeyachtclub: 0.0823, doodles-official: 0.5026, lilpudgys: 0.0239, milady: 0.0582, mutant-ape-yacht-club: 0.4645, pudgypenguins: 0.2370}
- pooled garch: confirmation ['2026-01-10', '2026-06-19'], n_pooled 1127, n_dates 161, n_eff (rows/30) 37.6, n_eff (dates/30) 5.4; ranking n_pooled 1680; every collection not worse: False; per collection diff {azuki: 0.9484, boredapeyachtclub: 0.1813, doodles-official: 0.4872, lilpudgys: -1.0621, milady: -0.3062, mutant-ape-yacht-club: 0.7625, pudgypenguins: -0.1293}

- per collection: folds 14, pooled rows 401, n_eff 13.4, built rows [0, 641), data 2024-10-17 to 2026-07-19, max label row reached 640 (< b2 641), sealed test from 2026-07-20

- sensitivity (unguarded floor_eth_asof, reported only): would serve persistence_vol30
  - ewma: QLIKE 9.6028 vs 8.9279, diff -0.6750 [-2.6697, 0.6325], every collection not worse False, approved False
  - garch: QLIKE 2.2732 vs 8.9279, diff 6.6547 [0.1597, 18.8548], every collection not worse False, approved False

**Reading it:**
- **EWMA is approved**, pooled over the 7 collections.
  - QLIKE is 0.6929 against 0.9333 for persistence.
  - The paired 95% CI (date blocks of 30) is [0.0668, 0.5855].
  - Every collection's point estimate favours EWMA.
  - It is served for all 7 collections (D59 "all or none").
- **GARCH(1,1) normal is not approved**: the pooled CI includes 0, and lilpudgys, milady and pudgypenguins are worse than persistence.
- The per-collection rows are reported only, not separate approvals (D65a).
- Power is low. n_effective counted as confirmation dates / 30 is **5.4**: 161 distinct dates, 2026-01-10 to 2026-06-19. The CI is wide, and the sealed test (10.8) will have about 3 independent windows.

**Served from 10.4 on:**
- volatility = EWMA floor vol x sqrt(365), which feeds the D52 cone.
- risk_score = 100 x (1 - p), where p is the pooled percentile of today's EWMA among the EWMA history of the 7 NFT collections on all dates <= today. This is a separate NFT pool, not comparable to the crypto scores (D59 amended).

## 3. Liquidity scores per collection (from liquidity.json, as of 2026-11-10)

| Collection (as of 2026-11-10) | Sales 7d | Sales 30d | Vol 7d ETH | Vol 30d ETH | Liquidity score | Label | Illiquid | Days scored | Days illiquid |
|---|---|---|---|---|---|---|---|---|---|
| azuki | 55 | 525 | 29.6 | 307.4 | 12.60 | Low | False | 701 | 0 |
| boredapeyachtclub | 96 | 347 | 661.6 | 2227.2 | 38.30 | Medium | False | 701 | 0 |
| doodles-official | 39 | 357 | 12.4 | 96.8 | 3.64 | Low | False | 701 | 0 |
| lilpudgys | 234 | 1359 | 49.3 | 318.8 | 40.13 | Medium | False | 701 | 0 |
| milady | 50 | 352 | 35.4 | 274.8 | 6.83 | Low | False | 701 | 0 |
| mutant-ape-yacht-club | 125 | 810 | 117.6 | 746.8 | 34.20 | Medium | False | 701 | 0 |
| pudgypenguins | 68 | 756 | 153.2 | 1968.6 | 34.75 | Medium | False | 701 | 0 |

Labels name what is counted: "Sales on OpenSea and Blur, as reported by OpenSea" (D56). No collection was illiquid (sales_7d < 10) on any of its 701 scored days.

## 4. Tests and hash check

- `python -m pytest ml -q`: **331 passed** (10.3 adds no code beyond what 10.2's full run covered).
  - The 10 tests in `test_nft_risk.py` cover:
    - features against the hand formulas
    - gaps refused
    - test rows never built, and changing test-period floors leaves the dev rows unchanged
    - no prediction depends on a later floor (all three predictors)
    - the date-block CI equals the Phase 9 row bootstrap for one collection
    - duplicated collections add no information
    - pooled approval needs both the CI and "no collection worse"
    - the trial count
    - the runner refusing a snapshot whose hash does not match
- Snapshot manifest sha256 `90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af`, recorded in the report; `--verify` OK.
- Trial count: 2 (1 EWMA config, 1 GARCH config; baselines are not trials). The sensitivity run is not a trial.

## 5. Rule breaks and open questions

**Rule breaks:** none.

**IMPORTANT, for review: the EWMA approval depends on D66.**
- On the unguarded `floor_eth_asof` (the declared sensitivity run), persistence QLIKE is 8.93 and EWMA 9.60: EWMA is not approved, and persistence would be served.
- GARCH beats persistence on the pooled CI there ([0.16, 18.85]) but fails "no collection worse".
- The one-day floor collapses (D66 list) dominate QLIKE on the raw series.
- If the planner rejects D66, the served measure becomes persistence vol_30d (D52 amended: the cone still shows).

**Open questions:**
1. Accept D66 and therefore EWMA? Decide before 10.8.
2. The milady CI on its own includes 0. The pooled rule (D59 amended) does not need per-collection CIs, so this is not a blocker.

Continuing to 10.4 (autonomous mode).
