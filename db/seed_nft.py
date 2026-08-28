"""
db/seed_nft.py
Seeds: nft_collections, nft_market_data, nft_sales, nft_holder_stats,
       nft_liquidity, nft_risk_breakdown, nft_traits, nft_tokens,
       nft_token_sale_history, nft_token_ownership_history
Source: frontend/src/data/sample_data/nftCollections.json + nftDetail.json
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

NOW = datetime.now(timezone.utc)

COLLECTIONS = [
    {"slug": "boredapeyachtclub", "name": "Bored Ape Yacht Club", "symbol": "BAYC",
     "subcategory": "Blue-chip", "banner_color": "#2b2b2b", "verified": True, "supply": 10000,
     "description": ""},
    {"slug": "neondrifters", "name": "Neon Drifters", "symbol": "NDRFT",
     "subcategory": "Generative Art", "banner_color": "#1e2038", "verified": True, "supply": 6000,
     "description": ""},
    {"slug": "pixelwardens", "name": "Pixel Wardens", "symbol": "PXLW",
     "subcategory": "Gaming", "banner_color": "#191a2e", "verified": False, "supply": 8888,
     "description": ""},
    {"slug": "genesispunks", "name": "Genesis Punks", "symbol": "GPUNK",
     "subcategory": "Blue-chip", "banner_color": "#0d0e1a", "verified": True, "supply": 4000,
     "description": ""},
    {"slug": "astralcats", "name": "Astral Cats", "symbol": "ACAT",
     "subcategory": "PFP/Community", "banner_color": "#1b1f2e", "verified": False, "supply": 9999,
     "description": ""},
]

MARKET_DATA = [
    {"slug": "boredapeyachtclub", "floor_eth": 14.2, "floor_usd": 54607.52, "change_24h": -4.5,
     "change_7d": -9.1, "volume_24h_eth": 182, "holders_count": 5412},
    {"slug": "neondrifters", "floor_eth": 3.8, "floor_usd": 14613.28, "change_24h": 5.4,
     "change_7d": 12.8, "volume_24h_eth": 64, "holders_count": 2890},
    {"slug": "pixelwardens", "floor_eth": 1.1, "floor_usd": 4230.16, "change_24h": -1.1,
     "change_7d": -3.2, "volume_24h_eth": 21, "holders_count": 3204},
    {"slug": "genesispunks", "floor_eth": 42.6, "floor_usd": 163862.56, "change_24h": 0.8,
     "change_7d": 3.4, "volume_24h_eth": 96, "holders_count": 1890},
    {"slug": "astralcats", "floor_eth": 0.65, "floor_usd": 2499.64, "change_24h": -6.7,
     "change_7d": -14.2, "volume_24h_eth": 9, "holders_count": 4120},
]

LIQUIDITY = [
    {"slug": "boredapeyachtclub", "sell_through_rate": 0.034, "illiquidity_risk_score": 58.2,
     "risk_bucket": "High", "wash_trading_flag": False},
    {"slug": "neondrifters", "sell_through_rate": 0.061, "illiquidity_risk_score": 34.5,
     "risk_bucket": "Medium", "wash_trading_flag": False},
    {"slug": "pixelwardens", "sell_through_rate": 0.028, "illiquidity_risk_score": 49.7,
     "risk_bucket": "Medium", "wash_trading_flag": False},
    {"slug": "genesispunks", "sell_through_rate": 0.019, "illiquidity_risk_score": 62.8,
     "risk_bucket": "High", "wash_trading_flag": False},
    {"slug": "astralcats", "sell_through_rate": 0.012, "illiquidity_risk_score": 74.3,
     "risk_bucket": "High", "wash_trading_flag": True},
]

RISK_BREAKDOWN = [
    {"slug": "boredapeyachtclub", "floor_volatility_30d": 62, "holder_concentration": 55, "liquidity_depth": 41},
    {"slug": "neondrifters", "floor_volatility_30d": 38, "holder_concentration": 29, "liquidity_depth": 64},
    {"slug": "pixelwardens", "floor_volatility_30d": 40, "holder_concentration": 24, "liquidity_depth": 47},
    {"slug": "genesispunks", "floor_volatility_30d": 45, "holder_concentration": 61, "liquidity_depth": 33},
    {"slug": "astralcats", "floor_volatility_30d": 78, "holder_concentration": 69, "liquidity_depth": 22},
]

HOLDER_STATS = [
    {"slug": "boredapeyachtclub", "unique_holder_pct": 54.1, "top_10_pct": 21.4, "top_1_pct": 6.8},
    {"slug": "neondrifters", "unique_holder_pct": 48.2, "top_10_pct": 17.9, "top_1_pct": 4.2},
    {"slug": "pixelwardens", "unique_holder_pct": 36.0, "top_10_pct": 19.2, "top_1_pct": 5.5},
    {"slug": "genesispunks", "unique_holder_pct": 47.3, "top_10_pct": 26.8, "top_1_pct": 9.1},
    {"slug": "astralcats", "unique_holder_pct": 41.2, "top_10_pct": 31.6, "top_1_pct": 12.4},
]

TRAITS = [
    {"slug": "boredapeyachtclub", "categories": ["Background", "Fur", "Clothes", "Eyes", "Mouth", "Hat"],
     "distribution": [
         {"trait": "Fur", "value": "Solid Gold", "rarity_pct": 0.8},
         {"trait": "Fur", "value": "Trippy", "rarity_pct": 1.2},
         {"trait": "Eyes", "value": "Laser Eyes", "rarity_pct": 0.9},
         {"trait": "Hat", "value": "King's Crown", "rarity_pct": 1.4},
         {"trait": "Mouth", "value": "Bored Unshaven Party Horn", "rarity_pct": 2.1},
     ]},
]

# Representative sample sales/tokens — extend per collection as needed
SALES = [
    {"slug": "boredapeyachtclub", "token_id": "8821", "price_eth": 13.8,
     "buyer": "0x7fA...c2e1", "seller": "0x91B...8f4a", "timestamp": "2026-08-28T02:40:00Z"},
    {"slug": "boredapeyachtclub", "token_id": "5502", "price_eth": 14.5,
     "buyer": "0x4dC...a301", "seller": "0x22E...9b7c", "timestamp": "2026-08-27T21:15:00Z"},
]

TOKENS = [
    {"slug": "boredapeyachtclub", "token_id": "4271", "rarity_rank": 1842, "rarity_score": 92.4,
     "listed_price_eth": None, "image_description": "Ape with blue fur, laser eyes, captain's hat, gold chain",
     "owner_address": "0x2c8...91Aa",
     "traits": [
         {"category": "Background", "value": "Aquamarine", "rarity_pct": 8.4},
         {"category": "Fur", "value": "Blue", "rarity_pct": 4.1},
         {"category": "Eyes", "value": "Laser Eyes", "rarity_pct": 0.9},
     ]},
]

TOKEN_SALE_HISTORY = [
    {"slug": "boredapeyachtclub", "token_id": "4271", "price_eth": 11.5, "type": "Purchase",
     "counterparty": "0x4bA...2f10", "timestamp": "2022-03-14T18:22:00Z"},
]

TOKEN_OWNERSHIP_HISTORY = [
    {"slug": "boredapeyachtclub", "token_id": "4271", "owner": "0x2c8...91Aa", "since": "2022-03-14T18:22:00Z"},
    {"slug": "boredapeyachtclub", "token_id": "4271", "owner": "0x4bA...2f10", "since": "2021-09-02T11:05:00Z"},
]


def seed():
    db = get_db()

    for c in COLLECTIONS:
        db.nft_collections.update_one(
            {"slug": c["slug"]}, {"$set": {**c, "created_at": NOW}}, upsert=True
        )
    print(f"[nft_collections] upserted {len(COLLECTIONS)}")

    for m in MARKET_DATA:
        db.nft_market_data.insert_one({**m, "timestamp": NOW})
    print(f"[nft_market_data] inserted {len(MARKET_DATA)}")

    for l in LIQUIDITY:
        db.nft_liquidity.insert_one({**l, "timestamp": NOW})
    print(f"[nft_liquidity] inserted {len(LIQUIDITY)}")

    for r in RISK_BREAKDOWN:
        db.nft_risk_breakdown.insert_one({**r, "timestamp": NOW})
    print(f"[nft_risk_breakdown] inserted {len(RISK_BREAKDOWN)}")

    for h in HOLDER_STATS:
        db.nft_holder_stats.insert_one({**h, "timestamp": NOW})
    print(f"[nft_holder_stats] inserted {len(HOLDER_STATS)}")

    for t in TRAITS:
        db.nft_traits.update_one({"slug": t["slug"]}, {"$set": t}, upsert=True)
    print(f"[nft_traits] upserted {len(TRAITS)}")

    for s in SALES:
        db.nft_sales.insert_one(s)
    print(f"[nft_sales] inserted {len(SALES)}")

    for tok in TOKENS:
        db.nft_tokens.update_one(
            {"slug": tok["slug"], "token_id": tok["token_id"]}, {"$set": tok}, upsert=True
        )
    print(f"[nft_tokens] upserted {len(TOKENS)}")

    for sh in TOKEN_SALE_HISTORY:
        db.nft_token_sale_history.insert_one(sh)
    for oh in TOKEN_OWNERSHIP_HISTORY:
        db.nft_token_ownership_history.insert_one(oh)
    print("[nft_token_sale_history / nft_token_ownership_history] inserted")

    # indexes
    db.nft_collections.create_index("slug", unique=True)
    db.nft_market_data.create_index([("slug", 1), ("timestamp", -1)])
    db.nft_sales.create_index([("slug", 1), ("timestamp", -1)])
    db.nft_tokens.create_index([("slug", 1), ("token_id", 1)], unique=True)
    print("Indexes ensured.")


if __name__ == "__main__":
    seed()