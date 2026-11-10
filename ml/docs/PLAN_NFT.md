PLAN_NFT — Phase 10: NFT collections, volatility cone and fair value

Planner: Claude (planning chat). Executor: the agent. The user relays
reports between the two. Every step ends at a CHECKPOINT: report and wait.
Precondition: Phase 9 and the volatility cone PR are merged into main.
Branch: phase-10-nft, from main.

GOAL
1. Collection pages: floor price history (ETH and USD) continuing into the
   same 30-day volatility cone as crypto (D52), with a liquidity badge.
2. Item pages: an estimated fair value for a single NFT, with a range,
   "X% above/below similar items", the main drivers, and similar recent
   sales.
3. A risk score and liquidity score per collection.
No floor price forecast line. "No model won" is a valid, reportable result.

FIXED RULES (on top of ml/AGENTS.md and the Phase 9 rules)
1. Reuse, don't copy: EWMA from ml.features.features.ewma_vol, the cone
   from frontend/src/utils/volCone.js, approval logic from approval.py.
2. Approval as D25: candidates and at most 4 configs per model type declared
   in code before any run; rank on the first 60% of walk-forward folds,
   confirm on the last 40% with a paired 95% CI that excludes 0.
3. The sealed test split is used ONCE (step 10.8), only on chosen configs.
4. All evaluation runs on frozen snapshots (D40 guard). Snapshot files never
   change after they are written; hashes recorded.
5. Every report records trial count, date ranges, git commit, n_effective.
6. No feature may use information from after the moment it describes
   (sale time or prediction date). Leakage tests for every new feature.
7. confidence stays null unless calibrated.
8. Do NOT edit backend/ or db/ without Person B's written OK. Propose
   exact API fields and tables first.
9. No API keys in the repo. Keys go in .env (gitignored) and .env.example
   lists the names only.
10. Two-attempt rule and time boxes as in Phase 9.

STEPS

10.0 Investigate (1 day, read-only) — CHECKPOINT
- What NFT support already exists in backend/, frontend/, db/, ml/
  (dashboard shows "0 collections", "0 NFT scores"). Any NFT pages,
  tables, endpoints, seed data?
- Data sources: compare CoinGecko NFT market_chart, OpenSea API v2
  (floor_prices, events/sales, collection traits), GoldRush/Covalent,
  and Alchemy NFT API. For each: what it provides (collection floor,
  volume, sales count, item sales with price and time, item traits,
  wash-trade flags), how far back history goes, free vs paid limits,
  rate limits. Moralis does not backfill history; note that.
- Propose 5-8 liquid collections. For each confirm: 365+ days of floor
  history, roughly how many item sales per month, trait metadata
  available.
- Estimate storage size and total backfill time.
Report: findings, recommended source(s), collections, and anything that
needs a paid key. Wait for OK.

10.1 Decisions (½ day) — CHECKPOINT
Write D-entries in DECISIONS.md:
- collections and data sources
- daily floor definition: daily median of the floor series (not raw
  ticks); store ETH and USD
- wash-trade filter rules (see 10.5)
- liquidity rule: illiquid if fewer than N sales in the last 7 days
  (propose N from the 10.0 data)
- risk target, candidates and baselines (10.3)
- fair value target, candidates, baselines and metrics (10.6)
- proposed API fields and DB tables (for Person B)
Add a Phase 10 row to PLAN.md. Send the D-entries and wait.

10.2 Collection data (3 days) — CHECKPOINT
- Collector module under ml/ (or where 10.0 found NFT code should live):
  backfill daily floor (ETH, USD), volume, sales count per collection.
- Daily refresh job, same pattern as ml-refresh.
- Snapshot the backfill for evaluation (frozen, hashed).
- Tests: no duplicate days, no future dates, gaps reported, ETH and USD
  consistent with the ETH price that day.
Report: rows per collection, date ranges, gaps, snapshot hashes.

10.3 Collection risk and liquidity (3 days) — CHECKPOINT
- Target: log forward 30-day realised volatility of daily floor log
  returns (ETH-denominated), same definition as D24.
- Candidates: EWMA (lambda 0.94). Optionally GARCH(1,1) only if 10.2
  shows 365+ clean days per collection.
- Baseline: persistence (trailing 30-day vol). Metric: QLIKE, plus
  Spearman. Approval per rule 2.
- Liquidity score: from 7-day and 30-day sales count and volume. Rule-based
  and documented, no model.
- If EWMA is approved, map it to a 0-100 risk score with a pooled
  percentile across collections (like D36).
Report: verdict table, liquidity scores per collection.

