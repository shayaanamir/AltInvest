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
# Maps internal asset_id → how to find the asset on CoinMarketCap and in RSS articles.
#
#   cmc_id          CoinMarketCap's stable id — what quote and trending lookups use. A symbol
#                   isn't unique on CMC (and can change: MATIC became POL), the id is.
#   cmc_symbol      Current ticker, for display/logging only.
#   names           Full names / phrases that are unambiguous on their own. Matched
#                   case-insensitively on word boundaries, in the title or the body.
#   tickers         Ticker symbols. A "$TICKER" cashtag always matches. A bare ticker matches
#                   case-insensitively unless the asset is marked ambiguous_ticker.
#   ambiguous_ticker  The ticker is also an everyday word or acronym (link, near, uni, atom,
#                   dot, sol, ada, pol), so a bare ticker only counts when it is written in
#                   UPPERCASE in the article TITLE (e.g. "LINK jumps 10%", not "click the link").
#
# Deliberately NOT keywords: generic terms like "defi", "oracle", "ibc", "shiba" (a different
# coin), "ether" (a chemical), or bare "binance" (exchange news isn't BNB news).
#
# Asset ids are kept stable for storage/API compatibility, which is why "matic" is the id of the
# token that has been called POL since the Sept 2024 migration. Both names match its articles.

ASSETS = {
    "btc": {
        "cmc_symbol": "BTC",
        "cmc_id": 1,
        "names": ["bitcoin", "satoshi nakamoto"],
        "tickers": ["btc"],
    },
    "eth": {
        "cmc_symbol": "ETH",
        "cmc_id": 1027,
        "names": ["ethereum", "vitalik buterin"],
        "tickers": ["eth"],
    },
    "sol": {
        "cmc_symbol": "SOL",
        "cmc_id": 5426,
        "names": ["solana"],
        "tickers": ["sol"],
        "ambiguous_ticker": True,
    },
    "bnb": {
        "cmc_symbol": "BNB",
        "cmc_id": 1839,
        "names": ["bnb chain", "binance coin", "binance smart chain"],
        "tickers": ["bnb"],
    },
    "xrp": {
        "cmc_symbol": "XRP",
        "cmc_id": 52,
        "names": ["xrp ledger", "ripple labs"],
        "tickers": ["xrp", "xrpl"],
    },
    "ada": {
        "cmc_symbol": "ADA",
        "cmc_id": 2010,
        "names": ["cardano"],
        "tickers": ["ada"],
        "ambiguous_ticker": True,   # also the Americans with Disabilities Act
    },
    "avax": {
        "cmc_symbol": "AVAX",
        "cmc_id": 5805,
        "names": ["avalanche"],
        "tickers": ["avax"],
    },
    "doge": {
        "cmc_symbol": "DOGE",
        "cmc_id": 74,
        "names": ["dogecoin"],
        "tickers": ["doge"],
    },
    "dot": {
        "cmc_symbol": "DOT",
        "cmc_id": 6636,
        "names": ["polkadot", "parachain"],
        "tickers": ["dot"],
        "ambiguous_ticker": True,
    },
    "link": {
        "cmc_symbol": "LINK",
        "cmc_id": 1975,
        "names": ["chainlink"],
        "tickers": ["link"],
        "ambiguous_ticker": True,
    },
    "matic": {
        "cmc_symbol": "POL",        # renamed from MATIC; same CMC id
        "cmc_id": 3890,
        "names": ["polygon", "polygon ecosystem token"],
        "tickers": ["matic", "pol"],
        "ambiguous_ticker": True,   # "pol" is also an everyday abbreviation (politics, policy)
    },
    "uni": {
        "cmc_symbol": "UNI",
        "cmc_id": 7083,
        "names": ["uniswap"],
        "tickers": ["uni"],
        "ambiguous_ticker": True,
    },
    "ltc": {
        "cmc_symbol": "LTC",
        "cmc_id": 2,
        "names": ["litecoin"],
        "tickers": ["ltc"],
    },
    "atom": {
        "cmc_symbol": "ATOM",
        "cmc_id": 3794,
        "names": ["cosmos hub", "cosmos network", "cosmos sdk"],
        "tickers": ["atom"],
        "ambiguous_ticker": True,
    },
    "near": {
        "cmc_symbol": "NEAR",
        "cmc_id": 6535,
        "names": ["near protocol"],
        "tickers": ["near"],
        "ambiguous_ticker": True,
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

# The current score is compared with the stored reading closest to
# TREND_LOOKBACK_HOURS ago, and only if one exists within TREND_TOLERANCE_HOURS of
# that point. Otherwise the trend is "unknown" rather than a guess.
TREND_LOOKBACK_HOURS  = 24
TREND_TOLERANCE_HOURS = 6

# ── MongoDB Collections ───────────────────────────────────────────────────────

COLLECTION_SENTIMENT        = "sentiment"
COLLECTION_RAW_ARTICLES     = "raw_articles"
COLLECTION_SENTIMENT_HISTORY = "sentiment_history"
