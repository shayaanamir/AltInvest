# db/seed.py
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.mongo_connection import get_db

ASSETS = [
    {"asset_id": "BTC", "name": "Bitcoin",  "symbol": "BTC"},
    {"asset_id": "ETH", "name": "Ethereum", "symbol": "ETH"},
]

def seed():
    db = get_db()
    for asset in ASSETS:
        db.assets.update_one(
            {"asset_id": asset["asset_id"]},
            {"$set": asset},
            upsert=True
        )
        print(f"Seeded {asset['name']}")

if __name__ == "__main__":
    seed()