# Checkpoint 10.7: Item card serving + 10.8 preparation

Date: 2026-11-14. Branch `phase-10-nft` (main untouched). No `load_sealed()` / `load_history()` call; no metric on any date on or after 2026-01-25.

**Headline:**
- The item card is live: an ETH estimate, no range, no drivers. The serving choice is a per-collection config value (model for 6 collections, B2 for lilpudgys).
- The served model is the dev-only fold-9 fit, and it reproduces the 10.6 predictions exactly.
- **The 10.8 protocol is committed as `2e6cacc`**, before any sealed access.
- Its dry run on the 10.6 confirmation months reproduces 10.6 row for row.

## 1. Commits (all pushed)
| Commit | What |
|---|---|
| `a5b33a7` | ML serving code (D78): config `NFT_FV_SERVE`, request-time features (`ml/nft/fv_serving.py`), artifact module, item endpoints, CONTRACT_NFT schemas, lightgbm in the serving image, artifact mounted read-only |
| `50c0ced` | Artifact metadata: `fv_pooled_l1_nl15` fitted at `a5b33a7`, `git_dirty` false, 137,040 clean dev rows from 2024-11-10 to 2025-12-24 |
| **`2e6cacc`** | **10.8 sealed-test protocol (D79)**: `ml/evaluation/run_nft_sealed_fv.py`, `item_data.load_history('10.8')`, protocol tests |
| `d574641` | Dry-run report `ml/reports/nft/sealed_fair_value_dry_run.json` (run at `2e6cacc`, `git_dirty` false) |
| `750b90c` | `backend:` item value pull, the item route and holdings estimates |
| `baa6fe6` | ML: item tables built under a lock and warmed at startup; live-loader test |
| `87adf68` | Frontend: item card and holding estimates |
| `7d471fb` | Screenshots, DOM facts, API logs and screenshot script; CSS fixes |
| this commit | D78 amendment, STATUS, WIP, this checkpoint |

**Two decisions you made during the step** (recorded in D78 as amended):
- **Live serving.** Request-time features use live data up to now. No error, metric or predicted-vs-actual comparison is computed on dates on or after 2026-01-25. The plan's live accuracy log stays **off** until after 10.8.
- **Rebuild.** You approved `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh`; the backend got only `docker restart`. `tx_payments.csv` and the two D68 fill files were copied into the ml-data volume with sha256 checked equal.

## 2. Serving summary (D78)
- **Serving rule:** `config.NFT_FV_SERVE`: `model` for azuki, boredapeyachtclub, doodles-official, milady, mutant-ape-yacht-club and pudgypenguins; `b2` for lilpudgys. Switching every collection to B2 is a config change only, tested by `test_item_values_follow_the_per_collection_serving_config`.
- **Estimate:** `estimated_value_eth` = the last OpenSea floor point before now × exp(predicted premium). It is ETH only and a point estimate only: no range for any collection and no drivers.
- **Served model:**
  - `nft-fv-pooled-l1-nl15-dev-2025-12-25`, the fold-9 fit, trained on dev data only.
  - Its predictions on the 10.6 fold-9 test rows equal the walk-forward's, tested to 1e-12.
  - It is refitted on all data only in 10.9.
  - `model.txt` stays local (gitignored); its sha256 is in the tracked `metadata.json` and is checked on load.
