import path_setup  # noqa: F401 — must be first, fixes sys.path before any local imports

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


@app.get("/")
def root():
    return {"message": "AAIP API is running. Visit /docs for the full API reference."}