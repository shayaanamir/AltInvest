# AltInvest — Sentiment Engine

The **AltInvest Sentiment Engine** is a high-performance Python application that parses RSS feeds, runs natural language processing (NLP) model ensembles on crypto-related news, collects market metrics from CoinGecko and Binance (no API key needed), and calculates a blended sentiment score for alternative assets.

---

## Key Features

*   **NLP Ensemble:** Integrates VADER (fast, rules-based) and FinBERT (heavy, financial context-aware) to score news headlines.
*   **Shared, polite collectors:** every RSS feed is downloaded at most once per 10 minutes for all assets together (conditional requests, a real User-Agent, cool-down after a 429, last good copy served meanwhile: `collectors/feed_cache.py`), and one CoinGecko call covers every asset's market data (`collectors/market_collector.py`).
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

*   Market data (CoinGecko, Binance) and the news feeds need no key. (`CMC_API_KEY` is no longer read.)
*   `MONGO_URI`: Connection string for MongoDB (defaults to `mongodb://localhost:27017`).
*   `MONGO_DB`: Name of the MongoDB database (defaults to `altinvest`).

## 3. NFT News Sentiment (`nft_sentiment/`)

A separate pipeline for the 7 tracked NFT collections (`ml/config.py` `NFT_SLUGS`) plus the NFT market
as a whole (slug `nft-market`). It reuses the crypto collector's matching helpers and VADER + FinBERT as a
fallback, but nothing in the crypto pipeline calls it, and its collections are not in `ASSETS`.

**Why it differs from the crypto pipeline**

| | Crypto | NFT |
|---|---|---|
| News source | 10 broad RSS feeds | Google News + Bing News searches per collection, plus the broad feeds |
| Scorer | VADER + FinBERT | LLM on Groq (`openai/gpt-oss-120b`), VADER + FinBERT fallback |
| Relevance | name match | name match, then the LLM drops articles not really about the collection |
| Duplicates | title-word overlap | the LLM links rewordings of one story; each story counts once |
| Market signal | CoinMarketCap | floor change (24h, 7d) and sales pace from `nft_market_data` / `nft_liquidity` |
| Window / half-life | 72h / 12h | 7 days / 48h |

In a live check on 2026-11-16 none of the 311 headlines from the past week in the broad feeds (NFT sites
included) named a tracked collection, OpenSea or even "NFT"; the search feeds found 18 BAYC stories.

**Scoring.** For each article the LLM returns `relevant`, `label` (positive/neutral/negative), `intensity`
(low/medium/high), `same_story_as` and a short `reason`, under a strict JSON schema. The score is derived
from label and intensity (0.3 / 0.6 / 0.9). Article text is treated as untrusted. A collection's articles go
in one request and the verdicts are cached until its article list changes, so quiet collections cost nothing.

**Output.** `sentiment_score` -1..1 = 65% news + 35% market signal (news only when there is no recent ML
market row), confidence from the number of distinct stories (1.0 at 10), trend against ~24h ago.

**Not validated.** There are no human-labelled NFT headlines; the score is a summary of recent news and
trading, not a forecast. `python -m nft_sentiment.compare` measures scorer *agreement* on live headlines
(`data/reports/nft_scorer_agreement.json`). On 2026-11-15 (62 articles): the LLM agreed with itself across two
runs on 93.5% of labels (kappa 0.90) and on 100% of relevance calls; it agreed with VADER + FinBERT on 56% of
the relevant articles (kappa 0.25, score correlation 0.52).

**Running it**

```bash
cd sentiment_engine
python -m nft_sentiment.run --collect-only        # which headlines matched (no LLM call)
python -m nft_sentiment.run --slug azuki          # score and print, nothing saved
python -m pytest tests -q                         # engine tests (no network)
```

In the app, `backend/controllers/nft_sentiment_controller.py` runs every 30 minutes and stores
`nft_sentiment` / `nft_sentiment_history`; `GET /nft/sentiment` and `GET /nft/collections/{slug}/sentiment`
only read. Environment: `GROQ_API_KEY` (without it everything falls back to VADER + FinBERT) and optionally
`NFT_SENTIMENT_MODEL`.