- **Request-time features** use the training code (`fv_features.build`) on the history as of t, plus a hypothetical sale at t. They are tested on dev dates against the full training pipeline:
  - **200 hypothetical (token, t) pairs**, including never-sold tokens;
  - **100 real sales** (features at the sale time equal that sale's training features);
  - prices after t never change a feature.
- **Live loader:** the live directory cut at 2026-01-25 rebuilds the training history **exactly**: 153,708 rows, identical frames.
- **Trait check:** live traits match the artifact's static-feature and trait hashes. On any mismatch, serving refuses with 503.
- **Never-sold tokens:** these get the training's missing-value handling and `no_prior_sale: true`, with a note.
- **Accuracy line:** `accuracy_note` comes from the artifact metadata ("Accuracy check pending"); 10.9 writes the sealed result there.
- **ML endpoints** (contract-validated):
  - `GET /nft/{slug}/items/{token_id}/value`;
  - `GET /nft/items/value?items=slug:id,...` (up to 50).
  - Live: unknown token → 404, malformed list → 422, lilpudgys → 200 via B2. A warm 2-item batch takes about 3 s (`logs/10.7_ml_item_values.log`).
- **Backend:**
  - The daily pull stores every NFT holding's estimate in `nft_item_values`. After the restart: `'NFT items': {'batch 1': 'stored 2'}`.
  - `GET /nft/collections/{slug}/items/{token_id}/value` makes one live call, stored on success. If ML fails, it returns the stored row with `stale: true`, otherwise 503.
  - `/portfolio/holdings` adds `estimated_value_eth` (display only; value and P&L are unchanged).
- **Serving image:** 917 MB (848 MB in 10.4; +69 MB for lightgbm and libgomp1).

## 3. Screenshots (`ml/docs/phase10/screenshots/`, live stack, demo user, headless Edge; facts in `10.7_screenshot_facts.json`)
- `10.7_item_card_desktop_dark.png`, `10.7_item_card_desktop_light.png`: pudgypenguins #7862, theme switched with the top-bar toggle.
- `10.7_item_card_phone_dark.png`: 390 px, sidebar collapsed, page scroll width 390 (no horizontal scroll).
- `10.7_item_card_azuki_desktop_dark.png`: azuki #8604, the second demo holding.
- `10.7_demo_holdings_desktop_dark.png`: both holdings with "Est. value … ETH" and "Typical error: Accuracy check pending".

**DOM checks** (from the facts file):
- the caption is present verbatim;
- the accuracy line is present;
- no range, driver, lower or upper wording;
- no `$` or USD on the card.

**Card contents:**

| Holding | Estimated value | Last floor | Last sale | Rarity rank |
|---|---|---|---|---|
| pudgypenguins #7862 | 2.394 ETH | 2.349 ETH (13 Nov 2026) | 4.320 ETH on 1 Jun 2026 | #1,712 of 8,888 |
| azuki #8604 | 0.513 ETH | 0.510 ETH | 0.840 ETH | #4,369 of 10,000 |

These are displayed values only; nothing compares them.

## 4. Tests
| Suite | Result |
|---|---|
| ML `python -m pytest ml -q` | 421 passed, 4 warnings (10:39). An earlier full run had 1 failure: `test_schemas_are_closed_and_separate_from_the_crypto_contract` expected only the 4 Phase 9 NFT schemas; its expected set now includes NftItemValueResponse and NftItemValuesResponse. |
| Backend (container) `python -m pytest tests -q` | **43 passed, 1 skipped** (the skip is the compose-file test, as before) |
| Frontend `npm test` | **20 passed** (6 new in `nftItemValue.test.js`); eslint clean on the changed files |

New ML tests:
- `test_nft_fv_serving.py` (8): feature equivalence, real-sale equivalence, after-t invariance, artifact = fold 9, config routing and the B2 switch, the no-prior-sale flag, endpoints, the live loader.
- `test_nft_sealed_protocol.py` (4): months and cutoffs, the loaders refusing outside 10.8, the served-configuration pass and fail rules, refusing a second sealed run.

## 5. 10.8 protocol (D79, commit `2e6cacc`, before any sealed access)
- **Window:** sales dated 2026-02-01 to 2026-11-10, one monthly expanding refit per month (10 months). For month M, training uses clean sales before start(M) − 7 days, with W2 cut at that cutoff.
- **Models:** `fv_pooled_l1_nl15` exactly as declared, plus B0/B1/B2 fitted the same way.
- **Features:** from `load_history('10.8')`, which holds all rows strictly before each sale, including earlier sealed sales. Test-row W2 uses sales up to 2026-11-10.
- **Evaluated:** the **served configuration** (model for 6 collections, B2 for lilpudgys).
- **Pass rule:** the paired 95% CI of MdAPE(best of B0/B1/B2) − MdAPE(served) must be above 0. Bootstrap: 7-day date blocks, 1,000 resamples, seed 0, pooled across collections.
- **Outcome:** PASS keeps the rule; FAIL means every collection serves B2. No range is served either way.
- **Descriptive only:** MdAPE by collection, rarity decile and month, plus B2's range coverage.
- **Run guards:** one invocation of `python -m ml.evaluation.run_nft_sealed_fv --sealed`. It refuses on a dirty tree or when its report already exists (tested), and writes `logs/10.8_sealed_run.log`.

## 6. Dry run (the exact script, `--dry-run`: dev data, mock window = the 10.6 confirmation months 2025-10-01 to 2026-01-24)
It runs end to end in 34 s. Monthly training cutoffs and rows: 2025-09-24 / 109,612; 2025-10-25 / 122,635; 2025-11-24 / 131,006; 2025-12-25 / 137,040.

| | served | fv_pooled_l1_nl15 | B0 | B1 | B2 |
|---|---|---|---|---|---|
| MdAPE (32,460 rows, 116 dates) | 0.0279 | 0.0284 | 0.0345 | 0.0372 | 0.0335 |

Best baseline B2. Paired diff B2 − served: **0.0055 [0.0042, 0.0063]**, so **PASS** on this window (about 16.6 blocks).

| collection | n | served | model | B0 | B1 | B2 |
|---|---|---|---|---|---|---|
| azuki | 3290 | 0.0323 | 0.0323 | 0.0388 | 0.0448 | 0.0410 |
| boredapeyachtclub | 1794 | 0.0278 | 0.0278 | 0.0325 | 0.0323 | 0.0321 |
| doodles-official | 3611 | 0.0314 | 0.0314 | 0.0432 | 0.0434 | 0.0436 |
| lilpudgys | 10878 | 0.0276 | 0.0291 | 0.0291 | 0.0364 | 0.0276 |
| milady | 4149 | 0.0291 | 0.0291 | 0.0391 | 0.0392 | 0.0392 |
| mutant-ape-yacht-club | 5044 | 0.0270 | 0.0270 | 0.0419 | 0.0365 | 0.0352 |
| pudgypenguins | 3694 | 0.0226 | 0.0226 | 0.0300 | 0.0280 | 0.0270 |

By month (served vs B2): 2025-10 0.0296 vs 0.0360; 2025-11 0.0249 vs 0.0293; 2025-12 0.0271 vs 0.0321; 2026-01 0.0293 vs 0.0348.

B2's 80% range coverage: 0.8699 (lower tail 0.0501, upper tail 0.0800). By rarity decile, the served configuration's MdAPE is below B0, B1 and B2 in all 10 deciles (full table in the JSON).

**Comparison with 10.6:**
- Every per-row prediction (model, B0, B1, B2) and every baseline range **equals** the 10.6 walk-forward rows: 32,460 of 32,460 rows, max difference 0.0. So the model and baseline MdAPEs are identical (0.0284, 0.0345, 0.0372, 0.0335).
- The only differences are expected, **not bugs**:
  1. **Served 0.0279 vs model-only 0.0284.** Lilpudgys uses B2 in the served configuration. The per-collection guard was chosen on these same months, so on this window the served number is **in-sample optimistic**; the sealed window has no such advantage.
  2. **The CI is narrower** than 10.6's [0.0015, 0.0079]. On lilpudgys, a third of the rows, the served prediction *is* B2, the baseline it is compared with, so those rows are identical on both sides.
- **No protocol change and no bug fix** after the dry run.

## 7. Open items
1. **New multi-token transactions after the snapshot have no payment record** in the live volume, so the request-time history drops them (D74 rule "no record → drop"). `ml.nft.tx_payments` is not run by the refresh sidecar. Adding it needs a decision, and the Alchemy RPC key in the sidecar.
2. **The live predicted-vs-actual log and its ALERT** (plan step 10.7) are off until after 10.8 (your decision). The monthly retrain job is also deferred: the served model stays the dev-only fit until 10.9.
3. **Two floors on screen.** The holdings card's "2.25 ETH" is the D55 daily floor at 00:00 UTC. The item card's "Last floor" is the latest OpenSea point before now (2.349), which is the floor the estimate uses. They can differ within a day.
4. **Startup refresh can't reach Binance.** Inside this Docker environment the ML container's startup crypto refresh can't reach `api.binance.com` (network unreachable), so it keeps the last good data (D40). This was the case before this step too.
5. **Pre-existing formatting:** the holdings card shows the floor unrounded ("0.469999 ETH"); I left it unchanged.
6. **10.8 must run with `config.NFT_FV_SERVE` exactly as committed.** The script records the `serve` map it evaluated.
7. **For review:**
   - the **AUTONOMOUS** items in D78: the subset rule, missing payments, trait hashes, the last-sale definition, the stale note and deployment;
   - the **AUTONOMOUS** items in D79: "best of B0/B1/B2" = lowest pooled MdAPE, and embargo rows inside later training cutoffs;
   - D76 and D77 from 10.6.

STOP. Waiting for review before 10.8.
