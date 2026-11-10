# Hard-coded asset prices: findings and proposed fix

Written 2026-11-10 by the ML side for Person B (backend). This is a read-only investigation: no file in `backend/` or `db/` was changed.
Priority: HIGH. Asset prices are hard-coded seed data and never update; ETH is about 80% off.

## 1. The problem

Two collections hold price data, and only seed scripts write either one:

| Collection | Holds | Written by | Updated after seeding? |
|---|---|---|---|
| `asset_market_data` | price, change_1h / 24h / 7d, market_cap, volume_24h, circulating_supply, market_rank | `db/seed_assets.py` `seed()`: hard-coded `MARKET_DATA` for 9 assets, plus `db/seed_data/assets.json` | No. Nothing in `backend/` writes it. |
| `prices` (hourly) | price, volume per hour | `db/seed_prices.py` `seed()`: **synthetic** geometric Brownian motion, rescaled so every series ends exactly at the seed price (`TARGET_PRICE`) | No. |
| `nft_market_data` | floor_eth, floor_usd | `db/seed_nft.py`: floor_usd = floor_eth × 3,845.60, the seeded ETH price | No. |

Seed price vs the real Binance daily close, 2026-11-08 (from the ML serving CSVs; BTC has also refreshed to 2026-11-09):

| Asset | Seed price | Real close | Seed is off by |
|---|---|---|---|
| BTC | $71,450.30 | $75,368.41 (11-09) | −5.2% |
| ETH | $3,845.60 | $2,127.46 | **+80.8%** |
| SOL | $178.92 | $86.54 | **+106.7%** |

Not checked: LINK, DOGE, ARB, DAI, UNI and BASE. They come from the same hard-coded list, so they should be assumed wrong too.

`db/seed_all.py` labels the price step "prices (from ml/data/raw CSVs)", but `db/seed_prices.py` does not read those CSVs; it generates synthetic data. So in the shared database every price chart and sparkline is synthetic as well, and each one ends at the hard-coded price.

## 2. Where the seeded prices are read, and what the user sees

### From `asset_market_data`

| # | File: function | Endpoint | What the user sees that is wrong |
|---|---|---|---|
| 1 | `backend/routes/assets.py`: `get_asset_detail` | `GET /assets/{s}/detail` | Asset page header price and 24h change; Market Stats card (rank, market cap, 24h volume, supply) |
| 2 | `backend/routes/assets.py`: `get_asset_header`, `get_asset_market_stats` | `GET /assets/{s}/header`, `/assets/{s}/market-stats` | The frontend does not call these; any other API consumer gets the seed values |
| 3 | `backend/controllers/market_controller.py`: `build_crypto_items` | `/discover`, `/compare`, `/compare/candidates`, and related / similar assets in `/assets/{s}/detail` | Discover cards; Compare cards; related and similar asset cards; topbar search prices (`topbarApi.js`); Sentiment page prices (`sentimentApi.js` via `fetchUniverse`) |
| 4 | `backend/controllers/portfolio_controller.py`: `get_valued_holdings` | `/portfolio/holdings`, `/portfolio/summary`, `/portfolio/allocation` | Holdings' current price, value and unrealised P&L; portfolio total and P&L; allocation percentages |
| 5 | `backend/controllers/portfolio_intelligence.py`: `build_intelligence` (via 4) | `/portfolio/intelligence` | Value weights behind the portfolio's AAI and risk summary |
| 6 | `backend/routes/dashboard.py`: `get_dashboard_stats` (via 4 and directly) | `/dashboard/stats` | Dashboard portfolio value and total 24h volume |
| 7 | `backend/controllers/snapshot_controller.py`: `record_snapshots` (via `get_total_portfolio_value`) | daily thread `portfolio-snapshots` (`backend/main.py`) | **Stored every day:** `portfolio_snapshots` rows valued at seed prices feed the 1W–1Y portfolio and dashboard performance charts. The history is flat at the seed value and stays wrong after a fix unless it is rebuilt. |
| 8 | `backend/routes/dashboard.py`: trending route, `controllers/trending_controller.py`: `score_assets` | `/dashboard/trending` | Trending list and its reasons ("2.1× its usual daily move"), using seeded `change_24h`; also the exported report (`reportApi.js`) |
| 9 | `backend/routes/watchlists.py`: `enrich` | `/watchlists` | Watchlist rows' price and 24h change |
| 10 | `backend/controllers/alert_controller.py`: `_current_values` | alert evaluation | **Price alerts never fire:** the price never moves, so `crossed()` never sees a crossing |
| 11 | `frontend/src/components/portfolio/AddHoldingModal.jsx` (ETH price from the `/discover` universe) → `backend/controllers/holdings_controller.py` | `POST` / `PATCH /portfolio/holdings` | **Stored in user data:** a new or edited NFT holding records `avg_buy_eth_usd_rate` = $3,845.60 and computes `cost_basis_usd` from it, so NFT cost basis and P&L are too high by about 81% and stay wrong |

### From `prices` (synthetic, ending at the seed price)

