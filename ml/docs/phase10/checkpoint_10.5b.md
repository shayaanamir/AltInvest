# Checkpoint 10.5b: Review fixes

Date: 2026-11-11. Branch `phase-10-nft`. User review of checkpoint 10.5. 10.6 was not started.

**Headline:** the D72 sales check, a rule fixed by the user before it was run, **withdrew the 10.3 EWMA approval**.
- NFT risk now serves persistence vol_30d of the raw floor, and the cone uses it (D73).
- D66 is withdrawn.
- The D66 causality test passed, so the withdrawal comes from the sale-price evidence, not from look-ahead.

## 1. Database safety (D69)

**Which database the backend used** (`logs/10.5b_db_host.log`; host only):
- The backend container's environment, the live uvicorn process (`/proc/1/environ`) and a real client connection all report `mongodb:27017`, database `aaip_db`. That is the local compose container.
- `db/mongo_connection.py` loads only `backend/.env`, which does not exist. The root `.env`, which holds the Atlas URI, is not mounted into the container.

**Confirmed local only:**
- The a9edff3 NFT pull ran only in the backend process started at 2026-11-10T20:14:06Z, created by `docker restart` (same container environment). The previous process predates that code; uvicorn has no reload.
- The 7351e3c seed ran by `docker exec` in the same container.
- No host-side Python imported `db` (the ML venv has no pymongo).
- The pull's rows are in the local container: 2,800 `ml-service` market rows.

**Fix (backend commit 68c1df7):**
- `docker-compose.yml`: the backend's `MONGO_URI` / `MONGO_DB_NAME` now come from `BACKEND_MONGO_URI` / `BACKEND_MONGO_DB_NAME`, defaulting to `mongodb://mongodb:27017` / `aaip_db`. With the current `.env`, which still holds the Atlas URI, `docker compose config backend` resolves to `mongodb://mongodb:27017` (`logs/10.5b_compose_resolved.log`).
- `db/seed_guard.py` is called by every `db/seed*.py` entry point and by `seed_all.run`. It refuses any host other than localhost, 127.0.0.1, ::1 or `mongodb`, and every `mongodb+srv` URI, unless `--allow-remote` is given. Messages show hosts only.
- Live check: a seed run with an Atlas-style URI exits 1 with "refusing to seed a non-local MongoDB".
- Tests: `backend/tests/test_seed_guard.py`. Local targets pass; remote ones are refused without credentials in the message; the flag allows them; `seed_all` and every seed `__main__` call the guard; compose defaults to local. The compose-file test is skipped inside the backend container because the file is not mounted there; the `docker compose config` check above covers it.

## 2. D66 causality

`ml/tests/test_nft_guard_causal.py`, **29 passed**. For every t, `guard_spikes(series[:t+1])[t] == guard_spikes(series)[t]` on:
- all 7 real collections, where it also matches the snapshot's stored `floor_eth_model` and `floor_spike`;
- 20 synthetic series with spikes and level shifts;
- edge cases.

`daily_floor` rows also never change when later points arrive. **The guard is strictly causal, so the 10.3 run is not void and was not re-run.**

**The earlier test fix, original vs corrected.** The original test existed only in the earlier session's working tree and was never committed; 262dfe9 committed the corrected version. From the session record:

```diff
-    # 1.0 is held (dip, back at 3.05); 1.4 is within 2x of 2.9; 2.3 is over 2x of 1.1 and of nothing before it,
-    # held; 0.3 and 0.1 disagree with the accepted 1.1 and with the day before, held; 0.11 confirms 0.1
-    assert model.tolist() == [3.0, 3.1, 3.1, 3.05, 2.9, 1.4, 1.0, 1.1, 1.1, 1.1, 1.1, 0.11]
-    assert held.tolist() == [False, False, True, False, False, False, False, False, True, True, True, False]
+    # day 2: 1.0 / 3.1 = 0.32, held (a dip; back at 3.05 the next day). day 5: 1.4 / 2.9 = 0.483 is outside the
+    # 2x band and equal to the ratio to the day before, so held. day 6: 1.0 / 1.4 = 0.71 confirms the new level,
+    # accepted. day 8: 2.3 / 1.1 = 2.09, held. days 9-10: 0.3 and 0.1 disagree with 1.1 and with the day before,
+    # held. day 11: 0.11 / 0.1 = 1.1 confirms, accepted.
+    assert model.tolist() == [3.0, 3.1, 3.1, 3.05, 2.9, 2.9, 1.0, 1.1, 1.1, 1.1, 1.1, 0.11]
+    assert held.tolist() == [False, False, True, False, False, True, False, False, True, True, True, False]
```

