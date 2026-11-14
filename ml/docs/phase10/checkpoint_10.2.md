# Checkpoint 10.2: Collection data

Date: 2026-11-11. Branch `phase-10-nft`. Plan step 10.2 with the approved 10.1 changes (D52, D55, D59, D61, D62 amended in 4741616) and the autonomous D63-D66.

## 1. What ran and what changed

**Commits:**
- 4741616: approved 10.1 amendments
- 49c2202: D63-D65
- c908d91: data layer
- e00a905: risk code
- cd82f32: D66, committed before any evaluation
- 262dfe9: spike guard and test fix
- b9a56e6: snapshot-order fix
- b9a56e6: snapshot commit

**New modules** under `ml/nft/`:
- `opensea.py`, `alchemy.py`: API clients. Keys come from `.env` and are never printed.
- `collect.py`: backfill stages meta, floor, eth, sales and traits.
- `floor.py`: D55 floor, the D63 as-of floor and the D66 guard.
- `sales.py`: D56 parsing and the D57 wash rules.
- `liquidity.py`: D58.
- `traits.py`: rarity.
- `build.py`: the one builder of derived tables.
- `snapshot.py`: freeze and verify (D62, D64).
- `refresh.py`: the daily job (same pattern as ml-refresh, 00:10 UTC; the compose sidecar comes in 10.4, D65e).
- `data_summary.py`: the report writer.

**Commands.** All output is in `ml/docs/phase10/logs/`.
- `python -m ml.nft.collect --stage meta --stage floor --stage eth`. The first ETH fetch timed out on a Binance connect; it passed on retry.
- `--stage sales`: 1,126 OpenSea calls, 198,548 sales.
- `--stage traits`: Alchemy, 90,395 tokens.
- `python -m ml.nft.snapshot --date 2026-11-10`, then `--verify`: OK, all hashes match.
- `python -m ml.nft.data_summary` wrote `ml/reports/nft/data_summary.json` and `liquidity.json`.

**Backfill completeness** (`logs/10.2_sales_vs_opensea_stats.log`):
- Our 7-day and 30-day sale counts are at or above OpenSea's `/stats` for every collection; for milady the 7-day count is equal.
- 30-day differences: azuki +6%, pudgypenguins +53%.
- One cause found: 331 (tx, token) pairs appear as more than one sale event (713 rows; in 303 of them one row's buyer is another row's seller, a pass-through trade). They are kept as separate sales, because each is a recorded transfer with its own price.
- `/stats` likely counts differently (for example by transaction). This is not resolved: an open question for the planner.

**Test fix (rule: check the test or the code).** `test_spike_guard_holds_back_one_day_spikes_and_accepts_a_level_confirmed_by_a_second_day` was wrong, not the code.
- On day 5, 1.4 / 2.9 = 0.483 is outside the 2x band, and the ratio to the day before is the same, so D66 holds it back (2.9).
- On day 6, 1.0 / 1.4 = 0.71 confirms the new level.
- The expected list and the comment were corrected; `guard_spikes` is unchanged.

## 2. Tables (generated from the JSON reports by a script, `logs/10.2_tables.md`)

report commit b9a56e6, git_dirty False, manifest sha256 90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af

| Collection | Floor days | First | Last | Dup days | Gap days (>48 h) | Spike days held | Median / max point age (h) | USD days compared | median / max abs USD dev | days > 5% | Sealed test from |
|---|---|---|---|---|---|---|---|---|---|---|---|
| azuki | 785 | 2024-09-17 | 2026-11-10 | 0 | 0 | 3 | 9.6 / 31.6 | 784 | 0.0108 / 0.2182 | 74 | 2026-07-20 |
| boredapeyachtclub | 785 | 2024-09-17 | 2026-11-10 | 0 | 0 | 0 | 9.0 / 44.1 | 785 | 0.0104 / 0.2316 | 68 | 2026-07-20 |
| doodles-official | 785 | 2024-09-17 | 2026-11-10 | 0 | 2 | 2 | 9.3 / 81.5 | 783 | 0.0093 / 0.2189 | 75 | 2026-07-20 |
| lilpudgys | 785 | 2024-09-17 | 2026-11-10 | 0 | 0 | 6 | 9.2 / 46.7 | 784 | 0.0116 / 0.2071 | 81 | 2026-07-20 |
| milady | 785 | 2024-09-17 | 2026-11-10 | 0 | 0 | 0 | 9.5 / 24.0 | 785 | 0.0107 / 0.2143 | 72 | 2026-07-20 |
| mutant-ape-yacht-club | 785 | 2024-09-17 | 2026-11-10 | 0 | 3 | 1 | 8.8 / 116.4 | 782 | 0.0106 / 0.2190 | 75 | 2026-07-20 |
| pudgypenguins | 785 | 2024-09-17 | 2026-11-10 | 0 | 3 | 0 | 9.4 / 90.9 | 782 | 0.0120 / 0.2169 | 81 | 2026-07-20 |

