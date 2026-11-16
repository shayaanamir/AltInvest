# AltInvest

**An analytics platform for alternative investments: crypto (BTC, ETH, SOL) and blue-chip NFT collections.**

AltInvest combines price data, news sentiment and risk measures into one score per asset, the
**Alternative Asset Index (AAI)**, and shows it alongside portfolios, watchlists, alerts and per-asset detail
pages. Every ML number it serves has been tested against a simple baseline on held-out data; where no model
beat the baseline, the baseline is served and the app says so.

---

## What's in the app

- **Dashboard, Discover and Compare**: AAI scores, prices and risk for every covered asset.
- **Asset pages**: price history, a 30-day volatility cone, sentiment and the AAI breakdown.
- **NFT collection pages**: floor price history, floor volatility, recent sales and per-item fair-value
  estimates, for 7 collections (Azuki, BAYC, MAYC, Doodles, Milady, Pudgy Penguins, Lil Pudgys).
- **Portfolio and watchlists**: holdings (crypto and NFTs, with item value estimates) and portfolio snapshots.
- **Sentiment**: news headlines scored with VADER and FinBERT, blended with CoinMarketCap market signals.
- **Alerts and notifications**, plus accounts with email verification and password reset.

### The AAI score

```
AAI = 0.40 × prediction score + 0.30 × sentiment score + 0.30 × risk score     (each on 0-100)
```

Implemented in [aai_engine/aai.py](aai_engine/aai.py).

### What the ML service serves today

| Output | Served | Why |
|---|---|---|
| Crypto 30-day price | Last value ("no change") | No model beat it on held-out data |
| Crypto direction signal | `UNCERTAIN` | Not served as a signal |
| Crypto risk | 30-day volatility (persistence), ranked 0-100 | GARCH/EWMA gains were not confirmed |
| NFT floor risk | 30-day volatility of the raw floor | EWMA approval withdrawn after review |
| NFT item fair value | Pooled LightGBM model, refit monthly (Lil Pudgys: baseline B2) | Passed a one-shot sealed test: median error 2.9% vs 3.5% for the floor baseline |

The full reasoning, with numbered decisions, is in [ml/docs/STATUS.md](ml/docs/STATUS.md) and
[ml/docs/DECISIONS.md](ml/docs/DECISIONS.md).

---

## Architecture

```
            ┌──────────────┐
            │   frontend   │  React 19 + Vite + Tailwind      :5173
            └──────┬───────┘
                   │ HTTP
            ┌──────▼───────┐        ┌───────────────────┐
            │   backend    │──HTTP─▶│        ml         │  FastAPI      :8001
            │   FastAPI    │        │ predict/risk/NFT  │
            │    :8000     │        └─────────┬─────────┘
            │              │                  │ ml-data volume
            │ imports:     │        ┌─────────▼─────────┐
            │  aai_engine  │        │ ml-refresh        │  daily 00:05 UTC (Binance)
            │  sentiment_  │        │ ml-nft-refresh    │  daily 00:10 UTC (OpenSea,
            │   engine     │        └───────────────────┘   Alchemy) + monthly refit
            │  db, shared  │
            └──────┬───────┘
                   │
            ┌──────▼───────┐
            │   MongoDB    │  :27017
            └──────────────┘
```

| Folder | What it is |
|---|---|
| [frontend/](frontend/) | React 19 SPA (Vite, Tailwind, shadcn/Radix, react-router) |
| [backend/](backend/) | FastAPI app: auth, assets, portfolio, watchlists, alerts, NFT, sentiment, risk, AAI routes |
| [ml/](ml/) | ML service, data pipelines, models, evaluation harness and reports ([ml/README.md](ml/README.md)) |
| [sentiment_engine/](sentiment_engine/) | RSS + CoinMarketCap collectors, VADER/FinBERT NLP, blended sentiment ([README](sentiment_engine/README.md)) |
| [aai_engine/](aai_engine/) | The AAI formula |
| [db/](db/) | MongoDB connection, indexes and seed scripts |
| [shared/](shared/) | Code shared by backend and engines |

The backend imports `sentiment_engine`, `aai_engine`, `db` and `shared` directly (not over HTTP), so its
Docker image is built from the repo root.

---

## Quick start (Docker)

Requirements: Docker Desktop, and outbound HTTPS to Binance, OpenSea and Alchemy for live data.

```bash
cp .env.example .env          # fill in the keys you have (see below)
docker compose up --build
```

| URL | |
|---|---|
| http://localhost:5173 | Frontend |
| http://localhost:8000/docs | Backend API docs |
| http://localhost:8001/docs | ML service API docs |

Seed the local database with demo assets, prices, NFTs and a demo user:

```bash
python db/seed_all.py
```

Seeds refuse to write to a remote MongoDB unless given `--allow-remote`.

The first build is slow (10-20 min) because the backend installs `torch` and `transformers` for FinBERT.
More detail, including the production frontend build and hot reload, is in [DOCKER.md](DOCKER.md).

### Environment variables

See [.env.example](.env.example). The main ones:

| Variable | Used for |
|---|---|
| `CMC_API_KEY` | CoinMarketCap market signals (sentiment) |
| `OPENSEA_API_KEY`, `ALCHEMY_API_KEY` | NFT floor, sales and trait data |
| `JWT_SECRET` | Signing login tokens (required for any shared deployment) |
| `SMTP_*` | Verification and reset emails (leave `SMTP_HOST` empty in dev: links are logged instead) |
| `BACKEND_MONGO_URI` | Point the backend container at a database other than the local `mongodb` service |

---

## Tests

```powershell
python -m pytest ml -q                                                              # ML
docker exec -w /app/backend altinvest-backend python -m pytest tests -q -p no:cacheprovider   # backend
cd frontend; npm test                                                               # frontend
```

The ML suite needs `ml/requirements.txt` (plus `ml/requirements-train.txt` for the training/evaluation tests).

---

## ML methodology, in short

- **Data**: Binance daily OHLCV for crypto; OpenSea floors and sales plus Alchemy traits for NFTs, with
  frozen, hashed snapshots for evaluation.
- **Evaluation**: chronological splits with a **sealed test set**, expanding-window walk-forward with an
  embargo, at most 4 declared configs per model type, and approval only when a paired block-bootstrap 95% CI
  of the gain over the baseline is above zero.
- **Every phase** has a write-up in [ml/docs/phases/](ml/docs/phases/), and every protocol choice is an
  append-only decision in [ml/docs/DECISIONS.md](ml/docs/DECISIONS.md).

Further reading: [ARCHITECTURE](ml/docs/ARCHITECTURE.md) · [CONTRACT](ml/docs/CONTRACT.md) ·
[CONTRACT_NFT](ml/docs/CONTRACT_NFT.md) · [EVALUATION](ml/docs/EVALUATION.md) ·
[GLOSSARY](ml/docs/GLOSSARY.md).

---

## Project status

The latest phase, Phase 10 (NFTs), is complete and merged into `main`. Open items are tracked in
the backlog section of [ml/docs/STATUS.md](ml/docs/STATUS.md).

AltInvest is a final-year (LY) project at Somaiya. It is for analysis and education only and is not
financial advice.
