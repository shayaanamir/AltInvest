# Running AltInvest with Docker

## Where these files go

Copy these into your repo like this (all at repo root alongside `backend/`, `frontend/`, `ml/`, etc.):

```
AltInvest/
├── docker-compose.yml        <- new
├── .env.example               <- new
├── .dockerignore               <- new
├── backend/
│   └── Dockerfile              <- new
├── ml/
│   └── Dockerfile              <- new
└── frontend/
    ├── Dockerfile               <- new (dev)
    ├── Dockerfile.prod          <- new (prod, optional)
    └── nginx.conf               <- new (used by Dockerfile.prod)
```

## What gets started

| Service    | Port | What it is |
|------------|------|------------|
| `mongodb`  | 27017 | Database used by backend + sentiment engine |
| `backend`  | 8000  | FastAPI app (`backend/main.py`) — assets, prediction, sentiment, risk, aai, health routes |
| `ml`       | 8001  | ML service v2 (`ml/api/service.py`): `/predict/{asset}`, `/risk/{asset}`, `/health` for BTC, ETH, SOL, serving baselines only (see `ml/README.md`). Fetches its own data into the `ml-data` volume at startup; the `ml-refresh` sidecar refreshes it daily at 00:05 UTC. Not called by `backend` automatically yet |
| `frontend` | 5173  | Vite dev server |

## Quick start

```bash
cp .env.example .env        # optional; set GROQ_API_KEY for the NFT sentiment LLM (no key is needed for market data)
docker compose up --build
```

Then visit:
- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- ML service docs: http://localhost:8001/docs

To stop: `docker compose down` (add `-v` to also wipe the volumes: Mongo's data and the ML service's
`ml-data`; the `ml` service re-fetches its data from Binance at the next start).

## First run: fill the database once

**Every machine has its own MongoDB** (the `mongodb` container and its `mongo_data` volume). Git shares code,
never databases, so a fresh clone starts empty and shows tickers instead of names ("BTC", not "Bitcoin"), no
descriptions, no trending list and no themes. The live jobs fill prices and news by themselves; the rest comes
from one command, safe to run again:

```bash
docker exec -w /app/backend altinvest-backend python -m controllers.bootstrap_controller
```

It creates the coin names and colours, the NFT collection details and the live prices and history, runs one news
sentiment pass, builds the insights and themes, and finally fetches every coin's CoinGecko profile (about 6 minutes;
CoinGecko's free tier is slow). It writes no made-up numbers and refuses a non-local database. Add
`--skip profiles` to leave out the slow step, or `--only coins,market` to run just some. Then hard-refresh the browser.

Put your own keys in `.env` first (they are never in git), then `docker compose up -d` (a plain `restart` does not
re-read `.env`): `GROQ_API_KEY` for themes and the NFT sentiment LLM; `OPENSEA_API_KEY` and `ALCHEMY_API_KEY` for the
NFT floor prices and sales, whose first download takes a while. Predictions, risk and AAI for the coins the ML
service does not cover are not set up by this command.

**Upgrading a database that already has portfolio data:** the backend now builds two unique indexes on
`portfolio_holdings` (one row per crypto symbol and per NFT token, per user) so two simultaneous trades can't
create duplicates. If old duplicate rows exist, the index build fails (the backend logs `uniq_user_crypto_symbol` /
`uniq_user_nft_token` under `[indexes] ... failed` and keeps running without it). Merge the duplicates first, then
restart the backend:

```bash
docker exec -w /app altinvest-backend python db/normalize_holdings.py
```

(It merges duplicate crypto rows. A duplicate NFT token row has to be removed by hand.)

## Important things to know before you build

1. **The backend build context is the repo root, not `backend/`.**
   `backend/path_setup.py` puts the project root *and* `sentiment_engine/`
   on `sys.path`, because `backend/controllers/aai_controller.py` and
   `backend/routes/sentiment.py` import `shared`, `aai_engine`, `db`, and
   pieces of `sentiment_engine` (`aggregator`, `storage`, `utils.config`)
   directly — not over HTTP. That's why `docker-compose.yml` builds
   `backend/Dockerfile` with `context: .`. If you ever `docker build` the
   backend manually, do it from the repo root: `docker build -f backend/Dockerfile .`

2. **First build will be slow and the images will be large.** The backend
   image also installs `sentiment_engine/requirements.txt`, which pulls in
   `torch` + `transformers` (for FinBERT). Expect a few GB for the backend
   image and a 10–20 minute first build. The `ml` image is small
   (python:3.12-slim with pandas, scikit-learn and FastAPI; no Prophet or
   TensorFlow) and builds in a few minutes. It needs outbound HTTPS to
   api.binance.com at startup and daily at 00:05 UTC to fetch its data.
   Subsequent builds are cached and much faster.

   If you want a fast local loop and don't need real sentiment scoring
   yet, you can temporarily strip `torch`/`transformers` lines out of
   `sentiment_engine/requirements.txt` for local dev — the backend's
   sentiment routes only import the engine lazily inside each request
   handler, so the app still boots without it (you'll just get errors if
   you actually hit `/sentiment/*`).

3. **`VITE_API_BASE_URL` mismatch note:** `frontend/src/config.js` defaults
   to `http://localhost:5000/api`, but the actual backend runs on `:8000`
   and mounts its routers with **no** `/api` prefix (see `backend/main.py`).
   The compose file sets `VITE_API_BASE_URL=http://localhost:8000` to match
   what the backend actually serves — adjust if you add an `/api` prefix
   later.

4. **Env vars / secrets:** `db/mongo_connection.py` and
   `sentiment_engine/utils/config.py` read `MONGO_URI` and `MONGO_DB_NAME` via `os.getenv(...)`
   (the NFT sentiment also reads `GROQ_API_KEY`). Both use the same database. These are set
   directly in `docker-compose.yml`'s `environment:` block for `backend`,
   pointing at the `mongodb` service by its container name. Outside Docker the repo-root `.env`
   is read as a fallback; it never overrides variables that are already set.
   Before the one-database change the sentiment engine wrote to a separate `altinvest`
   database; copy that data over once with `python db/migrate_sentiment_db.py` (see its docstring).

5. **Vite envs are baked at build time, not run time**, for the
   *production* image (`Dockerfile.prod`). Pass them as `--build-arg`
   (see the comment at the top of that file), not as `docker run -e`.

## Production build (optional)

```bash
docker build -f frontend/Dockerfile.prod \
  --build-arg VITE_API_BASE_URL=https://your-backend-domain \
  -t altinvest-frontend:prod ./frontend

docker run -p 80:80 altinvest-frontend:prod
```

This serves the built static assets via nginx, with an SPA fallback to
`index.html` for `react-router-dom` client-side routes.

## Hot reload

- `backend` runs with `uvicorn --reload`, watching the bind-mounted
  `backend/`, `shared/`, `aai_engine/`, and `db/` folders.
- `ml` has no hot reload: its source is copied into the image (no bind
  mount). After editing `ml/`, run `docker compose up -d --build ml ml-refresh`.
- `frontend` runs the Vite dev server, which already has HMR.

`sentiment_engine/` is bind-mounted into the backend container too, but
isn't in the reload-watch list by default (its heavy import chain makes
frequent restarts painful) — restart `docker compose restart backend`
after editing it.