Gap dates: {'doodles-official': ['2026-04-01', '2026-04-02'], 'mutant-ape-yacht-club': ['2024-11-11', '2024-11-12', '2024-11-13'], 'pudgypenguins': ['2024-10-23', '2024-11-18', '2024-11-19']}

| Collection | Sales raw | R1 | R2 | R3 | Kept | Sales first | Sales last | Kept per month | Marketplaces (raw) | Dropped events | Tokens | Without traits | Supply (OpenSea) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| azuki | 23736 | 28 | 391 | 21 | 23296 | 2024-11-10 | 2026-11-10 | 932 | {'unknown': 13661, 'blur': 9979, 'opensea': 96} | {'payment_token': 1} | 10000 | 40 | 10000 |
| boredapeyachtclub | 9620 | 41 | 156 | 6 | 9417 | 2024-11-10 | 2026-11-10 | 377 | {'unknown': 6428, 'blur': 3086, 'opensea': 106} | {'payment_token': 9} | 10000 | 42 | 9996 |
| doodles-official | 27641 | 43 | 529 | 29 | 27040 | 2024-11-10 | 2026-11-10 | 1082 | {'unknown': 19539, 'blur': 8051, 'opensea': 51} | {} | 10000 | 181 | 9998 |
| lilpudgys | 67319 | 75 | 1445 | 14 | 65785 | 2024-11-10 | 2026-11-10 | 2631 | {'unknown': 47384, 'blur': 19601, 'opensea': 334} | {'payment_token': 2} | 21935 | 24 | 21932 |
| milady | 18184 | 26 | 275 | 7 | 17876 | 2024-11-10 | 2026-11-10 | 715 | {'unknown': 10865, 'blur': 7246, 'opensea': 73} | {} | 10000 | 0 | 9976 |
| mutant-ape-yacht-club | 29268 | 56 | 642 | 11 | 28559 | 2024-11-10 | 2026-11-10 | 1142 | {'unknown': 20802, 'blur': 8268, 'opensea': 198} | {'payment_token': 3} | 19572 | 3 | 19571 |
| pudgypenguins | 22780 | 42 | 509 | 4 | 22225 | 2024-11-10 | 2026-11-10 | 889 | {'unknown': 11902, 'blur': 10810, 'opensea': 68} | {'payment_token': 14} | 8888 | 58 | 8888 |

future dates: 0; ETH-USD rows 3373 ['2017-08-17', '2026-11-10'] {'open': 3372, 'prev_close': 1}

| File | Rows | sha256 | Range |
|---|---|---|---|
| floor.parquet | 5495 | `4f0062e1e494feef6c8ad390f2c4e648eb596692166cea13d328355fb9488343` | ['2024-09-17', '2026-11-10'] |
| floor_points.parquet | 5483 | `9de584897f4b4fd1117c68f4555577d31b20e23cb56b1c4e6e5b7e8f56506622` | ['2024-09-16T02:52:47Z', '2026-11-10T15:43:47Z'] |
| eth_usd.parquet | 3373 | `0cf7bfa97fd450a04cba4ff17b64d50259ecf9a4e0b6e87fca00345f240f4962` | ['2017-08-17', '2026-11-10'] |
| sales_raw.parquet | 198548 | `70a751c76ad9be057d5360cee37e1a749a98b4d67314e97404231f23a4a9e0ed` | ['2024-11-10', '2026-11-10'] |
| sales_filtered.parquet | 194198 | `3872160c0042c9a92ab78c85f7617f10ad6fb34de59aa0c9114d1235bb861048` | ['2024-11-10', '2026-11-10'] |
| traits.parquet | 616987 | `b523224a9c4a84a0ac25dfb07652a2f523e442098ab77b14a059dd606e77499a` | None |
| tokens.parquet | 90395 | `5cac082dcc88f884196dfec334bc9f1ccc704559d70c03615e85baca30d02130` | None |

