# Build this from the REPO ROOT, not from backend/:
#   docker build -f backend/Dockerfile -t altinvest-backend .
# (docker-compose.yml at the repo root already does this correctly)
#
# Why root context? backend/path_setup.py puts the project root AND
# sentiment_engine/ on sys.path so that backend code can do
# `from shared.mock_data import ...`, `from aai_engine.aai import ...`,
# `from db.queries import ...`, and (lazily) `from aggregator.sentiment_aggregator
# import run_pipeline` / `from storage.mongo_handler import ...` /
# `from utils.config import ASSETS` which live inside sentiment_engine/.

FROM python:3.11-slim

# build-essential needed for a couple of pymongo/transitive C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Install Python deps first (better layer caching) ----
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r backend-requirements.txt

# sentiment_engine is imported directly by backend/routes/sentiment.py and
# backend/controllers/aai_controller.py, so its deps must be installed too.
# NOTE: this pulls in torch + transformers (FinBERT) -> large image (a few GB)
# and a slow first build. See README note in docker-compose.yml if you'd
# rather run without real sentiment scoring for local dev.
COPY sentiment_engine/requirements.txt ./sentiment-requirements.txt
RUN pip install --no-cache-dir -r sentiment-requirements.txt

# ---- Copy source ----
# Layout mirrors the repo root exactly, so path_setup.py's relative
# path math (PROJECT_ROOT = one level above backend/) keeps working.
COPY backend/         ./backend/
COPY shared/          ./shared/
COPY aai_engine/      ./aai_engine/
COPY sentiment_engine/ ./sentiment_engine/
COPY db/              ./db/

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