Only day 5 changed (1.4 -> 2.9, held). The original comment's claim "1.4 is within 2x of 2.9" was false.

## 3. D66 sales check (D72; rule committed in 20136fc before it was run)

Development dates only (before 2026-01-25). Clean sales follow D70. Generated from `ml/reports/nft/item_data_v2.json`:

git 0bb7af7 dirty False | evidence days 10, supporting raw 4, share 0.4, withdrawn True, D66 stands False

| Collection | Guarded days (dev) | No evidence | Supports raw | Supports guarded |
|---|---|---|---|---|
| azuki | 3 | 0 | 1 | 2 |
| doodles-official | 2 | 0 | 2 | 0 |
| lilpudgys | 5 | 0 | 1 | 4 |
| mutant-ape-yacht-club | 1 | 1 | 0 | 0 |
| boredapeyachtclub | 0 | 0 | 0 | 0 |
| milady | 0 | 0 | 0 | 0 |
| pudgypenguins | 0 | 0 | 0 | 0 |

| Collection | Date | Raw floor | Guarded floor | Clean sales that day | p_min | Verdict |
|---|---|---|---|---|---|---|
| azuki | 2025-01-24 | 4.7000 | 10.0000 | 465 | 3.5 | supports raw |
| azuki | 2025-02-15 | 1.0000 | 3.1197 | 134 | 3.02 | supports guarded |
| azuki | 2025-12-30 | 0.1138 | 0.6120 | 17 | 0.584 | supports guarded |
| doodles-official | 2024-12-21 | 0.7777 | 4.2915 | 73 | 1.0 | supports raw |
| doodles-official | 2025-05-10 | 0.9500 | 3.2900 | 195 | 1.36 | supports raw |
| lilpudgys | 2024-12-18 | 1.4800 | 3.2000 | 793 | 1.6 | supports raw |
| lilpudgys | 2025-01-04 | 0.4829 | 2.4540 | 95 | 2.37 | supports guarded |
| lilpudgys | 2025-01-29 | 0.2670 | 1.3540 | 442 | 1.03 | supports guarded |
| lilpudgys | 2025-02-15 | 0.1299 | 1.0790 | 414 | 1.04 | supports guarded |
| lilpudgys | 2025-07-19 | 0.3800 | 1.5000 | 108 | 1.43 | supports guarded |
| mutant-ape-yacht-club | 2024-11-06 | 0.2898 | 1.7398 | 0 |  | no evidence |

**Result: 10 evidence days, 4 of them support the raw floor (40% > 1/3).**
- **The EWMA approval is withdrawn.** Persistence is served for NFT risk, and the cone uses it (D73).
- One guarded day falls after the development cut (lilpudgys 2026-03-11, sealed period) and was not looked at.
- Note: p_min uses one sale, so a single cheap sale decides a day (doodles 2024-12-21: one sale at 1.0 against a guarded floor of 4.29). The rule was fixed beforehand and was applied as written.

**Applied (90ed452, after D73 in 526e75c):**
- `config.NFT_RISK_VOL_COLUMN = "vol_30d"`, `NFT_MODEL_FLOOR_COLUMN = "floor_eth_asof"`, `MODEL_VERSION_NFT_RISK = "nft-persistence-pooled-pct"`.
- The served note says no model is served (D72, D73).
- The liquidity rule R3 uses the raw floor.
- The ML services were rebuilt and the backend re-pulled: all 7 collections stored. Example: pudgypenguins volatility 0.829304, risk_score 37.719962.

## 4. 10.3 reporting

Generated from walkforward_risk.json (`logs/10.5b_risk_rank_confirm.md`):

10.3 report: commit 4ee833d, floor column floor_eth_model; target: fwd_vol_30d of the daily floor log returns in ETH (floor_eth_model; D59, D63, D66)

