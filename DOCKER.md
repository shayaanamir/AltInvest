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
cp .env.example .env        # optional, fill in CMC_API_KEY if you have one
docker compose up --build
```

Then visit:
- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- ML service docs: http://localhost:8001/docs

To stop: `docker compose down` (add `-v` to also wipe the volumes: Mongo's data and the ML service's
`ml-data`; the `ml` service re-fetches its data from Binance at the next start).

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
   `sentiment_engine/utils/config.py` read `MONGO_URI`, `MONGO_DB_NAME` /
   `MONGO_DB`, and `CMC_API_KEY` via `os.getenv(...)`. These are set
   directly in `docker-compose.yml`'s `environment:` block for `backend`,
   pointing at the `mongodb` service by its container name — no `.env`
   file inside `backend/` is needed for Docker (that `.env` file is only
   used when running the backend outside Docker).

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
