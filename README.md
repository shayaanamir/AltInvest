# AltInvest

**An analytics platform for alternative investments: crypto and blue-chip NFT collections.**

AltInvest brings prices, news sentiment and risk measures together into one score per asset, the
**Alternative Asset Index (AAI)**, and shows it next to your portfolio, watchlists, alerts and a detail
page for every coin and NFT collection. It is built to be honest about what it knows: an ML number is served only
if it beat a simple baseline on held-out data, and where nothing did, the baseline is served and the app says so.

> **For analysis and education only. It is not financial advice.** AltInvest is a final-year (LY) project at Somaiya.

---

## What's in the app

| Page | What it does |
|---|---|
| **Dashboard** | Market stats, portfolio performance, market insights, and trending coins and NFT collections. Which widgets show, and in what order, follows your **home focus** (below). |
| **Discover** | Every covered coin and NFT collection with search, sorting and filters (AAI score, sentiment, risk, volatility, market cap, signal). |
| **Compare** | Assets side by side. |
| **Asset and NFT pages** | Price history, volatility cone, sentiment and the AAI breakdown for a coin. Floor history, sales and item estimates for an NFT collection. |
| **Sentiment** | Market mood, themes and per-asset news sentiment. |
| **Portfolio** | Crypto and NFT holdings with cost basis, profit and loss, allocation and history. Trades are recorded atomically, so two at once can't oversell. |
| **Watchlists and Alerts** | Lists of assets to follow. Alerts on price, AAI score, sentiment or risk, delivered in the app and, if you choose, by email. |
| **Profile and Settings** | Risk profile and goal, display currency, date format, theme and density, notification rules (email, quiet hours), connected Google account, data export and account deletion. |

**Accounts:** email and password with email verification and password reset, or Google sign-in. A five-step
onboarding asks which markets you follow, your risk comfort, your goals, which assets to follow (saved as a starter
watchlist) and your **home focus**: Everything, Portfolio, Markets or Sentiment. The focus changes the dashboard layout
and the page AltInvest opens on after sign-in, and can be changed any time in Settings.

### The AAI score

```
AAI = 0.40 × prediction score + 0.30 × sentiment score + 0.30 × risk score        (each 0-100)
```

BUY is 55 and above, HOLD is 45 to 55, SELL is below 45. The formula is in [aai_engine/aai.py](aai_engine/aai.py).

**What is real today**

- **Prices and market data** come from CoinGecko and Binance, refreshed by background jobs. No API key is needed.
- **Sentiment** scores news headlines from publisher RSS feeds and per-coin Google News searches with VADER and FinBERT,
  and blends them with market signals. If a Groq key is set, an LLM also names the market themes and scores NFT news.
- **ML coverage is BTC, ETH and SOL only**, plus NFT risk and item fair value for 7 collections. The ML service serves what
  beat its baseline:

| Output | Served | Why |
|---|---|---|
| Crypto 30-day price | The last value ("no change") | No model beat it on held-out data |
| Crypto direction signal | `UNCERTAIN` | Not served as a signal |
| Crypto risk | 30-day volatility, ranked 0-100 | GARCH/EWMA gains were not confirmed |
| NFT floor risk | 30-day volatility of the raw floor | EWMA approval withdrawn after review |
| NFT item fair value | Pooled LightGBM model, refit monthly | Passed a one-shot sealed test (median error 2.9% against 3.5% for the floor baseline) |

So for BTC, ETH and SOL the prediction part of the AAI is a neutral 50 and the response says so. For the other coins,
there is no ML prediction or risk at all unless demo data is seeded in development. That gap is tracked as N-04 in
[AUDIT_2026-11-16.md](AUDIT_2026-11-16.md). The full reasoning is in [ml/docs/STATUS.md](ml/docs/STATUS.md) and
[ml/docs/DECISIONS.md](ml/docs/DECISIONS.md).

---

## Architecture