| Model | Config | Ranking (first 60% of folds): model QLIKE | Ranking: persistence QLIKE | Ranking rows | Confirmation (last 40%): model QLIKE | Confirmation: persistence QLIKE | Confirmation diff [95% CI] | Confirmation rows / dates | Approved in 10.3 |
|---|---|---|---|---|---|---|---|---|---|
| ewma | ewma | 0.5640 | 0.7522 | 1680 | 0.6929 | 0.9333 | 0.2404 [0.0668, 0.5855] | 1127 / 161 | True |
| garch | garch_normal | 0.5158 | 0.7522 | 1680 | 0.8073 | 0.9333 | 0.1260 [-0.5088, 1.2341] | 1127 / 161 | False |

Sensitivity, unguarded floor_eth_asof (reported only): ewma diff -0.6750 [-2.6697, 0.6325], approved False; garch diff 6.6547 [0.1597, 18.8548], approved False

- **The risk target is in ETH:** forward 30-day realised volatility of daily log returns of the ETH floor (D59), not USD.
- GARCH had the lower QLIKE on the ranking folds (0.5158 vs EWMA 0.5640). Each model type has a single config, so ranking selected nothing between configs, and GARCH failed confirmation.
- **D65 amended:**
  - the approval depended on D66;
  - power is about 5.4 independent windows (161 confirmation dates / 30);
  - **declared now:** one re-evaluation with the same candidates and rule once the floor history reaches 2027-05-10. It runs on the raw floor (`python -m ml.evaluation.run_nft_risk --floor-column floor_eth_asof` on a new snapshot), with a cumulative trial count of 4.

## 5. D63 / D67

Gaps, development dates only (from `item_data_v2.json`; table in section 6):
- Forward-filled days (no new floor point in the 24 h before midnight) are 0-5 per collection.
- The longest point gap is 5.74 days (mutant-ape-yacht-club) and 4.40 days (pudgypenguins), which is **over 3 days**.
- Sale-to-floor joins: 224 MAYC and 93 Pudgy sales use a floor point more than 3 days old.

So **a "Floor stale" indicator was added** (D67h):
- Floor rows now carry `floor_age_hours`: ML (CONTRACT_NFT, 90ed452), backend fd146bb, frontend 5f4c74c.
- The page shows the badge when the newest OpenSea point is more than 3 days old, or the newest floor is missing. It also counts the days in the shown range whose floor point was more than 3 days old.
- It is not visible in today's screenshots, because no collection's current point is that old. The logic is tested in `nftCone.test.js`.

**USD cone removed (D67 revised):**
- The USD view shows the USD history only (main chart layers: `history`).
- A separate "Next 30 days, in ETH" chart shows the last 30 ETH floors plus the cone, with the caption "This range is in ETH. ETH price moves are not included."

**Screenshots** (`ml/docs/phase10/screenshots/10.5b_*`, facts read from the DOM in `10.5b_screenshot_facts.json`):
- `10.5b_collection_desktop_dark.png` and `10.5b_collection_desktop_light.png`: ETH view, cone from persistence, "Last floor, 10 Nov".
- `10.5b_collection_desktop_light_usd.png`: USD history plus the ETH-only cone.
- `10.5b_collection_phone_dark.png`: 390 px, no horizontal scroll.
- `10.5b_btc_asset_desktop_dark_regression.png`: crypto cone unchanged.

## 6. Item data (D70, written in 20136fc before it was applied)

**New frozen item snapshot `2026-11-10-items-v2`** (5110e8d; manifest `git_dirty: false`).
- It holds `sales.parquet`: the rows after C1-C3, with `floor_point_eth`, `floor_point_age_hours`, `wash_flag`, `clean` and `sale_type`.
- It also holds `traits.parquet` with an `id_like` column, and `tokens.parquet` with rarity recomputed over known traits, ID-like categories excluded.
- **The floor join was same-day** (the D55 as-of value at 00:00 of the sale date) and is fixed: the floor is now the last floor point strictly before the sale. The "Floor changed" table shows how many development sales changed floor.

Generated from `item_data_v2.json` (`logs/10.5b_tables.md`):

