"""
utils/config.py
All configuration, constants, and environment variables for the sentiment engine.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────

CMC_API_KEY = os.getenv("CMC_API_KEY")
if not CMC_API_KEY:
    import warnings
    warnings.warn(
        "CMC_API_KEY is not set. CoinMarketCap requests will fail and the "
        "pipeline will fall back to neutral market signals for every asset."
    )
MONGO_URI   = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB    = os.getenv("MONGO_DB", "altinvest")

# ── Asset Definitions ─────────────────────────────────────────────────────────
# Maps internal asset_id → CMC symbol + search keywords for RSS filtering

ASSETS = {
    "btc": {
        "cmc_symbol": "BTC",
        "cmc_id": 1,
        "keywords": ["bitcoin", "btc", "satoshi"],
    },
    "eth": {
        "cmc_symbol": "ETH",
        "cmc_id": 1027,
        "keywords": ["ethereum", "eth", "ether", "vitalik"],
    },
    "sol": {
        "cmc_symbol": "SOL",
        "cmc_id": 5426,
        "keywords": ["solana", "sol"],
    },
    "bnb": {
        "cmc_symbol": "BNB",
        "cmc_id": 1839,
        "keywords": ["binance", "bnb"],
    },
    "xrp": {
        "cmc_symbol": "XRP",
        "cmc_id": 52,
        "keywords": ["ripple", "xrp"],
    },
}

# ── RSS Feed Sources ───────────────────────────────────────────────────────────
# Each source has a url, a display name, and a trust_weight (higher = more trusted)

RSS_FEEDS = [
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "trust_weight": 1.0,
    },
    {
        "name": "CryptoSlate",
        "url": "https://cryptoslate.com/feed/",
        "trust_weight": 0.9,
    },
    {
        "name": "Decrypt",
        "url": "https://decrypt.co/feed",
        "trust_weight": 0.9,
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "trust_weight": 0.95,
    },
    {
        "name": "BeInCrypto",
        "url": "https://beincrypto.com/feed/",
        "trust_weight": 0.8,
    },
    {
        "name": "The Block",
        "url": "https://www.theblock.co/rss.xml",
        "trust_weight": 1.0,
    },
    {
        "name": "Bitcoin Magazine",
        "url": "https://bitcoinmagazine.com/.rss/full/",
        "trust_weight": 0.85,
    },
    {
        "name": "Blockworks",
        "url": "https://blockworks.co/feed",
        "trust_weight": 0.9,
    },
    {
        "name": "NewsBTC",
        "url": "https://www.newsbtc.com/feed/",
        "trust_weight": 0.75,
    },
    {
        "name": "AMBCrypto",
        "url": "https://ambcrypto.com/feed/",
        "trust_weight": 0.75,
    },
]

# ── CoinMarketCap API ──────────────────────────────────────────────────────────

CMC_BASE_URL   = "https://pro-api.coinmarketcap.com/v1"
CMC_TIMEOUT    = 10  # seconds

# ── NLP Settings ──────────────────────────────────────────────────────────────

# FinBERT model (downloads once, cached by HuggingFace)
FINBERT_MODEL = "ProsusAI/finbert"

# Max tokens FinBERT can handle
FINBERT_MAX_TOKENS = 512

# Blend weights for ensemble: VADER is fast but generic, FinBERT understands finance
VADER_WEIGHT   = 0.35
FINBERT_WEIGHT = 0.65

# ── Recency Decay ─────────────────────────────────────────────────────────────
# Articles decay in weight exponentially.
# After HALF_LIFE_HOURS, an article is worth 50% of a fresh one.

RECENCY_HALF_LIFE_HOURS = 12

# Articles older than this are discarded entirely
MAX_ARTICLE_AGE_HOURS = 72

# ── Aggregation Weights ───────────────────────────────────────────────────────
# Final score = news_nlp_weight * nlp_score + market_signal_weight * cmc_score

NEWS_NLP_WEIGHT     = 0.70
MARKET_SIGNAL_WEIGHT = 0.30

# ── Confidence Thresholds ─────────────────────────────────────────────────────
# How many articles are needed for a "high confidence" score

CONFIDENCE_LOW_THRESHOLD    = 5
CONFIDENCE_MEDIUM_THRESHOLD = 15
CONFIDENCE_HIGH_THRESHOLD   = 30

# ── Trend Detection ───────────────────────────────────────────────────────────
# Minimum score delta between current and 24h-ago to declare a trend

TREND_DELTA_THRESHOLD = 0.05

# ── MongoDB Collections ───────────────────────────────────────────────────────

COLLECTION_SENTIMENT        = "sentiment"
COLLECTION_RAW_ARTICLES     = "raw_articles"
COLLECTION_SENTIMENT_HISTORY = "sentiment_history"