```
            ┌──────────────┐
            │   frontend   │  React 19 + Vite                       :5173
            └──────┬───────┘
                   │ HTTP
            ┌──────▼───────┐        ┌───────────────────┐
            │   backend    │──HTTP─▶│        ml         │  FastAPI    :8001
            │   FastAPI    │        │ predict / risk /  │
            │    :8000     │        │ NFT fair value    │
            │              │        └─────────┬─────────┘
            │ imports:     │                  │ ml-data volume
            │  aai_engine  │        ┌─────────▼─────────┐
            │  sentiment_  │        │ ml-refresh        │  daily 00:05 UTC (Binance)
            │   engine     │        │ ml-nft-refresh    │  daily 00:10 UTC (OpenSea,
            │  db, shared  │        └───────────────────┘   Alchemy) + monthly refit
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │   MongoDB    │  :27017
            └──────────────┘
```

| Folder | What it is |
|---|---|
| [frontend/](frontend/) | React 19 single-page app (Vite, react-router). Page code in `src/pages`, shared pieces in `src/components`, API calls in `src/services`. |
| [backend/](backend/) | FastAPI app: auth, assets, portfolio, watchlists, alerts, notifications, NFT, discover, sentiment, risk, AAI, settings, profile. |
| [ml/](ml/) | The ML service, data pipelines, models, evaluation harness and reports ([ml/README.md](ml/README.md)). |
| [sentiment_engine/](sentiment_engine/) | News and market collectors, VADER and FinBERT scoring, blended sentiment ([README](sentiment_engine/README.md)). |
| [aai_engine/](aai_engine/) | The AAI formula. |
| [db/](db/) | MongoDB connection, indexes, seed scripts and one-off migrations. |
| [shared/](shared/) | Code shared by the backend and the engines. |

The backend imports `sentiment_engine`, `aai_engine`, `db` and `shared` directly (not over HTTP), so its Docker image is
built from the repo root. Most background jobs (market data, news sentiment, insights, alerts, portfolio snapshots, FX
rates, the ML pull) run as threads inside the backend process, and each one claims its run in the database so that
several workers don't repeat it.

---

## Quick start (Docker)

You need Docker Desktop and outbound HTTPS (CoinGecko, Binance, news feeds; OpenSea and Alchemy for NFT data).