| Collection | Before | C1 pass-through rows collapsed | C1 ambiguous dropped | C2 bundle rows dropped | C3 < 1% floor dropped | W1 flagged | W2 flagged | Clean (all dates) |
|---|---|---|---|---|---|---|---|---|
| azuki | 23736 | 21 | 6 | 977 | 3 | 16 | 1394 | 21319 |
| boredapeyachtclub | 9620 | 46 | 8 | 95 | 0 | 9 | 425 | 9037 |
| doodles-official | 27641 | 61 | 14 | 1135 | 11 | 12 | 1691 | 24717 |
| lilpudgys | 67319 | 89 | 17 | 3639 | 8 | 25 | 3823 | 59718 |
| milady | 18184 | 23 | 2 | 886 | 4 | 9 | 657 | 16603 |
| mutant-ape-yacht-club | 29268 | 79 | 18 | 742 | 4 | 10 | 2126 | 26289 |
| pudgypenguins | 22780 | 28 | 2 | 297 | 2 | 21 | 1332 | 21098 |

Sealed T 2026-02-01, embargo ['2026-01-25', '2026-02-01']
| Split | azuki | boredapeyachtclub | doodles-official | lilpudgys | milady | mutant-ape-yacht-club | pudgypenguins | all |
|---|---|---|---|---|---|---|---|---|
| dev | 17626 | 6108 | 20565 | 48049 | 13035 | 18306 | 15649 | 139338 |
| embargo | 93 | 94 | 139 | 490 | 138 | 269 | 248 | 1471 |
| sealed | 3600 | 2835 | 4013 | 11179 | 3430 | 7714 | 5201 | 37972 |

| Collection (dev) | Sales | Floor changed vs same-day as-of | vs same-day guarded |
|---|---|---|---|
| azuki | 18769 | 9562 | 10099 |
| boredapeyachtclub | 6388 | 3324 | 3324 |
| doodles-official | 22014 | 10921 | 10938 |
| lilpudgys | 50849 | 26537 | 27092 |
| milady | 13553 | 7125 | 7125 |
| mutant-ape-yacht-club | 19720 | 10014 | 10014 |
| pudgypenguins | 16509 | 8488 | 8488 |

| Collection (dev) | Days | Forward-filled days (no new point in 24 h) | Longest forward-filled run (days) | Longest point gap (days) | Days with point > 3 days old | Sales with floor point > 24 h | > 3 days | Max sale-to-point age (days) |
|---|---|---|---|---|---|---|---|---|
| azuki | 495 | 1 | 1 | 2.01 | 0 | 2746 | 0 | 1.99 |
| boredapeyachtclub | 495 | 1 | 1 | 2.09 | 0 | 980 | 0 | 1.91 |
| doodles-official | 495 | 0 | 0 | 1.97 | 0 | 3382 | 0 | 1.94 |
| lilpudgys | 495 | 2 | 1 | 2.55 | 0 | 7681 | 0 | 1.99 |
| milady | 495 | 0 | 0 | 1.99 | 0 | 2271 | 0 | 1.96 |
| mutant-ape-yacht-club | 495 | 5 | 4 | 5.74 | 2 | 3425 | 224 | 5.72 |
| pudgypenguins | 495 | 5 | 3 | 4.40 | 1 | 2899 | 93 | 4.34 |

sale_type (dev, clean, descriptive only): {'azuki': {'bid_accept': 10903, 'listing_fill': 6723}, 'boredapeyachtclub': {'bid_accept': 3450, 'listing_fill': 2658}, 'doodles-official': {'bid_accept': 11500, 'listing_fill': 9065}, 'lilpudgys': {'bid_accept': 25494, 'listing_fill': 22555}, 'milady': {'bid_accept': 8025, 'listing_fill': 5010}, 'mutant-ape-yacht-club': {'bid_accept': 9821, 'listing_fill': 8485}, 'pudgypenguins': {'bid_accept': 10216, 'listing_fill': 5433}}
ID-like: {'milady': ['Number']}

**The D68 check** (`ml/reports/nft/d68_check.json`): 200 tokens that Alchemy read with traits (random sample, seed 0) were read from OpenSea. All 200 answered: **0 tokens disagree, 0 differing trait entries.**
- The rerun's `git_dirty: true` is caused only by its own log file, which is tracked and was being written during the run.

