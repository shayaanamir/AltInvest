# AltInvest — Sentiment Engine

The **AltInvest Sentiment Engine** is a high-performance Python application that parses RSS feeds, runs natural language processing (NLP) model ensembles on crypto-related news, collects market metrics from CoinMarketCap (CMC), and calculates a blended sentiment score for alternative assets.

---

## Key Features

*   **NLP Ensemble:** Integrates VADER (fast, rules-based) and FinBERT (heavy, financial context-aware) to score news headlines.
*   **Parallel Collectors:** Concurrent fetching for RSS feeds and CMC market signals to minimize network latency.
*   **Blended Scoring:** Combines news sentiment (NLP) with market dynamics (price, volume, and dominance signals).
*   **Caching & Resiliency:** Uses a MongoDB cache with a built-in **Circuit Breaker** to prevent performance degradation when the database is unreachable.

---

## 1. Local Setup (Without Docker)

Follow these steps to configure the virtual environment and run the sentiment engine standalone on your host machine.

### Prerequisites
*   Python 3.10+ (recommended 3.11/3.12)
*   CUDA-enabled GPU (optional, but highly recommended for fast FinBERT inference)

### Installation Steps

1.  **Navigate to the Sentiment Engine Directory:**
    ```bash
    cd sentiment_engine
    ```

2.  **Create & Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    # On Linux/macOS:
    source venv/bin/activate
    ```

3.  **Install PyTorch (CUDA 12.6 enabled):**
    Install PyTorch with GPU support to run deep learning inference on your graphics card:
    ```bash
    pip install torch --index-url https://download.pytorch.org/whl/cu126
    ```
    *Note: For CPU-only environments, install using:*
    `pip install torch --index-url https://download.pytorch.org/whl/cpu`

4.  **Install Remaining Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Standalone CLI

You can run the full pipeline for one or all assets using [main.py](file:///c:/Users/Shaun/OneDrive/Desktop/Somaiya/Year%203/Sem%206/LY%20Project/AltInvest/sentiment_engine/main.py):

*   **Analyse Bitcoin (BTC):**
    ```bash
    python main.py --asset btc
    ```
*   **Analyse All Configured Assets:**
    ```bash
    python main.py --asset all
    ```
*   **Run a Dry-Run (No Database required):**
    Skip writing or querying MongoDB by adding the `--no-save` flag. This outputs the processed JSON result directly to the console:
    ```bash
    python main.py --asset btc --no-save
    ```

> [!TIP]
> **Fast Execution & Model Hot-Loading:**
> Calling `main.py` directly from the CLI forces Python to reload the heavy FinBERT model from disk on every execution.
>
> To avoid this overhead, **leave the backend server running** in a separate terminal:
> ```bash
> cd backend
> python start.py
> ```
> Keeping `start.py` running preserves the FinBERT model hot in RAM/VRAM. You can then trigger fast, sub-second pipeline updates instantly via the API:
> *   **Trigger refresh:** `curl.exe -X POST http://localhost:8000/sentiment/btc/refresh` (or `Invoke-RestMethod -Method Post http://localhost:8000/sentiment/btc/refresh` in PowerShell)
> *   **Get cached output:** `curl http://localhost:8000/sentiment/btc`

---

## 2. Running with Docker (Recommended)

When running AltInvest inside Docker, the sentiment engine is automatically loaded and handled within the backend service container.

### Setup and Start

1.  **Navigate to the repository root directory.**
2.  **Run the compose environment:**
    ```bash
    docker compose up --build
    ```
    This spins up MongoDB, the FastAPI backend (with the sentiment engine mounted), the ML prediction service, and the Vite frontend.

### Interacting via API Endpoints

Once the backend is up and running on port `8000`, you can hit its endpoints using curl (or `curl.exe` in PowerShell) to query the sentiment engine:

*   **Get latest sentiment for all active assets:**
    ```bash
    curl http://localhost:8000/sentiment
    ```
*   **Get latest sentiment for a specific asset (BTC):**
    ```bash
    curl http://localhost:8000/sentiment/btc
    ```
*   **Get 7-day historical sentiment for chart rendering:**
    ```bash
    curl "http://localhost:8000/sentiment/btc/history?days=7"
    ```
*   **Force rerun the pipeline (bypassing cached data):**
    ```bash
    curl.exe -X POST http://localhost:8000/sentiment/btc/refresh
    ```

---

## Configuration & Environment Variables

Key settings can be overridden using environment variables or a `.env` file placed in the `sentiment_engine` folder:

*   `CMC_API_KEY`: Your CoinMarketCap Pro API Key.
*   `MONGO_URI`: Connection string for MongoDB (defaults to `mongodb://localhost:27017`).
*   `MONGO_DB`: Name of the MongoDB database (defaults to `altinvest`).