```bash
cp .env.example .env     # then set JWT_SECRET, or keep APP_ENV=dev (see below)
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:5173 | The app |
| http://localhost:8000/docs | Backend API docs |
| http://localhost:8001/docs | ML service API docs |

The first build is slow (10 to 20 minutes) because the backend image installs `torch` and `transformers` for FinBERT.

**A fresh database starts empty.** Every machine has its own MongoDB, and git never shares data. Fill it once with the
bootstrap command, which is safe to run again:

```bash
docker exec -w /app/backend altinvest-backend python -m controllers.bootstrap_controller
```

It creates the coin names and colours and the NFT collection details, loads live prices and history, runs a news
sentiment pass, builds the insights and themes, and fetches each coin's CoinGecko profile (about 6 minutes). It writes
no made-up numbers and refuses a non-local database. Then hard-refresh the browser. More detail, including hot reload,
the production frontend image and upgrade notes, is in [DOCKER.md](DOCKER.md).

**For local development only**, `python db/seed_all.py` seeds sample data: a demo user and portfolio (only when
`APP_ENV=dev`), and also **invented predictions and risk scores** for the coins ML doesn't cover. Those invented numbers
are written whatever `APP_ENV` is, so don't use it on a real deployment (audit item N-04). It refuses a remote database
unless given `--allow-remote`.

### Configuration

Everything is in [.env.example](.env.example), with comments. The ones you will touch first:

| Variable | Used for |
|---|---|
| `APP_ENV` | `dev` on a developer machine. Anything else (or unset) means production: the backend **refuses to start without a real `JWT_SECRET`**, the demo user is never seeded, and email links are never logged. |
| `JWT_SECRET` | Signs login tokens; at least 32 bytes. Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `FRONTEND_BASE_URL` | Where the frontend lives. It is the only origin the API accepts cross-origin calls from (CORS), and the base of the links in emails. |
| `ADMIN_EMAILS` | Verified accounts allowed to force a sentiment refresh. Empty means nobody. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google sign-in. Leave empty to disable the buttons. |
| `SMTP_*` | Verification, password reset and alert emails. With `SMTP_HOST` empty in dev, the links are printed to the backend log instead. **Outside dev, new users can't finish signing up without SMTP.** |
| `GROQ_API_KEY` | LLM-named market themes and NFT news sentiment (optional). |
| `OPENSEA_API_KEY`, `ALCHEMY_API_KEY` | NFT floor prices, sales and traits. |
| `MONGO_DB_NAME` | The one application database (`aaip_db` by default). |
| `BACKEND_MONGO_URI` | Point the backend container at a database other than the local `mongodb` service. |

Keep your real `.env` out of git. It is already ignored.

---

## Tests

```bash
cd backend && python -m pytest tests -q          # backend (install backend/requirements.txt first)
cd sentiment_engine && python -m pytest tests -q # sentiment engine (run from inside its folder; see its requirements.txt)
python -m pytest aai_engine -q                   # AAI engine (run from the repo root)
python -m pytest ml/tests -q                     # ML (run from the repo root, not from ml/)
cd frontend && npm test                          # frontend unit tests
cd frontend && npm run lint && npm run build     # lint and production build
```

- The sentiment tests need `sentiment_engine/requirements.txt` (`feedparser` and the NLP libraries), and from the repo root 5 of them fail on import paths, so run them from inside the folder.
- The ML tests need `ml/requirements.txt` plus `pyarrow`. Installing `ml/requirements-train.txt` as well (it pulls in CPU torch and Prophet) runs about 9 more training and evaluation tests that are otherwise skipped.
- Some backend tests run against a real MongoDB only when `MONGO_TEST_URI` is set, and are skipped otherwise. Use a
  throwaway server, for example `docker run --rm -p 27099:27017 mongo:7`, with `MONGO_TEST_URI=mongodb://localhost:27099`.
- `test_seed_guard` reads the repo-root `.env`, so it fails if that file points at a remote database.
- GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of the above on every push to `main` and every pull request, with a real MongoDB so the concurrency tests run. It also runs `pip-audit` and `npm audit` weekly, and checks that the compose files are valid. For the ML job, `pyarrow` is the one extra package the tests need (`pip install -r ml/requirements.txt pyarrow==26.0.1`).

---

## ML methodology, in short

- **Data:** Binance daily candles for crypto; OpenSea floors and sales plus Alchemy traits for NFTs, with frozen, hashed
  snapshots for evaluation.
- **Evaluation:** chronological splits with a **sealed test set**, expanding-window walk-forward with an embargo, at most
  4 declared configurations per model type, and approval only when the paired block-bootstrap 95% interval of the gain
  over the baseline is above zero.
- **Every phase** has a write-up in [ml/docs/phases/](ml/docs/phases/), and every protocol choice is an append-only decision
  in [ml/docs/DECISIONS.md](ml/docs/DECISIONS.md).

Further reading: [ARCHITECTURE](ml/docs/ARCHITECTURE.md) · [CONTRACT](ml/docs/CONTRACT.md) ·
[CONTRACT_NFT](ml/docs/CONTRACT_NFT.md) · [EVALUATION](ml/docs/EVALUATION.md) · [GLOSSARY](ml/docs/GLOSSARY.md).

---

## Project status

AltInvest runs well as a local development stack. It is **not production-ready yet**. There is no production compose
file (the frontend runs the Vite dev server and MongoDB is published without authentication), and the background
jobs still share a process with the API. [AUDIT_2026-11-16.md](AUDIT_2026-11-16.md) is the current review: every known gap,
what has been fixed, and what is left. [AUDIT_2026-11-02.md](AUDIT_2026-11-02.md) is the earlier one, kept for its detailed
write-ups. Open ML items are in the backlog section of [ml/docs/STATUS.md](ml/docs/STATUS.md).