**ID-like categories:** only milady "Number" (9,999 values).

**sale_type** is in `ml.nft.item_clean.NOT_FEATURES`, together with buyer, seller, tx, marketplace, payment_symbol, protocol_address, wash_flag and clean.

## 7. Sealed test (D71, rule committed before it was computed; counts added to D71)

**T = 2026-02-01**, computed by `ml.nft.item_data.sealed_cutoff` and fixed in `config.NFT_FV_SEALED_START`. Freezing refuses if the data gives another T.
- Embargo: 2026-01-25 to 2026-01-31, excluded from everything.
- Clean rows: development 139,338, embargo 1,471, sealed 37,972 (21.2% of 178,781). The per-collection counts are in the split table above and in D71.

**Enforcement:**
- `load_dev()` drops every date >= T - 7 days and asserts it.
- `load_sealed(step)` raises unless `step == "10.8"`.
- Tests: `test_nft_item_clean.py`, which runs `load_dev` on the real v2 files and checks the refusal.
- Every 10.5b statistic was computed on development dates only.

**Disclosure:** the 10.5 report (`item_data.json`) computed a repeat-sale share and monthly counts up to 2026-07-19, which includes 2026-02-01 to 2026-07-19, now sealed. Neither involves the premium.

## 8. Housekeeping

- `ml/data/nft/snapshots/CORRECTIONS.md` records:
  - the false `git_dirty` flag of the 2026-11-10 manifest (code at 262dfe9, files committed in b9a56e6);
  - the commits of all three snapshots;
  - that the guard columns are no longer used.
- **Commits touching backend/ or db/, all prefixed `backend:` (`logs/10.5b_backend_commits.log`):**
  - a9edff3: NFT pull
  - eca725c: detail route and dashboard count
  - 7351e3c: NFT seed and demo user
  - 68c1df7: seed guard and compose default
  - fd146bb: floor_age_hours
- e1dee9b, an ML commit, edited `docker-compose.yml` only to add the `ml-nft-refresh` sidecar (no backend/db file).
- The `*.log` files under `ml/docs/phase10/logs/` were gitignored and are now force-added. They were scanned for keys and credentialed URIs first: none found.

## 9. Tests and hashes

- ML `python -m pytest ml -q`: **383 passed**.
- Frontend `npm test`: **14 passed**.
- Backend (container): **38 passed, 1 skipped** (the compose-file test, see section 1).
- All three snapshots verify: `ml.nft.snapshot --verify`, `ml.nft.item_snapshot --verify`, `ml.nft.item_data --verify`.

## 10. Rule breaks and items for review

**Rule breaks:** none.

**Interpretations inside user-given rules (please review):**
1. **D70 C2:** "bundle" = one tx, one seller, one buyer, two or more tokens. 79% of the dev groups carry one repeated price, and many are BETH. These may be single-seller fills of a collection bid (real per-item prices) rather than bundles (`logs/10.5b_bundle_check.log`).
2. **D70 C1:** a pass-through group without exactly one final buyer is dropped.
3. **D70 W2:** every leg from X's sale to X's re-purchase is flagged.
4. **D70 sale_type:** sale_type is inferred from the payment token.
5. **D71:** T is pooled across collections and applies to fair value only; risk keeps the D59 split.
6. **D73:** with D66 withdrawn, serving and R3 use the raw floor, and the declared re-evaluation runs on the raw floor.

---

## HANDOFF FOR 10.6

**Snapshots** (frozen, never rewritten; see `ml/data/nft/snapshots/CORRECTIONS.md`). Manifests are tracked in git; the item parquet files are local only (D64) and are verified by hash on every load.

