# Checkpoint 10.5c: Last data fixes before 10.6

Date: 2026-11-11. Branch `phase-10-nft`. 10.6 not started.

**Commits:**
- 4bc1db4: D65 amendment, D74, D75, written before running.
- bc81974: code.
- c8a6ff8: v3 snapshot.
- This commit: D75 counts and this checkpoint.

## 1. Ranking protocol

**D25, verbatim:**
> Model approval protocol (refines D22): candidate configs are declared in code before any run, max 4 per model type, and the count is recorded in the report. Folds are split chronologically: configs are ranked on the first 60% of folds; the top config is then confirmed on the last 40% with a paired block-bootstrap 95% CI of the difference in Spearman vs persistence. Approved only if the CI excludes 0 and the point estimate is positive. All configs' results are reported, not only the winner

D25's "Why" column: "Ranking and confirming on separate folds stops the winner being chosen and judged on the same data (user decision, 2026-10-19). Implementation: ranking uses pooled Spearman on the first floor(0.6 x n_folds) folds"

**D44, verbatim:**
> Phase 9 approval and serving rule (D25 applied to every part with its D43 primary metric). Configs are ranked on the first floor(0.6 x n_folds) folds by the pooled primary metric; the top config is confirmed on the last 40% with a paired moving-block bootstrap 95% CI (block = h) of baseline metric minus model metric (direction: log-loss gain over the prior, D31). Approved only if the CI excludes 0 and the point estimate is positive. No extra minimum-margin rule (power is already low, D29/D30). No plain Diebold-Mariano test (overlapping windows). Baseline to beat = the strongest baseline on the confirmation folds: price = last value; range = the baseline band (D42 a or b) with the lower interval score, AND overall coverage in [75%, 85%] AND each tail miss rate <= 15%, both on the confirmation folds; risk = the baseline with the lower QLIKE (h = 30: persistence vol_30d or EWMA; h = 7: persistence vol_7d, persistence vol_30d or EWMA). If no risk model is approved but EWMA beats persistence by the same paired-CI rule, serving EWMA needs a new D-number and is mapped through the D36 pooled percentile. Direction = prior (D31). SEALED TEST (step 9.6): used once, only on the chosen config per part, asset and horizon; never for tuning, early stopping, thresholds or selection. A part is served only if it is approved in walk-forward AND its test metric is not worse than its baseline's (point estimates on the test split; walk-forward already required the CI). A part that is not served keeps its baseline (D27, D33, D35). D33 stays in force for ETH unless the ETH logistic regression also passes 9.6 AND its D34 backtest beats always-HOLD and buy-and-hold after fees; changing D33 then needs a new D-number.

**Verdict: D25 and D44 support the planner's reading.** Both rank *configs* together on the first 60% of folds and confirm only "the top config"; neither ranks per model type.
- In 10.3, GARCH ranked first: QLIKE 0.5158, vs EWMA 0.5640 and persistence 0.7522.
- GARCH then failed confirmation: CI [-0.5088, 1.2341].
- **So 10.3 would have approved nothing, even before D66.**

