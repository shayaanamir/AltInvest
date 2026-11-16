"""
utils/config.py
All configuration, constants, and environment variables for the sentiment engine.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Environment ───────────────────────────────────────────────────────────────
# Market data needs no API key: CoinGecko's public API and Binance's public klines are keyless.

MONGO_URI   = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# One database for the whole app (audit G-18): the backend's MONGO_DB_NAME. MONGO_DB is the engine's old
# variable, still honoured when MONGO_DB_NAME is unset; the default matches docker-compose's.
def resolve_db_name(env=os.environ) -> str:
    return env.get("MONGO_DB_NAME") or env.get("MONGO_DB") or "aaip_db"


MONGO_DB    = resolve_db_name()

# ── Asset Definitions ─────────────────────────────────────────────────────────
# Maps internal asset_id → how to find the asset in market data and in RSS articles.
#
#   symbol          Current ticker, for display/logging only.
#   coingecko_id    CoinGecko's stable coin id: what the market and trending lookups use. A symbol isn't
#                   unique on CoinGecko (and can change: MATIC became POL), the id is.
#   binance_symbol  The asset's USDT pair on Binance, for the 24h volume change (CoinGecko's markets
#                   endpoint gives the volume but not its change).
#   names           Full names / phrases that are unambiguous on their own. Matched
#                   case-insensitively on word boundaries, in the title or the body.
#   tickers         Ticker symbols. A "$TICKER" cashtag always matches. A bare ticker matches
#                   case-insensitively unless the asset is marked ambiguous_ticker.
#   ambiguous_ticker  The ticker is also an everyday word or acronym (link, near, uni, atom,
#                   dot, sol, ada, pol), so a bare ticker only counts when it is written in
#                   UPPERCASE in the article TITLE (e.g. "LINK jumps 10%", not "click the link").
#   exclude_names   Phrases of a DIFFERENT coin that contain this coin's name ("Ethereum Classic"). They are
#                   removed from the title and text before matching, so "Ethereum Classic forecast" is not
#                   Ethereum news but "Ethereum and Ethereum Classic rally" still is.
#
# Deliberately NOT keywords: generic terms like "defi", "oracle", "ibc", "shiba" (a different
# coin), "ether" (a chemical), or bare "binance" (exchange news isn't BNB news).
#
# Asset ids are kept stable for storage/API compatibility, which is why "matic" is the id of the
# token that has been called POL since the Sept 2024 migration. Both names match its articles.
# (backend/controllers/market_data_controller.py SOURCES has the same ids; a backend test keeps them equal.)

ASSETS = {
    "btc": {
        "symbol": "BTC",
        "coingecko_id": "bitcoin",
        "binance_symbol": "BTCUSDT",
        "names": ["bitcoin", "satoshi nakamoto"],
        "tickers": ["btc"],
        "exclude_names": ["bitcoin cash", "bitcoin sv", "bitcoin gold"],
    },
    "eth": {
        "symbol": "ETH",
        "coingecko_id": "ethereum",
        "binance_symbol": "ETHUSDT",
        "names": ["ethereum", "vitalik buterin"],
        "tickers": ["eth"],
        "exclude_names": ["ethereum classic"],
    },
    "sol": {
        "symbol": "SOL",
        "coingecko_id": "solana",
        "binance_symbol": "SOLUSDT",
        "names": ["solana"],
        "tickers": ["sol"],
        "ambiguous_ticker": True,
    },
    "bnb": {
        "symbol": "BNB",
        "coingecko_id": "binancecoin",
        "binance_symbol": "BNBUSDT",
        "names": ["bnb chain", "binance coin", "binance smart chain"],
        "tickers": ["bnb"],
    },
    "xrp": {
        "symbol": "XRP",
        "coingecko_id": "ripple",
        "binance_symbol": "XRPUSDT",
        "names": ["xrp ledger", "ripple labs"],
        "tickers": ["xrp", "xrpl"],
    },
    "ada": {
        "symbol": "ADA",
        "coingecko_id": "cardano",
        "binance_symbol": "ADAUSDT",
        "names": ["cardano"],
        "tickers": ["ada"],
        "ambiguous_ticker": True,   # also the Americans with Disabilities Act
    },
    "avax": {
        "symbol": "AVAX",
        "coingecko_id": "avalanche-2",
        "binance_symbol": "AVAXUSDT",
        "names": ["avalanche"],
        "tickers": ["avax"],
    },
    "doge": {
        "symbol": "DOGE",
        "coingecko_id": "dogecoin",
        "binance_symbol": "DOGEUSDT",
        "names": ["dogecoin"],
        "tickers": ["doge"],
    },
    "dot": {
        "symbol": "DOT",
        "coingecko_id": "polkadot",
        "binance_symbol": "DOTUSDT",
        "names": ["polkadot", "parachain"],
        "tickers": ["dot"],
        "ambiguous_ticker": True,
    },
    "link": {
        "symbol": "LINK",
        "coingecko_id": "chainlink",
        "binance_symbol": "LINKUSDT",
        "names": ["chainlink"],
        "tickers": ["link"],
        "ambiguous_ticker": True,
    },
    "matic": {
        "symbol": "POL",            # renamed from MATIC; same token
        "coingecko_id": "polygon-ecosystem-token",
        "binance_symbol": "POLUSDT",
        "names": ["polygon", "polygon ecosystem token"],
        "tickers": ["matic", "pol"],
        "ambiguous_ticker": True,   # "pol" is also an everyday abbreviation (politics, policy)
    },
    "uni": {
        "symbol": "UNI",
        "coingecko_id": "uniswap",
        "binance_symbol": "UNIUSDT",
        "names": ["uniswap"],
        "tickers": ["uni"],
        "ambiguous_ticker": True,
    },
    "ltc": {
        "symbol": "LTC",
        "coingecko_id": "litecoin",
        "binance_symbol": "LTCUSDT",
        "names": ["litecoin"],
        "tickers": ["ltc"],
    },
    "atom": {
        "symbol": "ATOM",
        "coingecko_id": "cosmos",
        "binance_symbol": "ATOMUSDT",
        "names": ["cosmos hub", "cosmos network", "cosmos sdk"],
        "tickers": ["atom"],
        "ambiguous_ticker": True,
    },
    "near": {
        "symbol": "NEAR",
        "coingecko_id": "near",
        "binance_symbol": "NEARUSDT",
        "names": ["near protocol"],
        "tickers": ["near"],
        "ambiguous_ticker": True,
    },
}

# ── Per-coin news search (Google News RSS, collectors/news_search.py) ─────────
# The search text for each coin; "when:3d" (the article age limit) is added. Results still have to name the
# coin (ASSETS names / tickers above), so a loose query only costs a few discarded results. An asset with no
# entry here simply gets the fixed publisher feeds.
NEWS_SEARCH_QUERIES = {
    "btc":   'Bitcoin',
    "eth":   'Ethereum',
    "sol":   'Solana',
    "bnb":   '"BNB Chain" OR "Binance Coin" OR BNB',
    "xrp":   'XRP OR "XRP Ledger"',
    "ada":   'Cardano',
    "avax":  'Avalanche AVAX crypto',
    "doge":  'Dogecoin',
    "dot":   'Polkadot',
    "link":  'Chainlink',
    "matic": 'Polygon blockchain',     # bare "Polygon" returns the gaming site Polygon.com; "POL" returns price pages
    "uni":   'Uniswap',
    "ltc":   'Litecoin',
    "atom":  '"Cosmos Hub" OR "Cosmos blockchain"',
    "near":  '"NEAR Protocol"',
}

# ── RSS Feed Sources ───────────────────────────────────────────────────────────
# Each source has a url, a display name, and a trust_weight (higher = more trusted).
# Fetched through collectors/feed_cache.py: once per cache period for all assets, with a real User-Agent.

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
        # The old /.rss/full/ URL answers 403 to every client; /feed works (checked 2026-11-16) but also
        # rejects the default python-requests User-Agent, which collectors/feed_cache.py replaces.
        "url": "https://bitcoinmagazine.com/feed",
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

# ── Market data (CoinGecko + Binance, both keyless) ───────────────────────────
# Replaced CoinMarketCap, whose key ran out of credits (429) and whose plan has no trending endpoint (403).
# One batched CoinGecko /coins/markets call covers every asset; /global and /search/trending are one call each.

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
MARKET_HTTP_TIMEOUT = 10  # seconds

# How long a fetched market response is reused across assets and pipeline runs.
MARKET_CACHE_TTL_SECONDS = 300

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
# Final score = news_nlp_weight * nlp_score + market_signal_weight * market_score.
# When there is no usable market score the reading is news only, not news blended with a neutral 0.5.

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

# History rows carry `ts` (a real date, next to the ISO-string `timestamp`) and expire this long after it
# through a TTL index (audit G-22). Longer than the longest window the API serves (90 days). Must match
# db/indexes.py, which creates the same index; a test checks they agree.
SENTIMENT_HISTORY_TTL_SECONDS = 120 * 24 * 60 * 60
