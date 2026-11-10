# Checkpoint 10.4: Collection page and cone

Date: 2026-11-11. Branch `phase-10-nft`. Plan step 10.4; D52 (amended), D59, D61 (approved by the user), D67 (AUTONOMOUS, needs review).

## 1. What ran and what changed

**Commits:**
- f89cc65: D67.
- e1dee9b, ML: `ml/serving/nft_responses.py`, plus four routes on :8001: `GET /nft/collections`, `/nft/{slug}/floor?days=`, `/nft/{slug}/risk` and `/nft/{slug}/sales?days=`.
  - Schemas are in the new `ml/docs/CONTRACT_NFT.md`, and every NFT response is validated before it is returned. CONTRACT.md and its test are unchanged.
  - Config: `NFT_RISK_VOL_COLUMN = "ewma_vol"`, `MODEL_VERSION_NFT_RISK = "nft-ewma-pooled-pct"`.
  - Docker: `ML_NFT_DIR=/data/nft`, and a new sidecar `ml-nft-refresh` (00:10 UTC; keys come from `.env` through compose).
- Backend, all prefixed `backend:`; the user approved these for Phase 10 (there is no Person B):
  - **a9edff3**: `backend/controllers/nft_pull.py`, called from the existing ml-pull. Adds upsert helpers in `db/queries.py` and two indexes in `db/indexes.py`.
  - **eca725c**: `GET /nft/collections/{slug}` adds `floor_history`, `volatility`, `risk_score`, `risk_note` (with the backend's 36 h stale note), `risk_model_version`, `risk_as_of` and `last_updated`. The dashboard's `nft_score_count` now counts collections that have an ML NFT risk score.
  - **7351e3c**: `db/seed_nft.py` now holds the 7 real collections, is idempotent, and deletes the fictional collections and made-up rows. `nftCollections.json` lists the 7 collections with no numbers. `seed_aai_scores.py` no longer writes NFT AAI rows. The demo user now holds pudgypenguins #7862 and azuki #8604 at the prices of real sales, and the watchlists use milady and doodles-official. Includes `backend/tests/test_nft_pull.py`.
- **01f9418**, frontend:
  - New: `pages/NftCollectionPage.jsx` (route `/nft-collection?slug=`), `components/nft/NftFloorCard.jsx`, `services/nftApi.js`, `styles/nftCollection.css`, and `utils/nftCone.js` with its tests.
  - The chart drawing moved into a shared `components/charts/ConeChart.jsx`, used by both `PricePerformanceCard` and the NFT card. `volCone.js` gains `coneFromVol`, and the crypto `buildCone` is unchanged.
  - Dashboard trending cards, Discover NFT cards, search results and the notification deep link now open the collection page.

**Local deployment** (logs in `logs/10.4_*`):
- The host backfill was copied into the `ml-data` volume. Then `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh` ran. The sidecar's first run was all OK, and the incremental sales continued from the backfill.
- `seed_nft.py` and `seed_user_data.py` ran in the backend container against the local `aaip_db`.
- `docker restart altinvest-backend`: the backend was restarted, not recreated, so it keeps its local Mongo environment and does not pick up the Atlas URI from `.env`. The pull stored all 3 crypto assets and all 7 NFT collections: 2,800 market rows, 7 liquidity, 7 risk and 4,608 sales.

## 2. API values (from the running services; logs `10.4_docker_ml_api.log`, `10.4_backend_api.log`)

- `GET :8000/nft/collections/azuki`:
  - 365 floor_history rows, from 2025-11-11 to 2026-11-10.
  - volatility 1.120375, risk_score 18.059113, `nft-ewma-pooled-pct`, as_of 2026-11-10.
  - The note ends "...relative to the other tracked NFT collections (higher = safer) and is not comparable to crypto risk scores."
  - Liquidity: Low, 55 sales in 7 days.
- `:8001/nft/pudgypenguins/risk`: volatility 0.879462, risk_score 33.448276, liquidity Medium.
- Crypto `/risk/BTC` returns 200 on both :8001 and :8000.

## 3. Screenshots (`ml/docs/phase10/screenshots/`, local docker stack, demo user, headless Edge)

| File | What it shows |
|---|---|
| `10.4_collection_desktop_dark.png` | Pudgy Penguins, ETH, 3M. The floor line runs into the 50% and 80% cone, labelled "Last floor, 10 Nov". It shows the liquidity badge, the caption, and the risk card's "relative to other NFT collections, not comparable to crypto" note. |
| `10.4_collection_desktop_light.png` | The same page in the light theme, switched with the app's own toggle. |
| `10.4_collection_desktop_light_usd.png` | USD view. The caption adds "In USD the range is the ETH range at the last ETH price; it does not include future ETH-USD moves." |
| `10.4_collection_phone_dark.png` | 390 px wide, with a tall viewport so the whole page fits in one image. The sidebar was collapsed with its own button (see section 5). There is no horizontal scroll (scrollWidth 390). |
| `10.4_dashboard_desktop_dark.png` | "Across 18 tracked assets and 7 collections"; "Composite of 3 crypto and 7 NFT scores"; 4 holdings. |
| `10.4_btc_asset_desktop_dark_regression.png` | BTC after the chart refactor: the cone is still drawn, labelled "Last close, 8 Nov". |

The facts behind these were read from the DOM by the script and are in `screenshots/10.4_screenshot_facts.json`. Every view has the layers `history cone-outer cone-inner`.

## 4. Tests

- ML `python -m pytest ml -q`: **340 passed**. That is 331 plus 9 in `test_nft_serving.py`:
  - schemas closed and separate from the crypto contract;
  - every response validates; 404 and 503 cases;
  - the served volatility equals the 10.3 evaluation's EWMA predictor on the same rows;
  - the risk score is the pooled NFT percentile, and the note says it is not comparable to crypto;
  - the stale note appears after 48 h;
  - no volatility under 60 days;
  - the cache follows file changes;
  - the config matches the 10.3 report;
  - the real live data validates against the contract.
- Two fixture errors were fixed while writing these tests; the code was not changed:
  - the floor points ended a day early;
  - the last date's ETH rate is the previous bar's close (D63).
- Backend, in its container: **26 passed** (20 before, plus 6 in `test_nft_pull.py`):
  - the pull's keys and rows;
  - a failed endpoint, or a bad body, writes nothing;
  - a 404 listing is skipped;
  - the detail route returns the history and ML risk;
  - a risk row older than 36 h gets the stale note;
  - the seed has exactly the 7 ML slugs and no fictional ones.
- Frontend `npm test`: **13 passed** (7 crypto cone tests, 6 NFT). The NFT tests check:
  - the cone uses the same maths as crypto;
  - it hides when the volatility is missing, null, zero or not a number, when the data is stale (36 h and 48 h notes), or when the collection is illiquid;
  - it does not hide for a served persistence volatility;
  - the USD cone equals the ETH cone times the last ETH price;
  - there is never a forecast or centre line;
  - the labels and captions are as required.
- Two existing crypto tests that read source text now read the shared `ConeChart.jsx`. They still check the same things: `futureShare(histSpan)`, the `coneStartLabel` start label and `data-role="cone-start"`.
- eslint is clean on every changed file. Its errors in `charts/TimeSeriesAreaChart.jsx` were already there on HEAD (that file is not changed). `npm run build` passes.
- Snapshot `--verify`: OK. Serving image `altinvest-ml`: 848 MB (no new dependencies; pyarrow is not needed for serving).

## 5. Rule breaks, findings, open questions

**Rule breaks:** none.

**The cone appears for all 7 collections:** EWMA was approved, no collection is illiquid, and the data is fresh.

**Findings:**
- **Phone layout:** at 390 px the app shell's sidebar does not collapse on its own. This is the existing HIGH frontend backlog item in STATUS, not new in this phase. With the sidebar collapsed by hand, the page fits without horizontal scroll, but the chart is narrow (about 250 px).
- **Labels not changed:** "Global AAI Sentiment: composite of ... NFT scores" now counts ML NFT risk scores (D67e). The label text was left alone.
- **Docker note:** `docker compose up` for the backend would pick up the Atlas `MONGO_URI` from `.env` (the Phase 7 finding). That is why only the ML services were recreated.

**Open question:** accept D67, in particular the dashboard count and the USD cone convention.

Continuing to 10.5 (autonomous mode).
