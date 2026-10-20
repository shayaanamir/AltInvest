# ML service v2. Build this from the REPO ROOT, like backend/Dockerfile:
#   docker build -f ml/Dockerfile -t altinvest-ml .
# (docker-compose.yml at the repo root already does this correctly)
#
# Serves baselines on :8001 (D27, D33, D35-D37; ml/README.md). No Prophet, TensorFlow or cmdstan, so the
# image is small and builds in a few minutes. Raw CSVs are NOT baked in (.dockerignore): at startup the refresh
# fetches and validates the serving data into /data (mount a volume there), then uvicorn starts. If the refresh
# fails, the API still starts and returns 503 for assets without valid data (D40).

FROM python:3.12-slim

# git only for the test suite: ml/tests/test_gitinfo.py builds a throwaway repo.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ml/requirements.txt ml/requirements.txt
RUN pip install --no-cache-dir --timeout 1000 --retries 10 -r ml/requirements.txt

COPY ml/ ml/

# Serving data directories (D40); never the evaluation snapshot under ml/.
ENV ML_RAW_DIR=/data/raw \
    ML_VALIDATION_DIR=/data/validation \
    PYTHONUNBUFFERED=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4)"

# Refresh once (a failure is logged in /data/validation/refresh_status.json, not fatal), then serve.
# exec makes uvicorn the main process, so `docker stop` reaches it.
CMD ["sh", "-c", "python -m ml.data.refresh; exec uvicorn ml.api.service:app --host 0.0.0.0 --port 8001"]
