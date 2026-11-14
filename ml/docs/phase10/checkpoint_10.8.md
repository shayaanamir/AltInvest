# Checkpoint 10.8: the one-time sealed fair-value test (D79)

Branch `phase-10-nft`. The protocol is D79, committed in `2e6cacc` before any sealed access. The run used commit
`cb6f00cbfc5442b482db67cc30fe5ed539f5d214` with a clean tree (`git_dirty: false`).

**Result: PASS.** The serving rule stays as committed: the model for 6 collections, B2 for lilpudgys, no range.
Nothing has been applied or changed after the run. Serving, the error line ("Accuracy check pending") and the live
accuracy log are untouched; that is 10.9.

## 1. Pre-flight (all passed before the run)

| Check | Result |
|---|---|
| Working tree and HEAD | Clean; HEAD = `cb6f00c` |
| `git diff 2e6cacc HEAD` on the protocol, evaluation, model and feature code (`ml/evaluation`, `ml/nft`, `ml/models`, `ml/config.py`) | No changes. Since 2e6cacc only `ml/serving`, `ml/api`, tests, backend, frontend and docs changed, all reported in checkpoint_10.7; the sealed script imports none of them |
| Backend Mongo | `altinvest-backend` has `MONGO_URI=mongodb://mongodb:27017` (local container host, no credentials). Container created 2026-11-13 11:50 IST, before the ML-only compose step (2026-11-14 04:12 IST); it was only restarted (04:17 IST), not recreated |
| Open items in checkpoint_10.7 | None blocks: items 1-5 concern live serving and the UI. Item 6 holds (`NFT_FV_SERVE` unchanged since 2e6cacc; the report records the map it evaluated). Item 7 is review only |

## 2. The run

- One invocation: `.venv-train/Scripts/python -u -m ml.evaluation.run_nft_sealed_fv --sealed`, exit 0, about 35
  minutes (report `generated_at` 2026-11-14T10:08:13Z). No crash, no re-run, no code change.
- Outputs:
  - `ml/reports/nft/sealed_fair_value.json` (sha256 `e70148f4...ae97a`);
  - `ml/reports/nft/sealed_fair_value.rows.parquet` (gitignored, 39,399 rows; sha256
    `3181e9b8f1620a18baa0e57ac928aaf3511da66d0ac4da39a9a0d8fe9c6dc865`);
  - the script's log `ml/docs/phase10/logs/10.8_sealed_run.log`;
  - the full console output `ml/docs/phase10/logs/10.8_sealed_run_cb6f00c_stdout.log` (same lines, plus the exit
    code).
- Item manifest sha256 `1d0c12d1...67dfd` (v3 snapshot).
- Window 2026-02-01 to 2026-11-10: 39,399 clean sales on 283 calendar dates (every date in the window), about 40
  seven-day blocks.

## 3. PASS / FAIL (D79)

Pooled MdAPE on price, all 7 collections, 39,399 sales:

| | MdAPE |
|---|---|
| **Served** (model for 6, B2 for lilpudgys) | **0.0294** |
| B0 floor | 0.0353 (**best baseline**) |
| B2 decile 90-day | 0.0362 |
| B1 rarity decile | 0.0376 |
| fv_pooled_l1_nl15 everywhere (descriptive, not the served setup) | 0.0275 |

Paired difference MdAPE(B0) − MdAPE(served): **0.0059, 95% CI [0.0034, 0.0085]**. Moving blocks of 7 calendar dates,
1,000 resamples, seed 0. Estimate > 0 and low > 0, so **PASS**: "keep the serving rule". No range is served
(`range_served: null`).

## 4. Descriptive only (changes nothing)

**By collection** (MdAPE):

| Collection | n | Served | Model | B0 | B1 | B2 |
|---|---|---|---|---|---|---|
| azuki | 3,716 | 0.0384 | 0.0384 | 0.0439 | 0.0496 | 0.0478 |
| boredapeyachtclub | 2,859 | 0.0358 | 0.0358 | 0.0443 | 0.0427 | 0.0464 |
| doodles-official | 4,173 | 0.0316 | 0.0316 | 0.0379 | 0.0424 | 0.0388 |
| lilpudgys (served = B2) | 11,979 | 0.0281 | 0.0223 | 0.0280 | 0.0317 | 0.0281 |
| milady | 3,601 | 0.0300 | 0.0300 | 0.0364 | 0.0378 | 0.0375 |
| mutant-ape-yacht-club | 7,808 | 0.0325 | 0.0325 | 0.0525 | 0.0483 | 0.0498 |
| pudgypenguins | 5,263 | 0.0196 | 0.0196 | 0.0262 | 0.0288 | 0.0272 |

**By rarity decile** (1 = rarest 10%):

