"""
db/seed_insights.py
Seeds: market_insights, sentiment_themes
Source: dashboard.json insights[] (deduplicated), sentiment.json themes[]
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

INSIGHTS = [
    {"source": "CryptoBrief",
     "title": "Bitcoin ETF inflows accelerate as institutional demand strengthens",
     "summary": "Spot BTC ETF net inflows topped $1.2B this week, the strongest since January, as large asset managers increased allocations ahead of the next rebalancing window.",
     "impact": "Positive", "related_asset_symbol": "BTC", "related_nft_slug": None,
     "published_at": "2026-08-27T14:20:00Z"},
    {"source": "Block Daily",
     "title": "NFT blue-chip floor prices soften as liquidity thins",
     "summary": "Trading volume across top-10 NFT collections fell 22% week-over-week, with BAYC and comparable projects seeing wider bid-ask spreads.",
     "impact": "Negative", "related_asset_symbol": None, "related_nft_slug": "boredapeyachtclub",
     "published_at": "2026-08-27T09:05:00Z"},
    {"source": "MarketWatch",
     "title": "Solana network activity cools after month-long meme-coin surge",
     "summary": "Daily active addresses on Solana dropped 14% from their August peak, with analysts pointing to reduced speculative trading volume.",
     "impact": "Negative", "related_asset_symbol": "SOL", "related_nft_slug": None,
     "published_at": "2026-08-26T18:40:00Z"},
    {"source": "CoinDesk",
     "title": "Dogecoin rallies on renewed retail interest and exchange listings",
     "summary": "DOGE posted its strongest weekly gain in five months after two major exchanges expanded margin trading support.",
     "impact": "Positive", "related_asset_symbol": "DOGE", "related_nft_slug": None,
     "published_at": "2026-08-26T11:15:00Z"},
    {"source": "Decrypt",
     "title": "Chainlink expands oracle coverage to three additional Layer 2 networks",
     "summary": "The integration is expected to increase demand for LINK staking as more DeFi protocols route price feeds through the network.",
     "impact": "Positive", "related_asset_symbol": "LINK", "related_nft_slug": None,
     "published_at": "2026-08-25T16:00:00Z"},
    {"source": "The Block",
     "title": "Uniswap governance proposal to cut treasury spending faces pushback",
     "summary": "A vote to reduce grant funding by 40% has split the community, with several delegates warning of a slowdown in ecosystem development.",
     "impact": "Negative", "related_asset_symbol": "UNI", "related_nft_slug": None,
     "published_at": "2026-08-24T20:30:00Z"},
]

THEMES = [
    {"label": "Spot ETF inflows", "direction": "up", "category": "crypto"},
    {"label": "L2 fee compression", "direction": "up", "category": "crypto"},
    {"label": "Meme-coin retail resurgence", "direction": "up", "category": "crypto"},
    {"label": "Blue-chip NFT liquidity outflows", "direction": "down", "category": "nft"},
    {"label": "DeFi governance disputes", "direction": "down", "category": "crypto"},
]


def seed():
    db = get_db()
    now = datetime.now(timezone.utc)

    db.market_insights.delete_many({})  # dedupe: full reload, this collection is small
    for i in INSIGHTS:
        db.market_insights.insert_one(i)
    print(f"[market_insights] inserted {len(INSIGHTS)} (deduplicated)")

    for t in THEMES:
        db.sentiment_themes.update_one(
            {"label": t["label"]}, {"$set": {**t, "updated_at": now}}, upsert=True
        )
    print(f"[sentiment_themes] upserted {len(THEMES)}")

    db.market_insights.create_index("published_at")
    print("Indexes ensured.")


if __name__ == "__main__":
    seed()