10.4 Collection page and cone (3 days) — CHECKPOINT
- Propose to Person B: endpoints such as GET /nft/collections and
  GET /nft/collections/{slug} returning floor history (ETH, USD),
  volatility, risk_score, liquidity, last_updated. Wait for OK before
  backend changes.
- Frontend: collection page with floor chart that continues into the
  30-day cone using volCone.js. Toggle ETH / USD. Caption: "Likely floor
  range based on recent volatility, not a price prediction."
- Hide the cone if volatility is missing, stale (same 36 h rule), the
  collection is illiquid, or EWMA was not approved in 10.3.
- Start label "Last floor, <date>". Liquidity badge on the page.
- Dashboard: "collections tracked" and NFT scores show real values.
- Tests: cone hide rules, no forecast line drawn, contract tests.
Report: screenshots (desktop dark and light, phone), tests.

10.5 Item-level data (4 days) — CHECKPOINT
- For each collection: item traits (metadata) and full sales history
  (token id, price in ETH and USD, timestamp, marketplace, buyer, seller).
- Wash-trade filter, documented in a D-entry:
  * drop sales where buyer == seller
  * drop sales where the same pair of wallets trade the same token back
    and forth within 30 days
  * drop sales below 10% or above 20x the collection floor that day
  * drop sales flagged as wash trades by the source, if it flags them
  Report how many sales each rule removes.
- Snapshot (frozen, hashed).
- Tests: no duplicates, every sale has a floor for its date, traits
  complete, filter rules tested.
Report: sales per collection before and after filtering, date ranges.

10.6 Fair value model (7 days, max) — CHECKPOINT
- Target: premium = log(sale price ETH / collection floor ETH on the
  sale date). Fair value = floor x exp(predicted premium). This removes
  market-wide moves, like using returns instead of prices.
- Features (all known before the sale):
  * trait one-hots and each trait's rarity (share of supply)
  * overall rarity rank
  * this token's previous sale premium and days since that sale
  * collection floor volatility and liquidity on the sale date
  * collection id (if pooled)
- Baselines:
  (a) floor: premium = 0
  (b) rarity heuristic: trailing 90-day median premium of sales in the
      same rarity decile of the same collection
- Candidates (max 4 configs each): LightGBM per collection; LightGBM
  pooled over collections; quantile LightGBM (q 0.10, 0.90) for the 80%
  range.
- Walk-forward by month, ordered by sale time. A token's own later sales
  must never be in training for an earlier test sale.
- Metrics: median absolute % error of predicted vs actual sale price
  (primary); 80% range coverage overall and per tail (each ~10%).
- Approval per rule 2 against the BEST baseline. Range approved only if
  coverage is within 75-85% and neither tail misses more than 15%.
- Comparable sales: for any item, the 3 most similar sold items in the
  last 90 days by trait overlap. Rule-based, no model; does not need
  approval.
Report: verdict table per collection, coverage table, trial count.

10.7 Fair value serving and item card (4 days) — CHECKPOINT
- Only for approved collections. Train final models in the training
  image; save LightGBM text models with metadata.json.
- Propose to Person B: GET /nft/collections/{slug}/items/{token_id}
  returning fair_value_eth, lower_eth, upper_eth, premium_vs_similar_pct
  (only if the item is listed), drivers (top 5 feature contributions),
  similar_sales (3), model_version. Wait for OK.
- Frontend item card: listed price, estimated fair value with range,
  "X% above/below similar items", what drives the estimate, similar
  recent sales. Caption: "Estimate from traits and recent sales of
  similar items. Not a forecast of future price."
- Collections that were not approved show traits and similar sales
  only, no fair value.
- Monthly retrain job; live log of predicted vs actual for new sales;
  ALERT if a served model falls behind its baseline for 2 months. Never
  switches models automatically.
Report: screenshots, contract tests, serving image size.

10.8 Sealed test (1 day) — CHECKPOINT
Run the sealed test ONCE on chosen configs (risk and fair value).
A part stays served only if it is approved in walk-forward AND not worse
than its baseline on test. Record whatever comes out. The planner
decides what stays served.

10.9 Close (1 day)
STATUS.md "How to verify Phase 10 yourself", docs/phases/
PHASE_10_nft.md, GLOSSARY terms (floor price, wash trading, premium,
rarity rank, liquidity score, comparable sales), scorecard updated.

Total: about 5-6 weeks.
Expected outcome (not a target): the cone and liquidity are likely to
ship; the fair value model has a reasonable chance on liquid collections;
thin collections will probably stay on baselines.

CHECKPOINT REPORT FORMAT
1. What ran (commands) and what changed (files, commits).
2. Verdict tables copied from the JSON reports, no hand-typed numbers.
3. Test results and snapshot hash check.
4. Rule breaks and open questions. Then stop and wait.
