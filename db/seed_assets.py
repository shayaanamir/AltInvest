"""
db/seed_assets.py
Seeds: assets (names, categories, colours, descriptions)
Source: db/seed_data/assets.json (seed input only; the frontend ships no data files)

No market numbers are written. Prices, market caps, volumes, changes and all-time highs are live:
backend/controllers/market_data_controller.py (CoinGecko + Binance) writes them, and deletes any
asset_market_data row it did not write.
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

# ── Remaining covered assets, built from the same sample JSON ───────────────
# The sample catalogue has 18 assets; the hand-written rows above cover 9 (metadata only).
# Fields the sample data doesn't have (description, website, related_assets)
# are left empty rather than invented.

def _add_remaining_from_sample():
    import json
    path = os.path.join(os.path.dirname(__file__), "seed_data", "assets.json")
    with open(path, encoding="utf-8") as f:
        sample = json.load(f)["assets"]

    have = {a["asset_id"] for a in ASSETS}
    for s in sample:
        if s["symbol"] in have:
            continue
        ASSETS.append({
            "asset_id": s["symbol"], "symbol": s["symbol"], "name": s["name"],
            "category": s["category"], "subcategory": s.get("subcategory"),
            "logo_color": s.get("logoColor"), "logo_url": None,
            "description": None, "website": None,
            "all_time_high": s.get("ath"), "ath_date": s.get("athDate"),
            "related_assets": [],
        })


_add_remaining_from_sample()


def seed():
    db = get_db()

    for a in ASSETS:
        db.assets.update_one(
            {"asset_id": a["asset_id"]},
            {"$set": {**a, "created_at": NOW}},
            upsert=True,
        )
        print(f"[assets] upserted {a['asset_id']}")

    db.assets.create_index("asset_id", unique=True)
    db.asset_market_data.create_index([("asset_id", 1), ("timestamp", -1)])
    print("Indexes ensured.")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()