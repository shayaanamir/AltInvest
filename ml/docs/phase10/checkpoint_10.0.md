# Checkpoint 10.0: Investigation (read-only)

Date: 2026-11-10. Branch: `phase-10-nft` (from `main` at 206a20d). Plan: `ml/docs/PLAN_NFT.md`.
No code, collectors, tables or models were written. No paid API was called and no API key was used or created.

## 1. What ran and what changed

**Precondition.** `origin/main` already contains everything on `phase-9-vol-cone` (`git log origin/main..phase-9-vol-cone` is empty), so Phase 9 and the cone PR are merged.

**Commands (all read-only):**
- Repo search: `git grep -i nft` across backend/, frontend/, db/, ml/, plus reads of `backend/routes/nft.py`, `db/seed_nft.py`, `db/queries.py`, `db/indexes.py`, `backend/routes/dashboard.py` and `frontend/src`.
- Live DB: `mongosh` document count for every `nft_*` collection in the running `altinvest-mongo` container.
- Free, keyless HTTP calls:
  - OpenSea v2 `GET /collections/{slug}`, `/collections/{slug}/stats` and `/traits/{slug}` for 12 candidate collections.
  - OpenSea `/floor_prices`, `/events/collection` and `/chain/.../nfts/{id}` (all three returned 401 without a key).
  - CoinGecko `/nfts/{id}` (free) and `/nfts/{id}/market_chart` (refused: "limited to PRO API subscribers").
  - Alchemy `demo` key: `getNFTSales`, `getFloorPrice` and `getNFTMetadata`.
  - Covalent/GoldRush `nft_market/.../floor_price` (401), and `api.reservoir.tools` (does not resolve).
- Docs read: OpenSea OpenAPI pages for floor_prices, events and API keys; the CoinGecko market_chart page; Dune `nft.wash_trades`; the GoldRush `llms.txt` endpoint index; web searches for pricing and deprecations.
- Raw probe output is in the scratchpad only, not in the repo.

**Blocked action.** I tried to mint OpenSea's free 7-day instant key (`POST /api/v2/auth/keys`) to check how far back the floor history goes. Claude Code's auto-mode safety check denied it, so I created no key. As a result, floor-history depth is **unconfirmed** for every source (see section 4).

**Files and commits:**
- `85c9b2e` docs: Phase 10 NFT plan (`ml/docs/PLAN_NFT.md`, saved exactly as given).
- This file, `ml/docs/phase10/checkpoint_10.0.md`.

## 2. Findings

### 2.1 Existing NFT support

| Layer | What exists | State |
|---|---|---|
| db/ | `db/seed_nft.py` seeds 10 collections: `nft_collections`, `nft_market_data`, `nft_sales`, `nft_holder_stats`, `nft_liquidity`, `nft_risk_breakdown`, `nft_traits`, `nft_tokens`, `nft_token_sale_history`, `nft_token_ownership_history`. Indexes are in `db/indexes.py:59-68`. `db/seed_data/nftCollections.json` holds 5 collections. | The seed is **partly fictional** (Neon Drifters, Pixel Wardens, Genesis Punks, Astral Cats; only BAYC is real, with stale numbers: floor 14.2 ETH vs 5.82 today). It inserts rows again on every re-run (AUDIT G-50). |
| Live DB (`aaip_db`) | All 10 `nft_*` collections exist. | **0 documents in each.** This is why the dashboard shows "0 collections" and "0 NFT scores". |
| backend/ | `backend/routes/nft.py`: `GET /nft/collections` (sort and order), `GET /nft/collections/{slug}` (joins market, holders, liquidity, risk, traits, last 10 sales, AAI) and `GET /nft/collections/{slug}/tokens/{token_id}`. Schemas are `NFTCollectionListItem`, `NFTCollectionDetail` and `NFTTokenDetail` in `backend/models/schemas.py:339-395`. `dashboard.py` counts collections from `nft_market_data` and scores from `aai_scores` (category nft). | Works, returns `[]` today. No floor *history*, no volatility, no fair-value fields. AUDIT says nothing in the frontend calls `/nft/*`. |
| frontend/ | Dashboard `TrendingCollectionsSection`, Discover NFT tab, portfolio `NftHoldingsGrid` and `AddHoldingModal`, watchlists and alerts accept NFT slugs. | **No NFT collection or item page.** `AssetDetailPage.jsx:49` says "NFT collections don't have a detail page yet". NFT cards do nothing when clicked. |
| ml/ | Nothing. `ml/AGENTS.md:3` says ML "Produces ONLY `/predict/{asset}` and `/risk/{asset}`". | Phase 10 needs an AGENTS.md amendment (open question Q1). |

