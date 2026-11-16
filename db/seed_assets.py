"""
db/seed_assets.py
Seeds: assets (identity only: id, symbol, name, category, display colour)
Source: db/seed_data/assets.json (seed input only; the frontend ships no data files)

No profile or market numbers are written. Description, website, subcategory and related assets come
from CoinGecko (backend/controllers/asset_profile_controller.py). Prices, market caps, volumes, changes and all-time highs are live:
backend/controllers/market_data_controller.py (CoinGecko + Binance) writes them, and deletes any
asset_market_data row it did not write.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

NOW = datetime.now(timezone.utc)

ASSETS = [
    {"asset_id": "BTC", "symbol": "BTC", "name": "Bitcoin", "category": "crypto", "logo_color": "#f7931a"},
    {"asset_id": "ETH", "symbol": "ETH", "name": "Ethereum", "category": "crypto", "logo_color": "#627eea"},
    {"asset_id": "SOL", "symbol": "SOL", "name": "Solana", "category": "crypto", "logo_color": "#9945ff"},
    {"asset_id": "LINK", "symbol": "LINK", "name": "Chainlink", "category": "crypto", "logo_color": "#2a5ada"},
    {"asset_id": "DOGE", "symbol": "DOGE", "name": "Dogecoin", "category": "crypto", "logo_color": "#c2a633"},
    {"asset_id": "ARB", "symbol": "ARB", "name": "Arbitrum", "category": "crypto", "logo_color": "#28a0f0"},
    {"asset_id": "DAI", "symbol": "DAI", "name": "Dai", "category": "crypto", "logo_color": "#f5ac37"},
    {"asset_id": "UNI", "symbol": "UNI", "name": "Uniswap", "category": "crypto", "logo_color": "#ff007a"},
]

# ── Remaining covered assets, built from the same sample JSON ───────────────
# The sample catalogue has 18 assets; the hand-written rows above cover 9 (metadata only).
# Fields the sample data doesn't have (description, website, related_assets)
# are left empty rather than invented.

# Not a real asset: a made-up "Base Ecosystem Index" with no market anywhere. Never seeded.
FICTIONAL = {"BASE"}


def _add_remaining_from_sample():
    import json
    path = os.path.join(os.path.dirname(__file__), "seed_data", "assets.json")
    with open(path, encoding="utf-8") as f:
        sample = json.load(f)["assets"]

    have = {a["asset_id"] for a in ASSETS}
    for s in sample:
        if s["symbol"] in have or s["symbol"] in FICTIONAL:
            continue
        ASSETS.append({
            "asset_id": s["symbol"], "symbol": s["symbol"], "name": s["name"],
            "category": s["category"], "logo_color": s.get("logoColor"),
        })


_add_remaining_from_sample()


def seed():
    db = get_db()

    for a in ASSETS:
        db.assets.update_one(
            {"asset_id": a["asset_id"]},
            {"$set": a, "$setOnInsert": {"created_at": NOW}},
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