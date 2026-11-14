"""
db/seed_nft.py
Seeds nft_collections with the static metadata of the 7 real collections the ML service tracks
(ml/config.py NFT_SLUGS, ml/docs/DECISIONS.md D54, D61, D67).

No market numbers are written: floor, liquidity, risk and sales come from the ML service through the daily
pull (backend/controllers/nft_pull.py). Rows of the fictional collections the old seed wrote are deleted
from every nft_* table. Safe to re-run: collections are upserted on slug and nothing is inserted twice.
Run: python db/seed_nft.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

NOW = datetime.now(timezone.utc)

# Names, symbols, supply and contracts as reported by OpenSea and Alchemy on 2026-11-10 (Phase 10 step 10.2).
# The ML pull refreshes name, symbol, supply, description and image_url; subcategory and banner_color stay.
COLLECTIONS = [
    {"slug": "boredapeyachtclub", "name": "Bored Ape Yacht Club", "symbol": "BAYC", "supply": 9996,
     "contract": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d", "banner_color": "#2b2b2b"},
    {"slug": "mutant-ape-yacht-club", "name": "Mutant Ape Yacht Club", "symbol": "MAYC", "supply": 19571,
     "contract": "0x60e4d786628fea6478f785a6d7e704777c86a7c6", "banner_color": "#1f2a1c"},
    {"slug": "pudgypenguins", "name": "Pudgy Penguins", "symbol": "PPG", "supply": 8888,
     "contract": "0xbd3531da5cf5857e7cfaa92426877b022e612cf8", "banner_color": "#1b2a3a"},
    {"slug": "lilpudgys", "name": "Lil Pudgys", "symbol": "LP", "supply": 21932,
     "contract": "0x524cab2ec69124574082676e6f654a18df49a048", "banner_color": "#1d2b3f"},
    {"slug": "azuki", "name": "Azuki", "symbol": "AZUKI", "supply": 10000,
     "contract": "0xed5af388653567af2f388e6224dc7c4b3241c544", "banner_color": "#3a1c1f"},
    {"slug": "doodles-official", "name": "Doodles", "symbol": "DOODLE", "supply": 9998,
     "contract": "0x8a90cab2b38dba80c64b7734e58ee1db38b8992e", "banner_color": "#2c2240"},
    {"slug": "milady", "name": "Milady Maker", "symbol": "MIL", "supply": 9976,
     "contract": "0x5af0d9827e0c53e4799bb226655a1de152a425a5", "banner_color": "#26262e"},
]
for _c in COLLECTIONS:
    _c.update({"subcategory": "PFP", "verified": True, "description": ""})

# Written by the earlier seed and not real (AUDIT G-07); removed everywhere on every run.
FICTIONAL_SLUGS = ("neondrifters", "pixelwardens", "genesispunks", "astralcats")

NFT_TABLES = ("nft_collections", "nft_market_data", "nft_sales", "nft_holder_stats", "nft_liquidity",
              "nft_risk_breakdown", "nft_traits", "nft_tokens", "nft_token_sale_history",
              "nft_token_ownership_history")

# Rows the earlier seed wrote for boredapeyachtclub with made-up numbers carry no `source`; ML rows carry
# source "ml-service". Only the made-up ones are removed.
SEEDED_NUMBER_TABLES = ("nft_market_data", "nft_sales", "nft_holder_stats", "nft_liquidity", "nft_risk_breakdown",
                        "nft_traits", "nft_tokens", "nft_token_sale_history", "nft_token_ownership_history")


def seed():
    db = get_db()
    removed = 0
    for table in NFT_TABLES:
        removed += db[table].delete_many({"slug": {"$in": list(FICTIONAL_SLUGS)}}).deleted_count
    for table in SEEDED_NUMBER_TABLES:
        removed += db[table].delete_many({"source": {"$ne": "ml-service"}}).deleted_count
    removed += db.aai_scores.delete_many({"target_type": "nft", "model_version": "seed-v1"}).deleted_count
    print(f"[nft_*] removed {removed} fictional or made-up rows")

    for c in COLLECTIONS:
        static = {k: c[k] for k in ("subcategory", "banner_color")}
        rest = {k: v for k, v in c.items() if k not in static}
        db.nft_collections.update_one(
            {"slug": c["slug"]},
            {"$set": {**rest, "updated_at": NOW}, "$setOnInsert": {**static, "created_at": NOW}},
            upsert=True,
        )
    print(f"[nft_collections] upserted {len(COLLECTIONS)} (market data comes from the ML pull)")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
