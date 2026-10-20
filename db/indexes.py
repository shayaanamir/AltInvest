"""
db/indexes.py

Every index the backend relies on, in one place. The backend creates them at startup
(backend/main.py), so a database that was never seeded still gets them; the seed scripts can
call ensure_indexes() too. create_index is idempotent, so running this repeatedly is harmless.

The (key, timestamp) indexes matter most: the "latest row per asset/collection" queries in
db/queries.py sort on exactly those fields, which lets MongoDB walk the index (one entry per key)
instead of sorting the whole collection in memory, where the 100 MB sort limit applies.

Run by hand: python db/indexes.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

from pymongo import ASCENDING as ASC, DESCENDING as DESC

from db.mongo_connection import get_db

log = logging.getLogger("indexes")

# How long a search stays in a user's recent-search history.
SEARCH_HISTORY_TTL_SECONDS = 90 * 24 * 60 * 60

# collection -> [(keys, options)]
INDEXES = {
    "users": [([("email", ASC)], {"unique": True})],
    "user_settings": [([("user_id", ASC)], {"unique": True})],
    "assets": [([("asset_id", ASC)], {"unique": True})],
    "asset_market_data": [([("asset_id", ASC), ("timestamp", DESC)], {})],
    "prices": [([("asset", ASC), ("timestamp", DESC)], {})],
    "predictions": [([("asset", ASC), ("timestamp", DESC)], {})],
    "risk_scores": [([("asset", ASC), ("timestamp", DESC)], {})],
    "risk_breakdown": [([("asset", ASC), ("timestamp", DESC)], {})],
    "aai_scores": [
        ([("target_type", ASC), ("target_id", ASC), ("timestamp", DESC)], {}),
        ([("target_type", ASC), ("target_id", ASC), ("date", ASC)], {}),   # the daily upsert's filter
    ],
    "portfolio_holdings": [([("user_id", ASC), ("asset_type", ASC)], {})],
    "portfolio_transactions": [
        ([("user_id", ASC), ("holding_id", ASC), ("timestamp", DESC)], {}),
        ([("user_id", ASC), ("timestamp", DESC)], {}),
    ],
    "portfolio_snapshots": [([("user_id", ASC), ("snapshot_date", DESC)], {})],
    "watchlists": [([("user_id", ASC)], {})],
    "alerts": [([("user_id", ASC), ("status", ASC)], {})],
    "notifications": [([("user_id", ASC), ("timestamp", DESC)], {})],
    "market_insights": [([("published_at", DESC)], {})],
    "nft_collections": [([("slug", ASC)], {"unique": True})],
    "nft_market_data": [([("slug", ASC), ("timestamp", DESC)], {})],
    "nft_sales": [([("slug", ASC), ("timestamp", DESC)], {})],
    "nft_holder_stats": [([("slug", ASC), ("timestamp", DESC)], {})],
    "nft_liquidity": [([("slug", ASC), ("timestamp", DESC)], {})],
    "nft_risk_breakdown": [([("slug", ASC), ("timestamp", DESC)], {})],
    "nft_traits": [([("slug", ASC)], {})],
    "nft_tokens": [([("slug", ASC), ("token_id", ASC)], {"unique": True})],
    "nft_token_sale_history": [([("slug", ASC), ("token_id", ASC), ("timestamp", DESC)], {})],
    "nft_token_ownership_history": [([("slug", ASC), ("token_id", ASC), ("since", DESC)], {})],
    "user_search_history": [
        ([("user_id", ASC), ("query_key", ASC)], {"unique": True}),       # one row per distinct query
        ([("user_id", ASC), ("searched_at", DESC)], {}),
        ([("searched_at", ASC)], {"expireAfterSeconds": SEARCH_HISTORY_TTL_SECONDS}),
    ],
    "fx_rates": [([("base", ASC), ("as_of", DESC)], {"unique": True})],
}


def ensure_indexes() -> dict:
    """Creates any missing index. One failure (say, duplicate emails blocking a unique index) is
    logged and doesn't stop the rest. Returns {"created_or_present": n, "failed": {name: error}}."""
    db = get_db()
    # Rows from before searches were de-duplicated have no query_key and were never read back;
    # they would block the unique (user_id, query_key) index.
    db.user_search_history.delete_many({"query_key": {"$exists": False}})
    ok, failed = 0, {}
    for collection, specs in INDEXES.items():
        for keys, options in specs:
            try:
                db[collection].create_index(keys, **options)
                ok += 1
            except Exception as exc:
                name = f"{collection}({', '.join(k for k, _ in keys)})"
                failed[name] = f"{type(exc).__name__}: {exc}"
                log.error("[indexes] %s failed: %s", name, failed[name])
    return {"created_or_present": ok, "failed": failed}


if __name__ == "__main__":
    print(ensure_indexes())