**The conflict to know about:** 10.3 instead confirmed each model type, following the Phase 9 risk practice in D49:
> RISK (h = 30 and 7): candidates are EWMA (1 config) and GARCH(1,1) Student-t (1 config; parameters fitted on the fold's train returns, variance recursion through all returns up to t, D48); the baseline is persistence vol_30d at both horizons. LightGBM and Ridge/HAR risk candidates and the vol_7d / EWMA baselines are dropped. Approved if it beats persistence (paired CI of QLIKE); if both pass, the one with the lower confirmation QLIKE wins; served through the D36 p

D59 cited D44, not D49:
> Approval: D44 (rank on the first 60% of folds, confirm on the last 40% with a paired moving-block bootstrap 95% CI, block 30, of baseline QLIKE minus model QLIKE). EWMA or GARCH is served for ALL collections or NONE (as D50/D51): it needs a pooled CI that excludes 0 and, per collection, a point estimate not worse than p

**What changed:**
- D65 is amended (D65i) with the paragraph above.
- **The 2027-05-10 re-evaluation uses the D25/D44 reading** (`--protocol top-only`; `ml.evaluation.nft_approval.pooled_top_only`).
- Tests:
  - `test_top_only_protocol_ranks_all_candidates_together_and_confirms_only_the_top`
  - `test_top_only_on_the_10_3_report_approves_nothing`, which shows that on the 10.3 numbers the top-only protocol approves nothing.
- Serving is unchanged: persistence has been served since D73.

## 2. Bundle rule (D74, revises D70 C2)

- **The source has no bundle flag.** The OpenSea sale events carry only event_type, event_timestamp, transaction, chain, payment, closing_date, seller, buyer, quantity and nft, and raw responses were never stored (D62).
- So the check uses each transaction's actual payment, read once through the Alchemy Ethereum RPC for all **2,634** multi-token transactions. 0 were missing (2 retries recovered), and the result is frozen as `tx_payments.parquet`.
- **The rule:** a group is kept when the sum of all sale rows of the transaction in that token is at most 1.01 x what the transaction paid in that token (P):
  - ETH: the transaction's value;
  - WETH or BETH: that token's Transfer amounts in the receipt.
- **Probe before the rule** (24 groups, `logs/10.5c_bundle_probe.log`): every group was per-token priced.
  - ETH: the transaction value equals the rows' sum.
  - WETH: the rows' sum plus fees.
  - BETH: exactly 2x the rows' sum, because each Blur pool payment appears as two Transfer events.

| Collection | Multi-token groups (rows) | Per-token priced, KEPT: groups (rows) | True bundle / not attributable, DROPPED: groups (rows) | Payment not returned, DROPPED: groups (rows) | v2 C2 dropped rows |
|---|---|---|---|---|---|
| azuki | 376 (977) | 363 (937) | 13 (40) | 0 (0) | 977 |
| boredapeyachtclub | 39 (95) | 39 (95) | 0 (0) | 0 (0) | 95 |
| doodles-official | 465 (1135) | 455 (1112) | 10 (23) | 0 (0) | 1135 |
| lilpudgys | 1481 (3639) | 1440 (3544) | 41 (95) | 0 (0) | 3639 |
| milady | 316 (886) | 313 (880) | 3 (6) | 0 (0) | 886 |
| mutant-ape-yacht-club | 308 (742) | 297 (716) | 11 (26) | 0 (0) | 742 |
| pudgypenguins | 129 (297) | 124 (287) | 5 (10) | 0 (0) | 297 |
| **all** | 3114 (7771) | 3031 (7571) | 83 (200) | 0 (0) | 7771 |

**What the dropped groups are** (`logs/10.5c_dropped_examples.log`): most are "ETH" sales whose transaction value is 0, or below the rows' sum. The ETH moved inside contracts, so these are **not attributable** rather than proven bundles. A bundle that OpenSea itself split into per-row prices cannot be detected and is kept.

**Cleaning, all dates** (v3 against v2):

| Collection | Before | C1 collapsed | C1 ambiguous | C2 dropped (D74) | C3 < 1% floor | W1 | W2 | Clean, v3 | Clean, v2 |
|---|---|---|---|---|---|---|---|---|---|
| azuki | 23736 | 21 | 6 | 40 | 5 | 16 | 1500 | 22148 | 21319 |
| boredapeyachtclub | 9620 | 46 | 8 | 0 | 0 | 9 | 440 | 9117 | 9037 |
| doodles-official | 27641 | 61 | 14 | 23 | 11 | 12 | 1842 | 25678 | 24717 |
| lilpudgys | 67319 | 89 | 17 | 95 | 8 | 25 | 4122 | 62963 | 59718 |
| milady | 18184 | 23 | 2 | 6 | 4 | 9 | 781 | 17359 | 16603 |
| mutant-ape-yacht-club | 29268 | 79 | 18 | 26 | 4 | 10 | 2315 | 26816 | 26289 |
| pudgypenguins | 22780 | 28 | 2 | 10 | 2 | 21 | 1374 | 21343 | 21098 |

## 3. Currency (D75)

ETH, WETH and BETH are treated 1:1: `payment_currency = "ETH"` for all three. Sales paid in other tokens:

```
events dropped at parse by reason, up to the snapshot date: {'payment_token': 29}
other-currency sales per collection and token:
slug                   payment_symbol
azuki                  USDC               1
boredapeyachtclub      APE                4
                       USDC               5
lilpudgys              USDC               2
mutant-ape-yacht-club  APE                2
                       USDC               1
pudgypenguins          USDC              14
total other-currency sales: 29
base manifest dropped_events (same counts, frozen): {"azuki": {"payment_token": 1}, "boredapeyachtclub": {"payment_token": 9}, "lilpudgys": {"payment_token": 2}, "mutant-ape-yacht-club": {"payment_token": 3}, "pudgypenguins": {"payment_token": 14}}
payment symbols inside the frozen sales_raw: {'ETH': 86336, 'BETH': 67041, 'WETH': 45171}
frozen prices in the snapshot: eth_usd only (no rate for these tokens) -> stay dropped (D75)
```

- These 29 sales never entered the snapshot: they were dropped when parsed (D56).
- They cannot be converted with frozen prices, because the snapshot freezes only ETH-USD. **They stay dropped.**
- `payment_currency`, `marketplace`, `sale_type` and `payment_symbol` are in `ml.nft.item_clean.NOT_FEATURES`.

## 4. Item snapshot v3

- `2026-11-10-items-v3`, manifest sha256 `1d0c12d1643ad18dee4e3851ff3a48f9d938ab1223b38e56abb2fddbc6e67dfd`.
- Code bc81974, `git_dirty: false`.
- Files: sales.parquet 197,900 rows `f1972846b4cf42f2b80443a335e5624393abf13b9c44bda04da5f4bc05de6bc9`; traits.parquet 618,970 rows `ad79c7e31d4bc06f751fd0cbbaefb3bd0b81e16523a6185c534a63e292f6e81f`; tokens.parquet 90,395 rows `6619f738491b5923a61f4689810822e6b7e10819c8093534de5d69848bcbf546`; tx_payments.parquet 2,634 rows `4d9cc1d5946cbea00fc454ebe8adf4984e8b2a9e0b391c2e795f28d819b6c32d`.
- v2 is unchanged and still verifies.
- **T stays 2026-02-01, embargo 2026-01-25 to 2026-01-31; not recomputed.**

| Split | azuki | boredapeyachtclub | doodles-official | lilpudgys | milady | mutant-ape-yacht-club | pudgypenguins | all | v2 all |
|---|---|---|---|---|---|---|---|---|---|
| dev | 18333 | 6165 | 21362 | 50479 | 13620 | 18736 | 15829 | 144524 | 139338 |
| embargo | 99 | 94 | 143 | 505 | 138 | 272 | 251 | 1502 | 1471 |
| sealed | 3716 | 2858 | 4173 | 11979 | 3601 | 7808 | 5263 | 39398 | 37972 |

- Sealed share: **0.2125** (v2: 0.2124).
- ML tests: `python -m pytest ml -q` gives **391 passed**. That includes `load_dev()` on the real v3 files and `test_nft_item_v3.py`, which covers:
  - kept groups, true bundles and missing payments;
  - other collections in the same transaction;
  - the 1% tolerance;
  - payment_currency;
  - RPC parsing;
  - failed batches never being stored.
- Frontend and backend were unchanged in this step and were not re-run.
- `ml.nft.snapshot --verify`, `item_snapshot --verify` and `item_data --verify` (v2 and v3): OK.

## 5. Logs and secrets

Every committed or local file under `ml/docs/phase10`, `ml/reports/nft` and `ml/data/nft` was searched for `alchemy.com/v2/`, `x-api-key`, `api_key`, `mongodb+srv` and `Authorization`:

```
files scanned: 97
('ml/docs/phase10/checkpoint_10.0.md', 102, 'api_key', '- Env name: `OPENSEA_API_KEY`.')
('ml/docs/phase10/checkpoint_10.0.md', 105, 'api_key', '- Free key at https://dashboard.alchemy.com. Env name: `ALCHEMY_API_KEY`.')
('ml/docs/phase10/checkpoint_10.0.md', 108, 'api_key', '- Free key at https://dune.com/settings/api. Env name: `DUNE_API_KEY`.')
('ml/docs/phase10/checkpoint_10.0.md', 111, 'api_key', "4. **Paid fallback only if OpenSea's floor history is shorter than 365 days:** CoinGecko Analyst plan (paid). Env name: `COINGECKO_PRO_API_KEY`.")
('ml/docs/phase10/checkpoint_10.0.md', 145, 'api_key', '**Next step after your OK:** you provide `OPENSEA_API_KEY` (and optionally `ALCHEMY_API_KEY` and `DUNE_API_KEY`) in `.env`. I run the depth check (7 calls) and ')
('ml/docs/phase10/checkpoint_10.0.md', 151, 'api_key', '## Addendum A1 (2026-11-10): OpenSea floor-history depth, checked with OPENSEA_API_KEY')
('ml/docs/phase10/checkpoint_10.1.md', 15, 'api_key', "- The working tree also has the user's own `.env.example` edit (DUNE_API_KEY removed). It is left uncommitted on purpose; it is the user's change.")
('ml/docs/phase10/checkpoint_10.5b.md', 24, 'mongodb+srv', '- `db/seed_guard.py` is called by every `db/seed*.py` entry point and by `seed_all.run`. It refuses any host other than localhost, 127.0.0.1, ::1 or `mongodb`, ')
hits: 8
```

All hits are env-variable *names* or prose. The branch's full history (every added line) was also searched, including for the real key values from `.env`:

```
added lines in branch history: 10675
key VALUES found: {'CMC_API_KEY': 0, 'MONGO_URI': 0, 'OPENSEA_API_KEY': 0, 'ALCHEMY_API_KEY': 0}
'alchemy.com/v2/': 0 added lines mention it; lines with something value-like right after it: 0
'x-api-key': 2 added lines mention it; lines with something value-like right after it: 0
'api_key': 12 added lines mention it; lines with something value-like right after it: 0
'mongodb+srv': 6 added lines mention it; lines with something value-like right after it: 2
    ATLAS = "mongodb+srv<REDACTED>
    "mongodb+srv<REDACTED>
'Authorization': 0 added lines mention it; lines with something value-like right after it: 0
```

The two value-like `mongodb+srv` lines are fake URIs in `backend/tests/test_seed_guard.py` (`user:secret@cluster0.abcde...` and `mongodb+srv://localhost`). **Nothing to scrub; no history rewrite needed.**

The new RPC module never prints its URL. Its errors show only the HTTP status or the exception type.

---

## HANDOFF FOR 10.6 (updates the one in checkpoint_10.5b.md; everything there still holds unless changed here)

- **Use item snapshot v3:** `2026-11-10-items-v3`, manifest sha256 `1d0c12d1643ad18dee4e3851ff3a48f9d938ab1223b38e56abb2fddbc6e67dfd`. The base snapshot `2026-11-10` (manifest `90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af`) still provides `eth_usd` and `floor`.
- **Load with** `ml.nft.item_data.load_dev()`. It verifies v3 and the base `eth_usd`, returns clean sales dated before 2026-01-25 plus tokens and traits, and adds `price_usd`.
- `load_sealed("10.8")` is the only route to sealed rows (dated on or after T = 2026-02-01).
- **Floor = the raw OpenSea floor point strictly before the sale** (`floor_point_eth`, with `floor_point_age_hours`). Never use the same-day floor, and never the D66 guarded `floor_eth_model` (withdrawn, D73). Premium = `log(price_eth / floor_point_eth)`.
- **Ranking protocol (D25/D44 as written, D65i):** rank all candidates of all model types together on the first 60% of the walk-forward months; only the top-ranked candidate goes to confirmation on the last 40%, against the best baseline with the paired date-block 95% CI (block 7 days, D60).
- **Forbidden as features:** everything in `ml.nft.item_clean.NOT_FEATURES` (`sale_type`, `payment_currency`, `marketplace`, `payment_symbol`, `buyer`, `seller`, `tx`, `protocol_address`, `wash_flag`, `clean`), and every trait category with `traits.id_like == True` (milady `Number`).
- **Cleaning in v3:**
  - C1: pass-throughs collapse to the final buyer; ambiguous groups are dropped.
  - C2 (D74): multi-token groups are kept when the rows add up to what the transaction paid, otherwise dropped.
  - C3: prices below 1% of the floor point are dropped.
  - Flags: W1 buyer == seller; W2 the token returns to a previous seller within 30 days.
  - `load_dev` returns `clean` rows only.
- **Baselines (D60, with D70's floor):** (a) premium 0; (b) the 90-day same-rarity-decile median premium (0 if fewer than 5 sales), using the v3 rarity (ID-like categories excluded).
- Open "AUTONOMOUS, needs review" items and the Docker restart warning are as in checkpoint_10.5b.md.
