# syntax=docker/dockerfile:1
# Build this from the REPO ROOT, not from backend/:
#   docker build -f backend/Dockerfile -t altinvest-backend .
# (docker-compose.yml and docker-compose.prod.yml at the repo root already do this correctly)
#
# Why root context? backend/path_setup.py puts the project root AND
# sentiment_engine/ on sys.path so that backend code can do
# `from aai_engine.aai import ...`,
# `from db.queries import ...`, and (lazily) `from aggregator.sentiment_aggregator
# import run_pipeline` / `from storage.mongo_handler import ...` /
# `from utils.config import ASSETS` which live inside sentiment_engine/.
#
# The same image serves development (docker-compose.yml bind-mounts the source over /app and overrides the
# command) and production (docker-compose.prod.yml runs it as built). It runs as the unprivileged user `app`.

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# One fully pinned file (audit N-02 / G-17): the backend's and the sentiment engine's packages with every
# transitive dependency, so the image can't end up with two files' versions fighting each other.
COPY backend/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 1000 --retries 10 -r requirements.txt

# Unprivileged user (audit G-11). Its home holds the Hugging Face cache (FinBERT is downloaded on first use);
# docker-compose.prod.yml keeps that cache on a volume so a restart doesn't download the model again.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app

COPY backend/         ./backend/
COPY shared/          ./shared/
COPY aai_engine/      ./aai_engine/
COPY sentiment_engine/ ./sentiment_engine/
COPY db/              ./db/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

USER app
WORKDIR /app/backend
EXPOSE 8000

# /health pings the database: 200 when it answers, 503 when it doesn't (routes/health.py).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# --proxy-headers: behind nginx (docker-compose.prod.yml) the client address comes from X-Forwarded-For, for the
# hosts in FORWARDED_ALLOW_IPS. Worker processes: WEB_CONCURRENCY (uvicorn reads it; default 1).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header"]
