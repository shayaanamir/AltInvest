# Build from ml/ directory:
#   docker build -t altinvest-ml ./ml
#
# NOTE on image size/build time: prophet pulls in cmdstanpy, which compiles
# a small C++ toolchain (cmdstan) the first time it's used, and tensorflow
# is large on its own. This image will be several GB and the first build can
# take 10-20+ minutes. That's expected for this stack, not a bug.

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        make \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/ml

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-build cmdstan at image build time instead of on first request.
# If this fails on your platform, comment it out - prophet will build it
# lazily on first use instead (just makes the first /prediction call slow).
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()" || true

# Copy the rest of ml/ - this includes data/raw/*.csv and
# models/artifacts/*.pkl|*.keras, which are read at REQUEST time
# (not just training time), so they must ship in the image.
COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.prediction_service:app", "--host", "0.0.0.0", "--port", "8001"]
