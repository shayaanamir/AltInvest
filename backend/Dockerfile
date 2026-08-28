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

# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 1000 --retries 10 -r backend-requirements.txt

COPY sentiment_engine/requirements.txt ./sentiment-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 1000 --retries 10 -r sentiment-requirements.txt

COPY backend/         ./backend/
COPY shared/          ./shared/
COPY aai_engine/      ./aai_engine/
COPY sentiment_engine/ ./sentiment_engine/
COPY db/              ./db/

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
