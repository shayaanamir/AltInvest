import path_setup  # noqa: F401 — must be first, fixes sys.path before any local imports

import threading
import traceback

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from utils.http_errors import (
    DB_UNAVAILABLE_MESSAGE, ENGINE_UNAVAILABLE_MESSAGE, INTERNAL_ERROR_MESSAGE, EngineUnavailable, redact,
)
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    health,
    auth,
    assets,
    prediction,
    sentiment,
    risk,
    aai,
    dashboard,
    portfolio,
    watchlists,
    alerts,
    notifications,
    nft,
    discover,
    compare,
    search,
    profile,
    settings,
    fx,
)

_log = logging.getLogger("api")

app = FastAPI(
    title="AAIP Backend",
    description="Alternative Asset Intelligence Platform API",
    version="1.0.0",
)

# ── Error handling ───────────────────────────────────────────────────────────
# One rule for every route: details go to the server log, the client gets a fixed message.
#   database unreachable / failing (any pymongo error)  -> 503 "Unable to reach the database right now."
#   sentiment engine not installed                      -> 503
#   anything else unexpected                            -> 500, generic message
# The catch-all is registered before CORS so it sits inside it and the 500 still carries CORS
# headers (otherwise the browser reports it as a network failure).

@app.exception_handler(PyMongoError)
async def _database_error(request: Request, exc: PyMongoError):
    _log.error("Database error on %s %s: %s: %s", request.method, request.url.path, type(exc).__name__, redact(exc))
    return JSONResponse(status_code=503, content={"detail": DB_UNAVAILABLE_MESSAGE})


@app.exception_handler(EngineUnavailable)
async def _engine_unavailable(request: Request, exc: EngineUnavailable):
    _log.error("Sentiment engine unavailable on %s %s: %s", request.method, request.url.path, redact(exc))
    return JSONResponse(status_code=503, content={"detail": ENGINE_UNAVAILABLE_MESSAGE})


@app.middleware("http")
async def _unexpected_error(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        # Full traceback for debugging, with any credentials in the message masked.
        _log.error("Unhandled error on %s %s\n%s", request.method, request.url.path,
                   redact("".join(traceback.format_exception(exc))))
        return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_MESSAGE})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to ["http://localhost:3000"] once frontend is running
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(prediction.router)
app.include_router(sentiment.router)
app.include_router(risk.router)
app.include_router(aai.router)
app.include_router(dashboard.router)
app.include_router(portfolio.router)
app.include_router(watchlists.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(nft.router)
app.include_router(discover.router)
app.include_router(compare.router)
app.include_router(search.router)
app.include_router(profile.router)
app.include_router(settings.router)
app.include_router(fx.router)


def _warmup_sentiment_engine() -> None:
    """
    Loads FinBERT/PyTorch into memory once, in a background thread, so the
    first real /sentiment request doesn't pay the ~10s-2min model-load cost.
    Mirrors sentiment_engine/main.py's warmup_pipeline() call for the CLI.
    Failures are swallowed here — routes/sentiment.py's own lazy-import
    guards still handle a missing/broken engine at request time.
    """
    try:
        from sentiment_engine.nlp.finbert_scorer import warmup_pipeline, get_load_error
        if warmup_pipeline():
            print("[startup] Sentiment engine (FinBERT) warmed up successfully.")
        else:
            print(
                f"[startup] FinBERT failed to load ({get_load_error()}); "
                "sentiment will be scored with VADER only until it loads."
            )
    except Exception as exc:
        print(f"[startup] Sentiment engine warmup skipped/failed: {exc}")


@app.on_event("startup")
def on_startup():
    # 1. Warm up FinBERT so the first /sentiment request bears no model-load cost.
    threading.Thread(target=_warmup_sentiment_engine, daemon=True).start()

    # 2. Background scheduler: re-runs the full sentiment pipeline for all 15
    #    active assets every 15 minutes, keeping MongoDB cache always fresh.
    #    Starts 90 s after launch (after FinBERT has loaded) then loops forever.
    from routes.sentiment import _run_scheduler
    threading.Thread(target=_run_scheduler, daemon=True, name="sentiment-scheduler").start()

    # 3. Daily portfolio snapshots (Dashboard 1W/1M/3M/1Y performance chart).
    from controllers.snapshot_controller import run_snapshot_scheduler
    threading.Thread(target=run_snapshot_scheduler, daemon=True, name="portfolio-snapshots").start()

    # 4. USD exchange rates for the display-currency setting (Frankfurter / ECB), every 6 hours.
    from controllers.fx_controller import run_fx_scheduler
    threading.Thread(target=run_fx_scheduler, daemon=True, name="fx-rates").start()


@app.get("/")
def root():
    return {"message": "AAIP API is running. Visit /docs for the full API reference."}