| Snapshot | Manifest sha256 | Files: rows, sha256 |
|---|---|---|
| base `2026-11-10` | `90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af` | floor 5,495 `4f0062e1e494feef6c8ad390f2c4e648eb596692166cea13d328355fb9488343`; floor_points 5,483 `9de584897f4b4fd1117c68f4555577d31b20e23cb56b1c4e6e5b7e8f56506622`; eth_usd 3,373 `0cf7bfa97fd450a04cba4ff17b64d50259ecf9a4e0b6e87fca00345f240f4962`; sales_raw 198,548 `70a751c76ad9be057d5360cee37e1a749a98b4d67314e97404231f23a4a9e0ed` |
| item v1 `2026-11-10-items` (D68) | `16a5c7568b8cfd4f32c0bd7b9d94d4d9a986f4994c116bd776b762a546cacb3d` | traits 618,970 `125d3b86d358747d137cc6d379ebbb4ede0a6dd6eaa18f1267a439b066fdd3ef`; tokens 90,395 `6404631e1342eed7ab2b076d7f5668766c4881abbd5e98b96d8fd749a9570d40` |
| **item v2 `2026-11-10-items-v2` (D70, use this)** | `bee1565c81ba3c7fb81597bb6bdf957092e64b8e58cc7d06ac03c2699965bdc4` | sales 190,331 `2df819414d061f0c25e603b8f55fc7f586c6bbeb25b82342789091dbf4e2f088`; traits 618,970 `ad79c7e31d4bc06f751fd0cbbaefb3bd0b81e16523a6185c534a63e292f6e81f`; tokens 90,395 `6619f738491b5923a61f4689810822e6b7e10819c8093534de5d69848bcbf546` |

**Loading them together:**
- `from ml.nft import item_data`.
- `item_data.load_dev()` returns `{sales, tokens, traits, not_model_features}`. It verifies the v2 hashes and the base `eth_usd` hash, keeps clean sales dated before T - 7, and adds `price_usd = price_eth x eth_usd` from the base snapshot.
- The floor for the premium is in each sale row: `floor_point_eth`, the last OpenSea point strictly before the sale, with `floor_point_age_hours`.
- Collection-level daily features (vol_30d, liquidity as of 00:00) come from `ml.nft.snapshot.load("floor")`, joined on (slug, sale date). They describe 00:00 of that date, so they are known before the sale.
- Use `floor_eth_asof`, never `floor_eth_model` (D73).

**Sealed cutoff:**
- T = **2026-02-01**; embargo 2026-01-25 to 2026-01-31.
- `item_data.load_sealed("10.8")` is the only route to rows dated on or after T.
- Development data ends 2026-01-24. Walk-forward months must lie inside it (D60's first test month, 2025-05, still fits).

**Cleaning rules (D70, already applied in v2), in this order:**
- C1: pass-throughs collapse to the final buyer's leg; ambiguous groups are dropped.
- C2: bundles (one tx, one seller, one buyer, two or more tokens) are dropped.
- C3: prices below 1% of the floor point (or with no point before the sale) are dropped.
- Then flags: W1 buyer == seller; W2 the token returns to a previous seller within 30 days (all legs flagged).
- `clean` = no flag. `load_dev` returns clean rows only; flagged rows stay out of training and evaluation.

**Excluded trait categories:** milady `Number` (`traits.id_like == True`). The v2 rarity already excludes it.

**sale_type policy:** descriptive only, never a model feature. Neither it nor any other column in `item_clean.NOT_FEATURES` may enter a model.

**Baselines as currently specified (D60, with D70's floor):**
- (a) floor: premium = 0, so fair value = `floor_point_eth`.
- (b) rarity heuristic: the median premium `log(price_eth / floor_point_eth)` of clean sales in the same rarity decile of the same collection over the 90 days before the sale date's 00:00 UTC; premium 0 if there are fewer than 5 such sales. Use the v2 rarity.

**Candidates, metrics and approval as in D60:**
- MdAPE is the primary metric.
- The range needs 75-85% coverage, with each tail at most 15%.
- The paired date-block CI uses blocks of 7 days.

**Open "AUTONOMOUS, needs review" items:**
- D63: as-of floor.
- D64: snapshot layout.
- D65: risk-run details, as amended.
- D66: withdrawn by D73.
- D67: API, dashboard count, cone and stale indicator, as revised.
- D68: item metadata fill.
- The 10.5b interpretations in section 10.

**Docker warning:**
- Restart the backend with `docker restart altinvest-backend`. Rebuild ML with `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh`.
- Since 68c1df7, compose gives the backend local Mongo by default even when `.env` holds the Atlas URI. Never set `BACKEND_MONGO_URI` or pass `--allow-remote` unless you mean to use the shared database.
