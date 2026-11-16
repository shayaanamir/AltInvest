"""
nft_sentiment/config.py

Configuration for the NFT sentiment pipeline. Deliberately separate from utils/config.py
(ASSETS), which drives the crypto lists, AAI and the dashboard: adding NFT collections there
would leak them into all of those.

Environment (read at call time, never at import time, so tests and containers can set them late):
    GROQ_API_KEY          required for the LLM scorer; without it the pipeline falls back to VADER + FinBERT
    NFT_SENTIMENT_MODEL   optional Groq model id (default below)
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── Collections ───────────────────────────────────────────────────────────────
# Keyed by the OpenSea slug used everywhere else (ml/config.py NFT_SLUGS, the nft_* collections).
#
#   names     phrases that identify the collection on their own, matched case-insensitively on
#             word boundaries in the title or body.
#   tickers   cashtag/ticker symbols ("$PENGU" always matches).
#
# A name that merely appears in an article is not enough to score it: the LLM scorer also decides
# whether the article is really about the collection and drops it if not. "yuga labs" is listed on
# both Ape collections because news about the company moves both; "bored ape" and "mutant ape" are
# kept apart, and no bare "ape" is used.
#   google_query  Google News search (supports OR and quotes); the collection's main news source.
#   bing_queries  Bing News searches, one phrase each (Bing's RSS returns nothing for OR queries).
NFT_COLLECTIONS: dict[str, dict] = {
    "boredapeyachtclub": {
        "name": "Bored Ape Yacht Club",
        "names": ["bored ape yacht club", "bored ape", "bored apes", "yuga labs"],
        "tickers": ["bayc"],
        "google_query": '"Bored Ape Yacht Club" OR "Bored Ape" OR BAYC',
        "bing_queries": ['"Bored Ape Yacht Club"'],
    },
    "mutant-ape-yacht-club": {
        "name": "Mutant Ape Yacht Club",
        "names": ["mutant ape yacht club", "mutant ape", "mutant apes", "yuga labs"],
        "tickers": ["mayc"],
        "google_query": '"Mutant Ape Yacht Club" OR "Mutant Ape" OR MAYC',
        "bing_queries": ['"Mutant Ape Yacht Club"'],
    },
    "pudgypenguins": {
        "name": "Pudgy Penguins",
        "names": ["pudgy penguins", "pudgy penguin"],
        "tickers": ["pengu"],          # the PENGU token: its news moves the collection
        # "Pengu" is also a League of Legends character (a TFT headline matched on 2026-11-16), so the
        # bare ticker only counts in UPPERCASE in a title; "$PENGU" always counts.
        "ambiguous_ticker": True,
        "google_query": '"Pudgy Penguins" OR PENGU',
        "bing_queries": ['"Pudgy Penguins"'],
    },
    "lilpudgys": {
        "name": "Lil Pudgys",
        "names": ["lil pudgys", "lil pudgy"],
        "tickers": [],
        "google_query": '"Lil Pudgys" OR "Lil Pudgy"',
        "bing_queries": ['"Lil Pudgys"'],
    },
    "azuki": {
        "name": "Azuki",
        "names": ["azuki", "chiru labs"],
        "tickers": [],
        "google_query": 'Azuki NFT OR "Azuki" anime NFT',
        "bing_queries": ["Azuki NFT"],
    },
    "doodles-official": {
        "name": "Doodles",
        "names": ["doodles"],
        "tickers": [],
        "google_query": '"Doodles" NFT',
        "bing_queries": ["Doodles NFT"],
    },
    "milady": {
        "name": "Milady Maker",
        "names": ["milady maker", "milady", "remilia"],
        "tickers": [],
        "google_query": '"Milady Maker" OR "Milady" NFT OR Remilia',
        "bing_queries": ["Milady NFT"],
    },
}

# A pseudo-collection for the NFT market as a whole (OpenSea, marketplaces, regulation, macro NFT
# mood). Sparse per-collection news makes this a useful backdrop. Only a headline hit counts
# (min_relevance 3 = one title match), because "NFT" in the body of a general crypto article is noise.
NFT_MARKET_ID = "nft-market"
NFT_MARKET = {
    "name": "NFT market",
    "names": ["nft", "nfts", "non-fungible token", "non-fungible tokens", "opensea", "magic eden"],
    "tickers": [],
    "min_relevance": 3.0,
    "google_query": '"NFT market" OR "NFT sales" OR OpenSea',
    "bing_queries": ['"NFT market"'],
}

# ── Sources ───────────────────────────────────────────────────────────────────
# Checked live on 2026-11-16. In the 7 days before, none of the 311 entries in the broad feeds below
# (NFT sites included, which now mostly republish general crypto news) had a tracked collection,
# OpenSea or even "NFT" in its title. Per-collection news SEARCH feeds are therefore the main source:
GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
BING_NEWS_URL = "https://www.bing.com/news/search"
SEARCH_WINDOW = "7d"                   # Google News "when:" operator
SEARCH_TRUST_DEFAULT = 0.7             # publisher not in SOURCE_TRUST

# Publishers seen in search results, by the name the search feed gives. Anything else gets
# SEARCH_TRUST_DEFAULT. Aggregator and price-page sites rank lowest.
SOURCE_TRUST = {
    "CoinDesk": 1.0, "The Block": 1.0, "Reuters": 1.0, "Bloomberg": 1.0, "Bloomberg.com": 1.0,
    "CoinTelegraph": 0.95, "Cointelegraph": 0.95, "Decrypt": 0.9, "Blockworks": 0.9, "The Defiant": 0.9,
    "CryptoSlate": 0.9, "Fortune": 0.9, "TechCrunch": 0.9, "Bitcoin Magazine": 0.85,
    "NFT Evening": 0.8, "NFTevening.com": 0.8, "BeInCrypto": 0.8, "Yahoo Finance": 0.75, "NFT Plazas": 0.7,
    "Coinpedia": 0.6, "NewsBTC": 0.6, "AMBCrypto": 0.6, "CoinMarketCap": 0.5, "Binance": 0.5,
    "KuCoin": 0.5, "Crypto.com": 0.5, "Forbes": 0.6,
}

# Broad feeds, scanned with the same name matching as the crypto pipeline. Kept because they are
# cheap (fetched once per cycle) and do carry NFT stories when there is big NFT news.
# Dropped: Cointelegraph's NFT tag (last item 2026-10-13), NFT Now and NFTGators (403), DappRadar
# (empty), OpenSea blog (404). The general crypto feeds from utils/config.py RSS_FEEDS are added on top.
NFT_RSS_FEEDS = [
    {"name": "CoinDesk NFTs", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml&tags=nfts", "trust_weight": 1.0},
    {"name": "The Defiant",   "url": "https://thedefiant.io/api/feed",       "trust_weight": 0.9},
    {"name": "NFT Evening",   "url": "https://nftevening.com/feed/",         "trust_weight": 0.8},
    {"name": "NFT Plazas",    "url": "https://nftplazas.com/feed/",          "trust_weight": 0.7},
]

FEED_TIMEOUT_SECONDS = 8
FEED_USER_AGENT = "Mozilla/5.0 (compatible; AltInvestSentiment/1.0)"
SUMMARY_MAX_CHARS = 600

# ── Windows and weights ───────────────────────────────────────────────────────
# NFT news is far sparser than crypto news, so the window is longer and decay slower than the
# crypto pipeline's 72h / 12h.
NFT_MAX_ARTICLE_AGE_HOURS = 168
NFT_RECENCY_HALF_LIFE_HOURS = 48
NFT_MAX_ARTICLES_SCORED = 40           # per collection per cycle, newest first (bounds LLM cost); search
                                       # results include many price pages the LLM drops, so leave room

NFT_NEWS_WEIGHT = 0.65
NFT_MARKET_SIGNAL_WEIGHT = 0.35

# Confidence reaches 1.0 at this many relevant articles (crypto: 30).
NFT_CONFIDENCE_FULL_ARTICLES = 10

# ── Market signal (floor and sales momentum) ──────────────────────────────────
# Percent changes are clipped to these bounds before being mapped onto 0..1.
MARKET_CLIP_24H_PCT = 15.0
MARKET_CLIP_7D_PCT = 30.0
MARKET_COMPONENT_WEIGHTS = {"change_7d": 0.45, "change_24h": 0.20, "activity": 0.35}

# ── LLM scorer ────────────────────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_TIMEOUT_SECONDS = 45
GROQ_BATCH_SIZE = 40                   # >= NFT_MAX_ARTICLES_SCORED: one request sees every article, so
                                       # rewordings of one story can be matched across the whole list
GROQ_MAX_ATTEMPTS = 3
GROQ_CACHE_MAX_ENTRIES = 64            # one entry per (collection, article list); bounded, since the
                                       # backend's memory is already under watch

# Ordinal label + intensity -> score. LLMs are better at ordinal judgements than at calibrated
# floats, and this keeps the scores comparable between runs.
INTENSITY_SCORE = {"low": 0.3, "medium": 0.6, "high": 0.9}


def groq_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY") or None


def model_name() -> str:
    return os.getenv("NFT_SENTIMENT_MODEL") or DEFAULT_MODEL
