import path_setup  # noqa: F401 — must be first, fixes sys.path before any local imports

import threading

from fastapi import FastAPI
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
)

app = FastAPI(
    title="AAIP Backend",
    description="Alternative Asset Intelligence Platform API",
    version="1.0.0",
)

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


def _warmup_sentiment_engine() -> None:
    """
    Loads FinBERT/PyTorch into memory once, in a background thread, so the
    first real /sentiment request doesn't pay the ~10s-2min model-load cost.
    Mirrors sentiment_engine/main.py's warmup_pipeline() call for the CLI.
    Failures are swallowed here — routes/sentiment.py's own lazy-import
    guards still handle a missing/broken engine at request time.
    """
    try:
        from sentiment_engine.nlp.finbert_scorer import warmup_pipeline
        warmup_pipeline()
        print("[startup] Sentiment engine (FinBERT) warmed up successfully.")
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


@app.get("/")
def root():
    return {"message": "AAIP API is running. Visit /docs for the full API reference."}