| # | File: function | What the user sees |
|---|---|---|
| 12 | `db/queries.py`: `get_daily_price_series`, used by `get_asset_detail` | Asset page price chart (all filters). The D52 volatility cone starts at this chart's last close, so in the shared database the cone's start point is synthetic too; its width (ML's EWMA volatility) is real. |
| 13 | `db/queries.py`: `get_price_sparklines` | Sparklines on Discover and Trending |
| 14 | `backend/routes/dashboard.py`: performance, filter `1D` | Dashboard 1D portfolio chart (hourly prices × quantity) |
| 15 | `backend/controllers/trending_controller.py`: `_recent_rows` | Trending's "usual daily move" and "volume vs 7-day average" |
| 16 | `db/seed_portfolio_snapshots.py` | Back-filled portfolio history (seed-time only) |

### From `nft_market_data`

| # | Where | What the user sees |
|---|---|---|
| 17 | `get_valued_holdings`, `build_nft_items`, `_current_values` | NFT floor prices in USD and NFT holding values, scaled by the seeded ETH price |

### Not affected today

- **AAI score:** `backend/controllers/aai_controller.py` `_expected_return_pct` reads `get_latest_price` only when a prediction has a `predicted_price`. ML serves `predicted_price: null` (no price model is approved), so price does not enter the AAI score now. It would once a price model is served.
- **ML service, `/risk` and `/predict`:** these use ML's own Binance daily closes, not Mongo.
- **Sentiment `marketSignals.price_change_24h`:** comes from the sentiment engine; not traced.

## 3. Proposed fix (not implemented)

### Where real prices come from

The Binance public REST API: the same source ML already uses (`ml/data/fetch.py`). It needs no key and has generous rate limits.

1. **Live price (header, lists, portfolio, alerts):** every **5 minutes**, one call to `GET /api/v3/ticker/24hr` with all `XXXUSDT` symbols. It returns `lastPrice`, `priceChangePercent` and `quoteVolume`. Write one new `asset_market_data` row per asset with `source: "binance-ticker"` and the exchange's `closeTime` as `timestamp`.
   - Market cap = price × `circulating_supply`. Supply and rank change slowly; refresh them daily from CoinGecko, which `db/enrich_asset_profiles.py` already uses.
2. **History (charts, sparklines, trending, dashboard 1D):** a one-time backfill of 365 days of **hourly klines** (`/api/v3/klines?interval=1h`, 9 pages of 1,000 per asset) that replaces the synthetic rows. After that, append the closed hourly bar every hour.
   - Upsert on (asset, timestamp) so a re-run does not duplicate rows.
   - The 23:00 UTC bar's close equals the daily close that ML uses, so the chart, the D52 cone and ML read the same data.
3. **Why not just ML's daily closes:** ML exposes no price endpoint (that would be a contract change), its CSVs live in the `ml-data` volume, and a daily close can be up to 24 h old, which is fine for the chart but wrong for a header price.

Run this as a backend thread like the existing `ml-pull`, `fx-rates` and `portfolio-snapshots` threads (`backend/main.py`), in a new `controllers/market_refresh_controller.py`.

### Assets Binance may not cover

BTC, ETH, SOL, LINK, DOGE, ARB and UNI trade as `XXXUSDT`. DAI's Binance pair and what "BASE" refers to need checking. An asset with no real source should return **no price** (`null`). The holdings code already handles that (`valuation_status: "no_price"`). It must never fall back to the seed price.

### When price data is stale

- Every response that carries a price gets `price_as_of` (the row's timestamp). These are additive fields only; nothing existing changes.
- If the newest row is older than **30 minutes** (6 missed refreshes), add `price_stale: true`. The frontend shows "Price as of 14:05" with a stale marker.
- Portfolio values keep using the last real price but carry the same stale flag.
- Alerts skip evaluation on a stale price, so a catch-up jump does not fire a burst of alerts.
- The seed scripts stop writing price fields, or tag those rows `source: "seed-demo"`. Readers then treat seed-demo rows as "no price", so demo numbers are never shown as market prices.

### Data already stored with seed prices (needs a decision)

- **`portfolio_snapshots`:** rebuild from the real daily closes once `prices` is real. `db/seed_portfolio_snapshots.py` already values holdings from `get_daily_price_series`.
- **NFT holdings with `avg_buy_eth_usd_rate` = 3845.6:** flag them, or recompute from the real ETH close on the buy date. Going forward, the backend should take the ETH/USD rate from its own latest real market row instead of trusting the client.

### Tests that would protect it

Backend pytest, with `httpx.MockTransport` as in `backend/tests/test_ml_pull.py`; no network:

1. A mocked ticker response becomes rows with `source` and `timestamp`, with values equal to the response.
2. A timeout, a 4xx or 5xx, or a malformed body writes nothing and keeps the previous row.
3. Stale boundary: a row 29 min old is fresh, one 31 min old is `price_stale: true`.
4. Header, `/discover`, `/portfolio/holdings` and `/watchlists` serve the newest real row. A `seed-demo` row is never served as a price.
5. Guard: `db/seed_assets.py` writes no untagged `price`, which stops this from coming back.
6. Kline backfill: re-running it adds no duplicates, and the 23:00 UTC close for a fixture day equals that day's close in an ML-format fixture CSV.
7. Creating an NFT holding stores the server's ETH/USD rate, not the client's.
8. Alerts: a price crossing fires once; a stale price does not evaluate.

### Size estimate

| Part | About |
|---|---|
| `market_refresh_controller.py` (ticker + hourly klines + thread) | 150 lines |
| Wiring in `backend/main.py`, schema fields (`price_as_of`, `price_stale`) | 25 lines |
| Seed changes (`seed_assets`, `seed_prices`, `seed_nft`) | 40 lines |
| Holdings: server-side ETH/USD rate | 15 lines |
| One-time backfill and snapshot-rebuild script | 80 lines |
| Tests | 200 lines |
| Frontend: "Price as of" and stale marker on the header and lists | 30 lines |

That is about 550 lines, roughly 2 days for Person B including review. The contract change is additive only (two optional fields). The ML service and its API are unchanged.

## 4. Open points

- Should the shared Atlas database be cleaned of the synthetic `prices` rows now, before the fix lands? That needs Person B and the team.
- Is a 5-minute refresh enough, or does the product want a websocket or second-level live price? I'd recommend 5 minutes; the app shows daily-horizon analytics.
- Are DAI and BASE kept as assets if no real price source exists for them?
