"""
db/seed_assets.py
Seeds: assets, asset_market_data
Source: values transcribed from frontend/src/data/sample_data/assets.json
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

NOW = datetime.now(timezone.utc)

ASSETS = [
    {"asset_id": "BTC", "symbol": "BTC", "name": "Bitcoin", "category": "crypto",
     "subcategory": "Layer 1", "logo_color": "#f7931a", "logo_url": None,
     "description": "Bitcoin is the original decentralized digital currency, operating without a central bank or single administrator. Transactions are verified by network nodes through cryptographic proof-of-work and recorded on a public blockchain.",
     "website": "https://bitcoin.org", "all_time_high": 108950.00,
     "ath_date": "2026-01-14", "related_assets": ["ETH", "LINK"]},
    {"asset_id": "ETH", "symbol": "ETH", "name": "Ethereum", "category": "crypto",
     "subcategory": "Layer 1", "logo_color": "#627eea", "logo_url": None,
     "description": "Ethereum is a decentralized, programmable blockchain that introduced smart contracts, enabling developers to build applications ranging from decentralized finance to NFT marketplaces.",
     "website": "https://ethereum.org", "all_time_high": 4860.00,
     "ath_date": "2025-11-02", "related_assets": ["BTC", "ARB", "UNI"]},
    {"asset_id": "SOL", "symbol": "SOL", "name": "Solana", "category": "crypto",
     "subcategory": "Layer 1", "logo_color": "#9945ff", "logo_url": None,
     "description": "Solana is a high-throughput Layer 1 blockchain designed for fast, low-cost transactions using a proof-of-history consensus mechanism.",
     "website": "https://solana.com", "all_time_high": 260.00,
     "ath_date": "2025-12-20", "related_assets": ["BTC", "ETH"]},
    {"asset_id": "LINK", "symbol": "LINK", "name": "Chainlink", "category": "crypto",
     "subcategory": "Infrastructure", "logo_color": "#2a5ada", "logo_url": None,
     "description": "Chainlink is a decentralized oracle network that connects smart contracts to real-world data, powering price feeds for a large share of DeFi protocols.",
     "website": "", "all_time_high": 52.70, "ath_date": "2025-08-09",
     "related_assets": ["ETH", "ARB"]},
    {"asset_id": "DOGE", "symbol": "DOGE", "name": "Dogecoin", "category": "crypto",
     "subcategory": "Meme/Community", "logo_color": "#c2a633", "logo_url": None,
     "description": "Dogecoin began as a lighthearted, meme-inspired cryptocurrency but has retained a large, active community and consistent liquidity.",
     "website": "", "all_time_high": 0.74, "ath_date": "2025-03-15",
     "related_assets": ["BTC"]},
    {"asset_id": "ARB", "symbol": "ARB", "name": "Arbitrum", "category": "crypto",
     "subcategory": "Layer 2", "logo_color": "#28a0f0", "logo_url": None,
     "description": "Arbitrum is a Layer 2 scaling network for Ethereum that uses optimistic rollups to reduce transaction costs while inheriting Ethereum's security guarantees.",
     "website": "", "all_time_high": 2.39, "ath_date": "2024-06-01",
     "related_assets": ["ETH"]},
    {"asset_id": "DAI", "symbol": "DAI", "name": "Dai", "category": "crypto",
     "subcategory": "Stablecoin-adjacent", "logo_color": "#f5ac37", "logo_url": None,
     "description": "Dai is a decentralized, crypto-collateralized stablecoin soft-pegged to the US dollar and managed through an over-collateralized vault system.",
     "website": "", "all_time_high": 1.01, "ath_date": "2023-05-01",
     "related_assets": ["ETH"]},
    {"asset_id": "UNI", "symbol": "UNI", "name": "Uniswap", "category": "crypto",
     "subcategory": "DeFi", "logo_color": "#ff007a", "logo_url": None,
     "description": "Uniswap is the largest decentralized exchange protocol on Ethereum, using an automated market maker model to enable permissionless token swaps.",
     "website": "", "all_time_high": 44.92, "ath_date": "2021-05-03",
     "related_assets": ["ETH", "ARB"]},
    {"asset_id": "BASE", "symbol": "BASE", "name": "Base Ecosystem Index", "category": "crypto",
     "subcategory": "Layer 2", "logo_color": "#0052ff", "logo_url": None,
     "description": "The Base Ecosystem Index tracks a basket of leading tokens built on the Base Layer 2 network, offering diversified exposure to the network's DeFi and consumer application growth.",
     "website": "", "all_time_high": 58.20, "ath_date": "2026-02-10",
     "related_assets": ["ETH", "ARB"]},
]

MARKET_DATA = [
    {"asset_id": "BTC", "price": 71450.30, "change_1h": 0.18, "change_24h": 2.14, "change_7d": 5.62,
     "market_cap": 1415945000000, "volume_24h": 38200000000, "circulating_supply": 19820000, "market_rank": 1},
    {"asset_id": "ETH", "price": 3845.60, "change_1h": -0.06, "change_24h": -0.85, "change_7d": 1.94,
     "market_cap": 463743360000, "volume_24h": 19600000000, "circulating_supply": 120600000, "market_rank": 2},
    {"asset_id": "SOL", "price": 178.92, "change_1h": 0.42, "change_24h": 1.83, "change_7d": -3.10,
     "market_cap": 86101000000, "volume_24h": 6800000000, "circulating_supply": 481200000, "market_rank": 5},
    {"asset_id": "LINK", "price": 16.40, "change_1h": 0.09, "change_24h": 1.10, "change_7d": 4.02,
     "market_cap": 9626800000, "volume_24h": 612000000, "circulating_supply": 587000000, "market_rank": 14},
    {"asset_id": "DOGE", "price": 0.187, "change_1h": 0.31, "change_24h": 11.62, "change_7d": 18.40,
     "market_cap": 27676000000, "volume_24h": 2100000000, "circulating_supply": 148000000000, "market_rank": 9},
    {"asset_id": "ARB", "price": 1.28, "change_1h": -0.02, "change_24h": 3.87, "change_7d": -1.20,
     "market_cap": 5068800000, "volume_24h": 284000000, "circulating_supply": 3960000000, "market_rank": 38},
    {"asset_id": "DAI", "price": 1.00, "change_1h": 0.00, "change_24h": 0.00, "change_7d": 0.01,
     "market_cap": 5300000000, "volume_24h": 3900000000, "circulating_supply": 5300000000, "market_rank": 19},
    {"asset_id": "UNI", "price": 9.14, "change_1h": -0.21, "change_24h": -4.06, "change_7d": -8.90,
     "market_cap": 6882420000, "volume_24h": 198000000, "circulating_supply": 753000000, "market_rank": 22},
    {"asset_id": "BASE", "price": 22.35, "change_1h": 0.04, "change_24h": 0.42, "change_7d": 2.11,
     "market_cap": 1117500000, "volume_24h": 41000000, "circulating_supply": 50000000, "market_rank": 102},
]


def seed():
    db = get_db()

    for a in ASSETS:
        db.assets.update_one(
            {"asset_id": a["asset_id"]},
            {"$set": {**a, "created_at": NOW}},
            upsert=True,
        )
        print(f"[assets] upserted {a['asset_id']}")

    for m in MARKET_DATA:
        doc = {**m, "timestamp": NOW}
        db.asset_market_data.insert_one(doc)
        print(f"[asset_market_data] inserted snapshot for {m['asset_id']}")

    db.assets.create_index("asset_id", unique=True)
    db.asset_market_data.create_index([("asset_id", 1), ("timestamp", -1)])
    print("Indexes ensured.")


if __name__ == "__main__":
    seed()