| Collection (as of 2026-11-10) | Sales 7d | Sales 30d | Vol 7d ETH | Vol 30d ETH | Liquidity score | Label | Illiquid | Days scored | Days illiquid |
|---|---|---|---|---|---|---|---|---|---|
| azuki | 55 | 525 | 29.6 | 307.4 | 12.60 | Low | False | 701 | 0 |
| boredapeyachtclub | 96 | 347 | 661.6 | 2227.2 | 38.30 | Medium | False | 701 | 0 |
| doodles-official | 39 | 357 | 12.4 | 96.8 | 3.64 | Low | False | 701 | 0 |
| lilpudgys | 234 | 1359 | 49.3 | 318.8 | 40.13 | Medium | False | 701 | 0 |
| milady | 50 | 352 | 35.4 | 274.8 | 6.83 | Low | False | 701 | 0 |
| mutant-ape-yacht-club | 125 | 810 | 117.6 | 746.8 | 34.20 | Medium | False | 701 | 0 |
| pudgypenguins | 68 | 756 | 153.2 | 1968.6 | 34.75 | Medium | False | 701 | 0 |

## 3. Tests and snapshot hash check

- `python -m pytest ml -q` (.venv-train): **331 passed** (302 before Phase 10 code; 29 NFT tests).
  - Tests cover: no duplicate days, no future dates, gaps reported, `floor_usd == floor_eth x ETH-USD of that date`, the as-of rule never using a later point, all three wash rules and their order, liquidity windows ending at 00:00, the spike guard looking at past days only, the snapshot written once with a changed file refused, and the refresh refusing the snapshot directory and older floor data.
- Backend: `docker exec altinvest-backend ... pytest tests -q`: **20 passed** (unchanged; nothing in backend/ changed yet).
- Snapshot: `python -m ml.nft.snapshot --verify`: OK. The manifest sha256 is in the header line above.
- Crypto evaluation snapshot untouched (no write path to ml/data/raw).

## 4. Rule breaks, findings and open questions

**Rule breaks:** none.

**Findings and judgement calls:**

- **Manifest `git_dirty: true`** (commit 262dfe9) is a false positive. The manifest read the git state after the parquet files were written, so only the snapshot's own new files were uncommitted. The snapshot is not rewritten (rule 4); the order is fixed for any future snapshot (b9a56e6).
- **OpenSea USD cross-check (D55):** 70-81 days per collection are more than 5% away from OpenSea's own `usd_price` (median 1%).
  - Cause (`logs/10.2_usd_check_diagnostic.log`): OpenSea converts at the time of the point, up to 48 h before midnight. 433 of the 526 rows over 5% fall within 5% against the ETH price on the point's own date.
  - Our `floor_usd` follows D55 (ETH price at 00:00 of the date) and is exact by construction. D55 is not changed.
- **Gaps (floor point older than 48 h):** 0-3 days per collection; the dates are listed above. floor_eth is null on those days. The as-of floor (D63) fills them for modelling.
- **D66 spike guard** holds back 0-6 days per collection, all listed with their values in D66 (pre-test dates only). I also have to report this: an earlier dry run printed the full-series maximum one-day move per collection, which includes the sealed period. No metric was computed on test rows.
- The snapshot includes the partial UTC day 2026-11-10 for sales (collected about 16:00 UTC). Liquidity for a date uses only sales before 00:00 of that date, so it is unaffected. Fair value (10.6) stops 7 days before the sealed test.
- Every collection is liquid on every scored day (0 illiquid days at N = 10). The `Illiquid` path is tested with fixtures only.
- Item-level parquet files (about 25 MB) are not in git (D64); their hashes are in the tracked manifest. Re-running 10.5 or 10.6 from a fresh clone needs the backfill re-run, and the hashes will then differ.

**Open questions:**
1. Should pass-through rows (several sale events in one transaction for one token) be collapsed to one sale?
2. Should D66's factor 2.0 stand (see the D66 examples)?
3. Should D63 (as-of floor) stand?

Continuing to 10.3 (autonomous mode).
