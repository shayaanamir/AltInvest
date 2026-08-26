import path_setup  # noqa: F401 — must be first, fixes sys.path before any local imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import assets, prediction, sentiment, risk, aai, health, auth

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


@app.get("/")
def root():
    return {"message": "AAIP API is running. Visit /docs for the full API reference."}