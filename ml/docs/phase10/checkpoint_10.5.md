# Checkpoint 10.5: Item-level data

Date: 2026-11-11. Branch `phase-10-nft`. Plan step 10.5; D56, D57, D64, D68 (AUTONOMOUS, needs review).

## 1. What ran and what changed

- The item sales and traits were collected in 10.2 and frozen in the base snapshot `2026-11-10` (D64: one snapshot for collection and item data). For each sale the snapshot has: token id, price in ETH, timestamp, marketplace, buyer, seller and tx.
- `price_usd` is computed when the data is loaded: price_eth x the frozen ETH-USD of the sale's UTC date (`item_summary.with_usd`, D68). It is not stored a second time.
- **Problem found:** 348 tokens had no traits and no name. These were failed Alchemy metadata reads. Under D60 they would have counted as 'none' in every category and looked very rare (a pudgypenguins token ranked 6th), and 1,118 kept sales are of such tokens.
- **Fix (D68, committed first as e8e6157):**
  - `python -m ml.nft.item_snapshot --fill` read the 348 tokens once from OpenSea `GET /chain/ethereum/contract/{contract}/nfts/{id}`. All 348 answered with traits (`logs/10.5_item_fill.log`).
  - `--freeze` wrote a **separate** frozen item snapshot, `ml/data/nft/snapshots/2026-11-10-items/`, containing `traits.parquet` and `tokens.parquet`. Rarity was recomputed over tokens with known traits only. The manifest records the parent manifest's sha256 and `git_dirty: false`. The base snapshot is unchanged.
- `python -m ml.nft.item_summary` wrote `ml/reports/nft/item_data.json`. It computes nothing about the premium (the 10.6 target).
- **Commits:**
  - e8e6157: D68
  - 9df9029: the code (`ml/nft/item_snapshot.py`, `ml/nft/item_summary.py`, `traits.rarity_all(known_only=)`, `opensea.Client.nft`, `snapshot.load(date=)`, `config.NFT_ITEM_SNAPSHOT`, `ml/tests/test_nft_items.py`)
  - 24dfefa: the item manifest
  - the checkpoint commit

## 2. Sales per collection before and after filtering (from item_data.json by a script, `logs/10.5_tables.md`)

report commit 24dfefa, git_dirty False; base manifest 90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af; item manifest 16a5c7568b8cfd4f32c0bd7b9d94d4d9a986f4994c116bd776b762a546cacb3d; sealed test from 2026-07-20

| Collection | Before filter | R1 | R2 | R3 | After filter | Date range (after) | USD volume after | Pre-test kept | Min month (pre-test) | Sealed-period kept | Repeat-sale share (pre-test) | Tokens | Supply | Traits missing | Categories | Values |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| azuki | 23736 | 28 | 391 | 21 | 23296 | 2024-11-10 to 2026-11-10 | 324,338,542 | 21834 | 293 | 1462 | 0.825 | 10000 | 10000 | 0 | 12 | 454 |
| boredapeyachtclub | 9620 | 41 | 156 | 6 | 9417 | 2024-11-10 to 2026-11-10 | 312,448,021 | 8399 | 112 | 1018 | 0.754 | 10000 | 9996 | 0 | 7 | 169 |
| doodles-official | 27641 | 43 | 529 | 29 | 27040 | 2024-11-10 to 2026-11-10 | 171,752,891 | 25219 | 240 | 1821 | 0.864 | 10000 | 9998 | 0 | 6 | 265 |
| lilpudgys | 67319 | 75 | 1445 | 14 | 65785 | 2024-11-10 to 2026-11-10 | 280,809,602 | 60860 | 410 | 4925 | 0.852 | 21935 | 21932 | 0 | 9 | 403 |
| milady | 18184 | 26 | 275 | 7 | 17876 | 2024-11-10 to 2026-11-10 | 147,246,855 | 16229 | 192 | 1647 | 0.786 | 10000 | 9976 | 0 | 16 | 10309 |
| mutant-ape-yacht-club | 29268 | 56 | 642 | 11 | 28559 | 2024-11-10 to 2026-11-10 | 151,176,814 | 25836 | 316 | 2723 | 0.826 | 19572 | 19571 | 0 | 8 | 348 |
| pudgypenguins | 22780 | 42 | 509 | 4 | 22225 | 2024-11-10 to 2026-11-10 | 755,928,733 | 19775 | 150 | 2450 | 0.835 | 8888 | 8888 | 0 | 5 | 173 |

