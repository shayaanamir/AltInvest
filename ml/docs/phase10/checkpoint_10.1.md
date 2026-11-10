# Checkpoint 10.1: Decisions

Date: 2026-11-10. Branch: `phase-10-nft`. Inputs: checkpoint 10.0 with its A1 addendum, and planner amendments A1-A10.

## 1. What ran and what changed

- **A1** (first action): 8 OpenSea `floor_prices` calls plus a few probe calls (events, `one_day`, Alchemy). Results were added to `checkpoint_10.0.md` (commit 59c80da).
- **10.1 changes:**
  - `ml/docs/DECISIONS.md`: D53-D62 appended.
  - `ml/AGENTS.md` line 3 amended to allow NFT outputs (D53, A8).
  - `ml/docs/PLAN.md`: Phase 10 row added.
  - `ml/docs/STATUS.md`: Phase 10 section added.
  - This file.
- No code, collectors, tables or models. No backend/ or db/ edits (D61 is a proposal).
- The working tree also has the user's own `.env.example` edit (DUNE_API_KEY removed). It is left uncommitted on purpose; it is the user's change.

## 2. D-entries (full text in DECISIONS.md)

| D | Topic | Key points |
|---|---|---|
| D53 | Scope, AGENTS.md (A8) | ML may serve NFT outputs under `/nft/...`; AAI stays with the backend. |
| D54 | Collections, sources (A2, A7) | The 7 slugs, with CloneX as reserve. OpenSea for floor, sales and stats; Alchemy for traits; Binance ETH-USD. CoinGecko, GoldRush, Alchemy sales, Moralis, Reservoir and Dune are not used. |
| D55 | Daily floor (A3, A4) | Modelling value is the OpenSea floor **as of 00:00 UTC** (at most 48 h old, else null), identical for backfill and live. USD = ETH floor × Binance ETH open of that day. The intraday median is a display-only column. `floor_source` column; the A3 proxy is defined but not needed (786 days everywhere). |
| D56 | Sales, marketplaces (A6, A10) | OpenSea sale events from 2024-11-10. ETH, WETH and BETH payments. Marketplace is derived: Seaport = opensea, BETH = blur, otherwise unknown. Label example: "Sales on OpenSea and Blur, as reported by OpenSea". |
| D57 | Wash filter (A5) | R1 buyer == seller; R2 30-day round trip on the same token; R3 price below 0.1× or above 20× the floor of the sale date. Rule 4 is dropped (no Dune). Removal counts per rule. Limitations recorded. |
| D58 | Liquidity | Illiquid if sales_7d < **N = 10**. Score = 100 × mean pooled percentile of 7d and 30d sales and USD volume. High, Medium and Low labels. |
| D59 | Risk | D24 target on floor_eth. EWMA 0.94 and GARCH(1,1), 1 config each; persistence baseline; QLIKE. 70/15/15 split with 30-day embargo; `NFT_MIN_TRAIN_ROWS = 180`. D44 approval; served for all collections or none. **Separate NFT percentile pool** for risk_score. |
| D60 | Fair value | Premium-over-floor target, features, the two baselines, and 3 candidate families of at most 4 configs each. Monthly walk-forward from 2025-05, ending 7 days before the sealed test. MdAPE primary. Coverage rule 75-85% with each tail at most 15%. Jaccard comparable sales. |
| D61 | API and tables (A9), **for Person B** | New ML endpoints `/nft/collections`, `/nft/{slug}/floor`, `/nft/{slug}/risk`, `/nft/{slug}/sales`, pulled by the backend at 00:15 into the **existing** `nft_*` tables (field mapping listed). Seed clean-up and an idempotent re-run. |
| D62 | Snapshots | Parquet snapshot with a sha256 manifest under `ml/data/nft/snapshots/<date>/`; D40 guard; keys and raw responses never committed. |

## 3. Tests and snapshot hash check

- `python -m pytest ml` (.venv-train): **302 passed**. Only docs changed.
- No snapshots exist yet.

## 4. Rule breaks and open questions

**Rule breaks:** none.

**Open questions:**

- **Q1 (D59 pool):** should the NFT risk_score use a separate NFT-only percentile pool (proposed), or join the crypto D36 pool? Joining would put every NFT near "riskiest", but would make scores comparable inside mixed portfolios.
- **Q2 (power):** the risk sealed test covers about 118 days per collection at h = 30, so about 4 independent windows. Walk-forward has about 15 folds per collection. Expect wide CIs, so "no model won" is likely for risk unless pooling across collections carries it (D59 serves all or none).
- **Q3 (Person B):** D61 needs Person B's written OK before any backend/ or db/ code. Removing the fictional collections also touches `db/seed_data/nftCollections.json` and `db/seed_user_data.py` (2 references, demo holdings and watchlists), so demo users will lose those NFT holdings.
- **Q4:** ml/data/raw/eth_1d.csv in the working copy ends 2026-10-17 (the ml-refresh container holds the current copy). 10.2 will read ETH-USD from the refreshed serving data, so USD values for the last weeks are not missing.

Stop: waiting for OK on 10.1 before starting 10.2.