| Decile | n | Served | Model | B0 | B1 | B2 |
|---|---|---|---|---|---|---|
| 1 | 1,980 | 0.0906 | 0.0860 | 0.1822 | 0.1092 | 0.1149 |
| 2 | 3,011 | 0.0448 | 0.0429 | 0.0668 | 0.0551 | 0.0561 |
| 3 | 3,402 | 0.0326 | 0.0317 | 0.0406 | 0.0463 | 0.0436 |
| 4 | 4,070 | 0.0277 | 0.0259 | 0.0335 | 0.0377 | 0.0357 |
| 5 | 4,056 | 0.0277 | 0.0257 | 0.0320 | 0.0367 | 0.0346 |
| 6 | 4,374 | 0.0279 | 0.0260 | 0.0323 | 0.0351 | 0.0337 |
| 7 | 4,444 | 0.0259 | 0.0235 | 0.0293 | 0.0323 | 0.0308 |
| 8 | 4,417 | 0.0258 | 0.0238 | 0.0309 | 0.0334 | 0.0327 |
| 9 | 4,921 | 0.0255 | 0.0238 | 0.0294 | 0.0316 | 0.0296 |
| 10 | 4,724 | 0.0254 | 0.0237 | 0.0300 | 0.0316 | 0.0306 |

**Sale counts and MdAPE by month** (training cutoff = month start − 7 days):

| Month | Train cutoff | n train | n test | Served | Model | B0 | B1 | B2 |
|---|---|---|---|---|---|---|---|---|
| 2026-02 | 2026-01-25 | 144,592 | 5,609 | 0.0234 | 0.0210 | 0.0291 | 0.0283 | 0.0267 |
| 2026-03 | 2026-02-22 | 150,420 | 3,358 | 0.0217 | 0.0185 | 0.0211 | 0.0324 | 0.0281 |
| 2026-04 | 2026-03-25 | 154,456 | 5,502 | 0.0347 | 0.0320 | 0.0556 | 0.0441 | 0.0447 |
| 2026-05 | 2026-04-24 | 158,470 | 3,874 | 0.0283 | 0.0269 | 0.0328 | 0.0361 | 0.0369 |
| 2026-06 | 2026-05-25 | 163,611 | 3,734 | 0.0291 | 0.0268 | 0.0314 | 0.0352 | 0.0350 |
| 2026-07 | 2026-06-24 | 167,502 | 3,277 | 0.0287 | 0.0248 | 0.0289 | 0.0373 | 0.0357 |
| 2026-08 | 2026-07-25 | 170,342 | 3,596 | 0.0281 | 0.0261 | 0.0342 | 0.0368 | 0.0345 |
| 2026-09 | 2026-08-25 | 174,158 | 3,987 | 0.0299 | 0.0285 | 0.0339 | 0.0416 | 0.0369 |
| 2026-10 | 2026-09-24 | 178,065 | 5,529 | 0.0416 | 0.0428 | 0.0528 | 0.0507 | 0.0498 |
| 2026-11 (1-10 Nov) | 2026-10-25 | 183,669 | 933 | 0.0363 | 0.0359 | 0.0445 | 0.0430 | 0.0426 |

**B2's 80% range coverage** (not served under D79 whatever the result):
- Pooled 0.829; lower-tail miss 0.060, upper-tail miss 0.111.
- By collection: azuki 0.784, boredapeyachtclub 0.728, doodles-official 0.895, lilpudgys 0.899, milady 0.843,
  mutant-ape-yacht-club 0.743, pudgypenguins 0.823.

## 5. Unexpected

1. **The lilpudgys guard cost accuracy on the sealed window.**
   - In 10.6 (confirmation folds), lilpudgys favoured B2: model 0.0291 vs B2 0.0276. That is why the guard sends it to
     B2.
   - On the sealed window this reverses: model **0.0223** vs B2 0.0281.
   - lilpudgys is 30% of the sealed rows (11,979 of 39,399), so the model everywhere would have scored 0.0275
     pooled, against 0.0294 served.
   - The rule PASSed as committed, and per D79 the per-collection numbers change nothing. Switching lilpudgys to the
     model now would be a choice made on the sealed set, so any sealed-set number for it would no longer be an
     untouched estimate. This is a planner decision for 10.9; I have changed nothing.
2. **The best baseline switched** from B2 (best on development, D77) to **B0, the plain floor** (0.0353 vs B2 0.0362).
   - B0 is notably bad on the rarest decile (0.182) but strong for common items.
3. **March 2026: the served setup is slightly worse than B0** (0.0217 vs 0.0211), the only month where it is.
   - July is nearly tied (0.0287 vs 0.0289).
   - The model alone beats B0 in every month.
4. **October 2026 has the highest errors of the window** for every method (served 0.0416; B0 0.0528).
   - It is the only month where the served setup beats the model everywhere (the B2 guard helped lilpudgys there).
   - April is the other high month (B0 0.0556).
5. **B2's pooled range coverage is inside the 75-85% band on the sealed window** (0.829, tails 0.060 / 0.111). On
   development it was out of band (0.8699).
   - Per collection it still varies widely, 0.728 (boredapeyachtclub) to 0.899 (lilpudgys).
   - The misses are skewed upward: sales land above the range almost twice as often as below.
   - Per D79 no range is served either way.
6. **The rarest decile is hard**: MdAPE 0.091 served, about 3.5 times the other deciles. Deciles 4-10 sit between
   0.025 and 0.028.
7. **November is partial**: 933 sales over 1-10 Nov, as declared.

Nothing failed, and no metric on dates >= 2026-01-25 was computed outside this one run. `load_sealed()` was not called; the
script reads the as-of history through `load_history("10.8")` as declared in D79.

STOP. Waiting for review before 10.9.