The ML side already has the daily ETH-USD price (Phase 1b data), which can convert ETH floors to USD and serve the plan's consistency test.

### 2.2 Data sources

| Source | Collection floor history | Volume / sales count | Item sales (price, time, buyer, seller, marketplace) | Item traits | Wash-trade flag | History depth | Free vs paid | Rate limits |
|---|---|---|---|---|---|---|---|---|
| **OpenSea API v2** | `GET /collections/{slug}/floor_prices?timeframe=…&resolution=N`, with timeframes up to `one_year` and `all_time`. Each point has time, token_unit (ETH) and usd_price. **Needs a key** (401 without one). | `/collections/{slug}/stats`: 1d, 7d and 30d volume and sales, plus lifetime totals. **Works keyless** (used for the table in 2.3). | `GET /events/collection/{slug}?event_type=sale&after=&before=`, paged. Gives price, time, buyer, seller and token. **Needs a key.** | `/traits/{slug}` gives category value counts (keyless, but intermittent: 4 of 11 slugs returned 401). Per-item traits come from `/chain/{c}/contract/{a}/nfts/{id}` (key). | **None** | Floor: `all_time` exists, but depth and per-day resolution are **unverified without a key**. Sales: back to 2021 per OpenSea (lifetime totals of 58k–168k sales). | Free. An instant key (no signup) lasts 7 days at about 600 reads/h. A full key from opensea.io/settings/developer has higher limits (exact numbers come back in the `X-RateLimit-*` headers). | Token bucket, shared per account. |
| **CoinGecko NFT** | `/nfts/{id}/market_chart?days=max` gives floor (native and USD), 24h volume and market cap. **Daily point at 00:00 UTC** for ranges over 14 days, 5-minute data for 1–14 days. | 24h volume (in market_chart); `one_day_sales` only in the current snapshot. | No | No | No | `days=max` is accepted. The real start date is unverified. | market_chart is **paid only (Analyst plan and above)**, confirmed: the keyless call returned error 10005. `/nfts/{id}` (current snapshot) is free. | Demo about 30/min (hit a 429 after 6 calls). |
| **GoldRush (Covalent)** | The old `nft_market/{addr}/floor_price`, `volume` and `sale_count` endpoints (daily, max 365 days) **are no longer in the GoldRush docs index**. Only wallet and ownership NFT endpoints are listed. Likely removed; a key would be needed to confirm. | Same | No | Wallet holdings only | No | At most 365 days, even when it existed | 14-day trial with 25k credits, then $10/mo (10k credits) or $250/mo | 4 RPS on the trial |
| **Alchemy NFT API** | `getFloorPrice` gives the **current value only** (OpenSea and LooksRare). No history. | No | `getNFTSales` is **deprecated**, confirmed: it returns "This API endpoint has been deprecated." (sunset 2026-09-30, no replacement). | **Yes.** `getNFTMetadata` and `getNFTsForContract` return `attributes` (confirmed with the demo key on BAYC #1). | No | n/a | Free key (monthly compute-unit allowance) | Compute units per call |
| **Dune** (not in the plan; the only source with wash flags) | Can be derived from trades only (no listing floor) | Yes, from `nft.trades` | `nft.trades`: every marketplace (OpenSea, Blur, …) since 2021, with buyer, seller, price in ETH and USD, and the project | No | **Yes.** `nft.wash_trades.is_wash_trade`, plus `filter_1_same_buyer_seller`, `filter_2_back_and_forth_trade`, `filter_3_bought_or_sold_3x`, `filter_4_first_funded_by_same_wallet` and `filter_5_flashloan` | Full on-chain history | Free plan: 2,500 credits/mo, but one report (July 2026) says **free is now view-only**, unverified. Analyst is $75/mo. Export costs 20 credits/MB on the free plan. | Credit-based |
| **Moralis** | `/nft/{address}/floor-price/historical` exists, but it does **not backfill**: history starts only when Moralis began tracking (as the plan notes). | — | — | — | — | Not usable for a 365-day backfill | Free key | — |
| **Reservoir** | **Shut down 2025-10-15.** DNS does not resolve. | — | — | — | — | — | — | — |

### 2.3 Proposed collections

Sales figures are from OpenSea `/stats` (keyless) on 2026-11-10. They show **one recent month**, not an average, and may count only sales OpenSea sees. All are ERC-721 on Ethereum.

| # | OpenSea slug | Floor (ETH) | Sales 7d | Sales 30d | Lifetime sales | Supply | Created | Trait categories (OpenSea `/traits`) | CoinGecko id | Floor history 365+ days? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | boredapeyachtclub | 5.82 | 78 | 298 | 58,079 | 9,996 | 2021-04 | 7 (Background, Clothes, Earring, Eyes, Fur, Hat, Mouth) | bored-ape-yacht-club ✓ | **Unconfirmed** (needs key) |
| 2 | mutant-ape-yacht-club | 0.80 | 121 | 727 | 136,535 | 19,571 | 2021-08 | 8 | mutant-ape-yacht-club ✓ | Unconfirmed |
| 3 | pudgypenguins | 2.20 | 63 | 408 | 93,557 | 8,888 | 2021-07 | 5 | pudgy-penguins ✓ | Unconfirmed |
| 4 | lilpudgys | 0.21 | 222 | 1,048 | 168,228 | 21,932 | 2021-12 | 9 | id not found yet ("lil-pudgys" 404) | Unconfirmed |
| 5 | azuki | 0.44 | 56 | 498 | 93,246 | 10,000 | 2022-01 | 12 | azuki ✓ | Unconfirmed |
| 6 | doodles-official | 0.23 | 44 | 356 | 88,038 | 9,998 | 2021-10 | 6 | doodles-official ✓ | Unconfirmed |
| 7 | milady | 0.66 | 55 | 345 | 72,157 | 9,976 | 2021-08 | Keyless call refused; needs a key | not checked (429) | Unconfirmed |

Every collection is more than 3.5 years old, so 365+ days of history exists in principle. No source has yet been *confirmed* to serve it (section 4).

**Rejected:**
- cryptopunks: 72 sales in 30 days, its own non-ERC-721 market and only 2 trait categories.
- degods-eth: 27 sales in 30 days.
- meebits: 82 sales in 30 days.
- proof-moonbirds: the keyless stats call was refused.
- clonex (348 sales in 30 days, traits not checked keyless): kept as the reserve if one of the 7 fails.

**7-day sales in the shortlist range from 44 to 222**, which gives a starting point for the illiquidity N in 10.1.

### 2.4 Backfill time and storage (estimates, not measured)

| Item | Volume | Calls | Time |
|---|---|---|---|
| Floor history | 7 collections × 1–2 calls | about 14 | under 1 minute |
| Item traits (Alchemy `getNFTsForContract`, 100 per page) | about 90,400 tokens | about 905 | about 10–20 minutes on a free key |
| Sales, last 24 months (about 3,700 per month in total) | about 89,000 sales | about 1,800 at 50 per page | about 3 hours at 600/h (instant key); under 1 hour on a full key |
| Sales, full lifetime | about 710,000 sales (sum of OpenSea lifetime totals) | about 14,200 | about 24 hours at 600/h; a few hours on a full key |

| Storage | Raw JSON | Parquet snapshot |
|---|---|---|
| Sales, lifetime (about 250 B per row) | about 180 MB | about 30–60 MB |
| Sales, 24 months | about 22 MB | about 4–8 MB |
| Traits (about 90k tokens × about 8 traits) | about 25 MB | about 3–5 MB |
| Daily floor (7 × about 1,800 days) | under 1 MB | under 1 MB |
| Mongo serving tables (latest values plus 365 days of floor) | — | under 5 MB |

The repo's parquet layout can hold this comfortably. The Dune export cost, if Dune is chosen: about 30–60 MB × 20 credits per MB, or 600–1,200 credits on the free plan (within 2,500 credits if free still allows API use).

### 2.5 Recommendation and keys to get

1. **OpenSea API v2: primary source** (floor history, sales events, traits, stats).
   - Get a **full API key** at https://opensea.io/settings/developer. It is free; a wallet sign-in may be required.
   - Env name: `OPENSEA_API_KEY`.
   - The first thing to run after your OK is one `floor_prices?timeframe=all_time` call per collection, to confirm 365+ days and the point spacing.
2. **Alchemy: item traits in bulk.**
   - Free key at https://dashboard.alchemy.com. Env name: `ALCHEMY_API_KEY`.
   - Optional: OpenSea can supply traits too, but needs about 90k per-item calls.
3. **Dune: wash-trade flags and sales from every marketplace.**
   - Free key at https://dune.com/settings/api. Env name: `DUNE_API_KEY`.
   - Please check at sign-up whether the free plan still allows API query execution. If it is now view-only, it is **paid (Analyst, $75/mo)**, and you decide whether that is worth it.
   - Without Dune, the 4th wash rule (source flags) does nothing and the sales data covers OpenSea only.
4. **Paid fallback only if OpenSea's floor history is shorter than 365 days:** CoinGecko Analyst plan (paid). Env name: `COINGECKO_PRO_API_KEY`.
5. **Not recommended:** GoldRush (NFT market endpoints appear removed; 365-day cap), Moralis (no backfill), Reservoir (shut down).

Rule 9: none of these keys exist in the repo. In 10.2, `.env.example` gets the names only.

## 3. Test results and snapshot hash check

No code and no snapshots in 10.0, so there is nothing to test or hash. The existing test suites were not run (nothing changed).

## 4. Rule breaks and open questions

**Rule breaks:** none. The blocked key-mint is described in section 1. No paid call was made, and no edits were made to backend/ or db/.

**Things that make parts of the plan unrealistic as written:**

1. **365+ days of floor history is unconfirmed for every source.** OpenSea `floor_prices` (free key) is the only free candidate, and its depth and resolution are unknown. CoinGecko is paid. GoldRush capped history at 365 days and now seems to have dropped the endpoint. Alchemy is current-only. Moralis does not backfill. If OpenSea falls short, 10.2 and 10.3 need either CoinGecko Analyst (paid) or a floor *derived from sales* (for example, the daily 10th percentile of sale prices). A derived floor would change the D-entry definition.
2. **"Daily median of the floor series" cannot apply to the backfill.**
   - CoinGecko history beyond 14 days is a single 00:00 UTC point per day.
   - OpenSea's per-day resolution is unknown.
   - The median can be computed only for days we collect live (intraday polling).
   - Proposal for 10.1: backfill = the source's daily value; live = the median of intraday polls; the switch date is recorded. Otherwise the volatility target mixes two definitions.
3. **Source wash-trade flags exist only in Dune**, and Dune's free API status is uncertain. OpenSea events have no flag. Rules 1–3 can still be applied to OpenSea sales ourselves.
4. **Alchemy can no longer supply sales** (`getNFTSales` is deprecated). The plan's Alchemy role shrinks to traits.
5. **Sales coverage.** OpenSea `/stats` and `/events` may not include Blur-only sales, so the counts above may understate liquidity. Only Dune `nft.trades` is marketplace-complete. This matters for the fair-value premium (10.6): a sale on Blur against an OpenSea listing floor.
6. **Thin data for item models.** About 300–1,000 sales per month per collection means monthly walk-forward test folds of a few hundred sales, before wash filtering. Per-collection LightGBM with trait one-hots (Azuki has about 450 trait values) risks overfitting. The pooled model and the rarity baseline are likely the realistic contenders, which matches the plan's "expected outcome".

**Open questions for the planner:**

- **Q1.** `ml/AGENTS.md:3` limits ML to `/predict` and `/risk`. Phase 10 adds NFT risk and fair value, so may AGENTS.md be amended in 10.1?
- **Q2.** The existing `/nft/*` backend schema (nft_market_data, nft_liquidity, nft_risk_breakdown and others) and the fictional seed collections. Should 10.1 propose reusing these tables (fill them with real data and drop the fictional seed rows), or new tables? Either way it is a db/ and backend/ change that needs Person B.
- **Q3.** If OpenSea's floor history is shorter than 365 days: pay for CoinGecko Analyst, or derive the floor from sales?
- **Q4.** Is Dune in scope (a new source not in the plan)? If its free API is gone, is $75/mo acceptable?
- **Q5.** Sales backfill window: full lifetime (about 710k sales, about 24 h on an instant key) or the last 24 months (about 89k, about 3 h)? 24 months is enough for monthly folds and avoids the 2021–22 bubble regime.

**Next step after your OK:** you provide `OPENSEA_API_KEY` (and optionally `ALCHEMY_API_KEY` and `DUNE_API_KEY`) in `.env`. I run the depth check (7 calls) and add the result to this checkpoint before 10.1.

STOP: waiting for OK.

---

## Addendum A1 (2026-11-10): OpenSea floor-history depth, checked with OPENSEA_API_KEY

**Commands.**
- `GET /api/v2/collections/{slug}/floor_prices?timeframe=all_time` for the 7 collections in A2 and the CloneX reserve. 8 calls, all HTTP 200.
- For BAYC also `resolution=100`, `resolution=5000`, `timeframe=one_year` and `timeframe=one_day`.
- One `GET /events/collection/boredapeyachtclub?event_type=sale` page each for the 2024-11-03..10 window and for the most recent sales.
- One Alchemy `getNFTsForContract` page for milady.
- Keys were read from `.env` (gitignored) and never printed or written anywhere. Raw responses are kept in the scratchpad, not the repo.

**Floor history.** Figures computed from the responses by a script, not hand-typed.

| Collection | Points | First | Last | Span (days) | Distinct days | Missing days | Median gap (h) | 3 largest gaps (h) | USD zero or null |
|---|---|---|---|---|---|---|---|---|---|
| boredapeyachtclub | 782 | 2024-09-16 | 2026-11-10 | 786 | 781 | 5 | 24.0 | 51, 55, 61 | 0 |
| mutant-ape-yacht-club | 781 | 2024-09-16 | 2026-11-10 | 786 | 781 | 5 | 24.0 | 48, 63, 138 | 0 |
| pudgypenguins | 782 | 2024-09-16 | 2026-11-10 | 786 | 781 | 5 | 24.2 | 48, 82, 106 | 0 |
| lilpudgys | 785 | 2024-09-16 | 2026-11-10 | 786 | 784 | 2 | 23.9 | 48, 48, 61 | 1 (2026-06-29) |
| azuki | 786 | 2024-09-16 | 2026-11-10 | 786 | 785 | 1 | 24.3 | 48, 48, 48 | 1 (2026-06-29) |
| doodles-official | 782 | 2024-09-16 | 2026-11-10 | 786 | 782 | 4 | 23.6 | 47, 54, 100 | 0 |
| milady | 786 | 2024-09-16 | 2026-11-10 | 786 | 786 | 0 | 24.0 | 48, 48, 48 | 0 |
| clonex (reserve) | 781 | 2024-09-16 | 2026-11-10 | 786 | 780 | 6 | 24.0 | 48, 48, 54 | 0 |

**What this shows:**
- **Every collection has 786 days (over 365) of OpenSea floor history.** The A3 sales-derived proxy is therefore not needed for any collection. The 24-month sales window (A6, from 2024-11-10) lies entirely inside the floor history.
- **The history starts on 2024-09-16 for all 8 collections**, so this is an OpenSea data cutoff, not each collection's start. `resolution=5000` returns the same 782 points as the default, so there is no finer history. `resolution=100` downsamples.
- **There is about one point per day, at an irregular time of day.** Only 14–21% of points fall between 23:00 and 01:59 UTC, so the A4 "value at 00:00 UTC" must be an as-of value (the last point at or before 00:00). 10.1 defines this.
- **`timeframe=one_day` returns intraday points**: 45 points over the last 24 h for BAYC, about one every 30 minutes. These are the source for the display-only intraday median (A4). They cannot be backfilled.
- **USD/ETH ratio check:**
  - The USD/ETH ratio implied by OpenSea's `usd_price` has a median of about 2,490–2,510 per collection, which matches ETH's price range.
  - Azuki and Lil Pudgys each have one point (2026-06-29) with `usd_price` = 0.
  - USD will be computed from our own ETH price, not OpenSea's `usd_price` (10.1).

**Rate limit.** The response headers show `x-ratelimit-limit: 120` with a reset about 30 s ahead, roughly 4 requests per second. This is far above the 600/h assumed in section 2.4. Revised backfill time:
- Sales, 24 months: about 1,800 pages of 50, or about 450 pages of 200 (the events `limit` maximum is 200), so **under 10 minutes**.
- Traits (Alchemy): about 905 pages, about 10–20 minutes.

**Sales events.** Fields: buyer, seller, event_timestamp, nft (identifier, contract and **traits**), payment (quantity, token, symbol), transaction, protocol_address and quantity.
- Payment symbols are **ETH, WETH and BETH**. BETH is Blur's pool token. In the 2024-11 BAYC sample, 27 of 50 sales were paid in BETH, with an empty `protocol_address`. In the recent sample, 39 of 50 used Seaport (`0x0000000000000068f116a894984e2db1123eb395`).
- **So OpenSea's sales feed includes Blur sales.** The Blur coverage gap from section 4 item 5 is smaller than feared. It is not proven complete: Blur sales paid in plain ETH or WETH with no protocol address cannot be told apart from other marketplaces, and there is no explicit marketplace field.
- 10.1 records the marketplace as derived from protocol address and payment token, and A10 labels follow that.

**Alchemy.** `getNFTsForContract` for milady returned 100 tokens per page, all 100 with `attributes`. Milady trait metadata is confirmed.

**Effect on section 2.3:** for all 7 collections, the "365+ days of floor history?" column is now **yes (786 days)**.