Checks (all collections; each must be 0): {'duplicate_sales': 0, 'sales_without_floor_for_their_date': 0, 'sales_without_eth_usd_for_their_date': 0, 'sales_with_empty_buyer_or_seller': 0, 'sold_tokens_without_metadata': 0, 'sold_tokens_without_traits': 0, 'duplicate_trait_rows': 0} | all pass: True
Per-collection checks all 0: True

- Removal counts use the first matching rule, in the order R1 buyer == seller, R2 30-day round trip, R3 price below 0.1x or above 20x the floor (D57).
- The events dropped before parsing (other payment token, quantity not 1) are listed per collection in `item_data.json`: 0-14 per collection.
- "Min month (pre-test)" is the smallest monthly count of kept sales before the sealed test (2026-07-20). 10.6 test folds will have at least that many sales: 112 for BAYC, 150 for Pudgy Penguins.

## 3. Tests and snapshot hash check

- `python -m pytest ml -q`: **344 passed** (340 + 4 in `test_nft_items.py`):
  - known-only rarity does not rank unread metadata as rare;
  - OpenSea items parse like Alchemy metadata;
  - the merge only fills missing tokens and never replaces base rows;
  - every data check counts its problem and passes on clean data.
- The wash rules and their order are tested in `test_nft_data.py`, which is unchanged.
- The plan's 10.5 tests are run on the real snapshot data in `item_data.json` (`checks_all`), and every count is 0:
  - no duplicate sales
  - every sale has a floor and an ETH-USD price for its date
  - no empty buyer or seller
  - every sold token has metadata and traits
  - no duplicate trait rows
- Frontend `npm test`: 13 passed. Backend (container): 26 passed.
- Snapshots:
  - `python -m ml.nft.snapshot --verify`: OK. Base manifest sha256 `90e74e885eee75336e7a9b46bb9f718a4a9757802234fc197053901f3d27d7af`.
  - `python -m ml.nft.item_snapshot --verify`: OK. Item manifest sha256 `16a5c7568b8cfd4f32c0bd7b9d94d4d9a986f4994c116bd776b762a546cacb3d`; traits.parquet `125d3b86d358...`, tokens.parquet `6404631e1342...` (full hashes are in the manifest).
- The sealed test data has not been used for any metric: only data checks and one total count of the sealed period's kept sales.

## 4. Rule breaks, findings and open questions (for the 10.6 session)

**Rule breaks:** none.

**Findings:**
1. **milady "Number"** is the token's own number, with 9,999 distinct values. It is an identifier, not a trait.
   - It adds the same amount to every milady rarity score, so ranks are unaffected.
   - But it must not become trait one-hots. Recommendation for 10.6: drop any category whose values are unique per token, and declare that before the run.
2. **High-cardinality categories** elsewhere: lilpudgys Body has 132 values and azuki Hair has 123 (`logs/10.5_trait_cardinality.log`). Per-collection one-hots will be sparse (10.0 already noted the overfitting risk).
3. **Earlier sales are common:** 75-86% of pre-test kept sales have an earlier sale of the same token, so the "previous sale premium" feature will usually exist.
4. **Token counts vs supply:** BAYC 10,000 tokens vs reported supply 9,996, milady 10,000 vs 9,976, lilpudgys and MAYC +3 and +1. These are probably burned tokens that are still in the contract listing. Harmless for rarity (within 0.3%).
5. **Open since 10.2:** pass-through trades (one transaction, one token, two sale rows; 713 rows) are kept as separate sales. 10.6 may want one sale per transaction for the premium target.

**Open questions:**
- Accept D68.
- The 10.6 choices above (identifier categories, pass-through trades).

**STOP: 10.6 is for another session.**
