# Checkpoint: real prices, seed cleanup, backups (2026-11-16)

Branch `real-prices`, from `main` at 180aa51. Not pushed, not merged. This step is code plus read-only checks: **no backup, backfill or cleanup was run, and nothing was written to Atlas or the local Mongo.** Commits touching `backend/` or `db/` are prefixed `backend:`. Decisions D90-D93 are in ml/docs/DECISIONS.md. D87-D89 are skipped because branch phase-11-cone uses them; expect a trivial conflict at the end of the decisions table when both merge. Items marked (A) are AUTONOMOUS and need review.

## 1. Commits

| Commit | What |
|---|---|
| `217f1d3` | backend: seed guard fix (item 5) |
| `e0c5129` | backend: real Binance price feed and backfill (item 1) |
| `2843f47` | backend: seed cleanup, hidden assets, migration check (items 2, 4) |
| `1a451a7` | backend: backup and restore tooling (item 3) |
| this commit | D90-D93, this checkpoint, the dry-run and migration JSON |

`README.md` (the owner's edit) stays uncommitted.

## 2. What was built

1. **Price feed (D90, `backend/controllers/price_feed.py`).**
   - **`prices`:** one row per **closed 1-hour** Binance kline (BTCUSDT, ETHUSDT, SOLUSDT): close, quote volume, `source: "binance-klines-1h"`. These are the same symbols and endpoint as `ml/data/fetch.py`.
   - **Why hourly, not daily (A):** sparklines (168 h), trending (31 × 24 h), the dashboard 1D chart and `/performance` read `prices` as hourly rows. The 23:00 kline closes with exactly the 1d close; this was checked on 5 days for all three assets. So the chart's last price per day equals the ML close, and the Phase 11 guard sees a gap of 0. A test checks this through `get_daily_price_series`.
   - **`asset_market_data`:** one row per asset and day, with the ticker's last price and the 1h, 24h and 7d change. `source: "binance-ticker"`.
   - **Fields left null (A):** market cap, rank, supply and 24h volume. Binance doesn't publish them; its volume is one exchange's only.
   - **Idempotent:** upserts on (asset, timestamp) and (asset_id, date). A seeded row at the same hour is overwritten and gets the real source.
   - **Schedule:** daily inside the ML pull (startup and 00:15 UTC), fetching from the newest stored real hour (at most 400 days back, at least the last 72 h).
   - **Backfill:** `python -m controllers.price_feed --backfill-days 400`; `--dry-run` only counts.
   - **Network (A):** each call retries, then falls back to `data-api.binance.vision`. On this machine Docker's first connection to api.binance.com often fails ("Network is unreachable"), and the mirror answered every time.
2. **Seed cleanup (D91, `db/cleanup_seed_data.py`).**
   - Dry run by default. Real deletes need `--confirm`, and on Atlas also `--allow-remote`, through `db/seed_guard.py`. Only hosts are printed.
   - Rules: section 4. User collections are never deleted from.
   - Assets with no real source are handled by `--unsourced-assets keep|hide|delete` and `--prune-watchlists` (section 4).
3. **Backup (D93).** `db/backup_atlas.ps1 -OutDir <folder outside the repo>` runs mongodump of `altinvest_db` from the `mongo:7` image. It refuses a folder inside the repo before creating anything (tested). The matching mongorestore is in `db/BACKUP.md`. Not run.
4. **Migration check (D92, `db/migration_check.py`).** Read-only. Results in section 5.
5. **Seed guard.** `require_local_target(uri=None)` used to fall back to the live `MONGO_URI` (Atlas in the dev container), so `test_local_targets_pass[None]` failed. A sentinel now marks "read the environment". Tests pass URIs explicitly; three tests were added.

## 3. Tests

The stack was stopped outside this session (all six containers exited at 20:56 UTC), and the backend was not restarted. Tests ran in a throwaway container from the backend image with `--network none`: no database and no network.

| Suite | Result |
|---|---|
| `backend/tests` (full) | 65 passed, 2 skipped |
| `test_price_feed.py` (new) | 10 |
| `test_cleanup_seed_data.py` (new) | 9 |
| `test_seed_guard.py` (3 new) | passes, including the formerly failing `[None]` case |

- The 2 skips are the compose check and the ml/config.py symbol check: those files aren't visible in the container.
- No `mongomock` in the image, so `backend/tests/fake_mongo.py` is a small in-memory fake.

## 4. Cleanup dry run on Atlas (read-only, `cleanup_dry_run_atlas.json`)

Target `altinvest-cluster.xn7ma0g.mongodb.net / altinvest_db`. Counts only; nothing changed.

| Collection | Would delete | Of | Rule |
|---|---|---|---|
| prices | 86,400 | 86,400 | no source (simulated, `seed_prices.py`) |
| asset_market_data | 18 | 18 | no source (seeded) |
| predictions | 21 | 36 | no source or seed-v1 |
| risk_scores | 18 | 33 | no source |
| risk_breakdown | 36 | 36 | no source |
| aai_scores | 18 | 33 | seed-v1 |
| market_insights | 6 | 6 | seed titles |
| sentiment_themes | 5 | 5 | seed labels |
| nft_collections | 4 | 11 | the 4 fictional slugs |
| nft_market_data | 10 | 2,810 | fictional or no source |
| nft_sales | 4 | 3,652 | fictional or no source |
| nft_holder_stats | 10 | 10 | fictional or no source |
| nft_liquidity | 10 | 17 | fictional or no source |
| nft_risk_breakdown | 10 | 17 | fictional or no source |
| nft_traits | 1 | 1 | no source |
| nft_tokens | 1 | 1 | no source |
| nft_token_sale_history | 2 | 2 | no source |
| nft_token_ownership_history | 4 | 4 | no source |
| **Total** | **86,578** | | |

**Every row in `prices` and `asset_market_data` would go, including BTC, ETH and SOL.** Run the backfill (D90) before the cleanup, or the header and charts are empty until the next pull.

**Assets with no real price source:**

| Asset | References in user data |
|---|---|
| ARB, DAI, UNI | none |
| BASE | 1 holding, 1 transaction |
| DOGE | 1 watchlist item |
| LINK | 1 watchlist item |

- **What these assets lose:** price, 24h/7d change, market cap, rank, supply and volume. Also the chart and sparkline, their place in Discover, the dashboard, compare and trending (all built from `asset_market_data`), and the seeded prediction, risk and AAI. Nothing replaces these, because the ML doesn't cover these assets.
- **Proposal: hide (`--unsourced-assets hide`).** The asset documents stay, so the BASE holding and transaction keep a name. Lists, search and the detail page skip the assets (`get_supported_assets`, `get_asset` and `search_all` filter `hidden`). The step can be undone by unsetting the flag.
- `delete` removes the asset documents, plus their watchlist items when combined with `--prune-watchlists`. The BASE holding would then point at an unknown asset.
- Watchlist items pointing at fictional collections: `genesispunks` 1, `astralcats` 1. `--prune-watchlists` removes them.
- The holding, transaction and alerts are only reported, never deleted.

## 5. Migration check: local `aaip_db` -> Atlas `altinvest_db` (read-only, `migration_check.json`)

The local Mongo container was started only for this check (owner approved) and then stopped again.

| Collection | Real rows (local) | Missing in Atlas | Pulled later locally | Missing dates | Proposal |
|---|---|---|---|---|---|
| ml_past_ranges | 3 | 3 | 0 | all (Phase 11) | RE-PULL: comes with the phase-11-cone merge |
| predictions | 21 | 12 | 9 | 2026-11-09 to 11-14 | COPY: the ML serves only today's row |
| risk_scores | 21 | 12 | 9 | 2026-11-09 to 11-14 | COPY |
| nft_market_data | 2,835 | 35 | 2,800 | 2025-10-07 to 10-11 | RE-PULL (the floor history is served again) |
| nft_liquidity | 35 | 28 | 7 | 2026-11-10 to 11-14 | COPY |
| nft_risk_breakdown | 35 | 28 | 7 | 2026-11-10 to 11-14 | COPY |
| nft_sales | 5,262 | 1,614 | 3,648 | 2026-10-11 to 11-10 | COPY: the pull asks for 30 days only |
| nft_item_values | 4 | 4 | 0 | (local demo holdings) | RE-PULL for the tokens Atlas users hold |
| fx_rates | 5 | 2 | 1 | | SKIP: the latest is refetched |
| prices | 1,200 | 219 | 0 | 2026-08-28 to 11-08 | SKIP: the D90 backfill replaces them |
| portfolio_snapshots | 18 | 18 | 0 | 2026-11-10 to 11-15 | SKIP: the local users don't exist in Atlas |

- "Pulled later locally" means the same key with a later `pulled_at`. The values are most likely identical, and for RE-PULL collections a pull refreshes them anyway.
- Every local collection with real rows has a rule: no unknown collections.
- No copy tool is written yet. Copying would be a later, separate step after a backup, with an upsert on the keys above.

## 6. Order for the owner (none of it run)

1. Back up: `powershell -ExecutionPolicy Bypass -File db\backup_atlas.ps1 -OutDir D:\altinvest-backups`.
2. Backfill:
   - First, inside the backend container: `python -m controllers.price_feed --backfill-days 400 --dry-run`.
   - Then the same command without `--dry-run`.
   - Or restart the backend on this branch; the startup pull writes the last 72 h only.
3. Clean up:
   - Dry run: `python -m db.cleanup_seed_data` (from `/app`).
   - Then: `--confirm --allow-remote --unsourced-assets hide --prune-watchlists`.
4. Migration: re-pull happens with the daily pull. COPY needs a decision and a tool.

## 7. Notes

- A backend restart on this branch writes to Atlas immediately: the price feed (last 72 h) and the other ML pulls.
- `asset_market_data` will show null market cap, rank, supply and volume for BTC, ETH and SOL too. Lists sort by market cap with `or 0`, so the three tie. A real source for these (for example CoinGecko or CMC, whose collector already exists in the backend logs) would be a separate decision.
- `assets` metadata (names, descriptions, all-time highs) is seeded but describes real coins; the cleanup leaves it. The BTC all-time high shown ($108,950) is out of date.
