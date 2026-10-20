"""
db/seed_portfolio_snapshots.py
Seeds: portfolio_snapshots (history before the backend's daily snapshot job started)

For each user and each day since their first holding was added:
    value = sum(quantity x that day's close) over crypto holdings already held,
          + sum(quantity x TODAY's floor) over NFT holdings already held.
This answers "what would these holdings have been worth", assuming the quantities
never changed. NFT floor history isn't stored, so NFTs are valued at today's floor
on every day; rows are tagged source="backfill", nft_at_current_floor=True.
Existing rows (including the live ones written by the backend) are never overwritten.

Run after seed_prices and seed_user_data (seed_all.py does).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone

from db.mongo_connection import get_db
from db.queries import get_daily_price_series, get_nft_market_data_latest

MAX_DAYS = 365


def _day_key(d) -> str:
    return d.strftime("%Y-%m-%dT00:00:00Z")


def seed():
    db = get_db()
    db.portfolio_snapshots.create_index([("user_id", 1), ("snapshot_date", -1)])

    today = datetime.now(timezone.utc).date()
    total_rows = 0

    for user_id in db.portfolio_holdings.distinct("user_id"):
        holdings = list(db.portfolio_holdings.find({"user_id": user_id}))
        if not holdings:
            continue

        # Daily closes per crypto symbol, with gaps carried forward.
        closes: dict[str, dict] = {}
        for h in holdings:
            sym = h.get("symbol")
            if h.get("asset_type") == "crypto" and sym and sym not in closes:
                closes[sym] = {p["date"]: p["price"] for p in get_daily_price_series(sym, MAX_DAYS)}

        nft_floor = {}
        for h in holdings:
            slug = h.get("nft_collection_slug")
            if h.get("asset_type") == "nft" and slug and slug not in nft_floor:
                nft_floor[slug] = (get_nft_market_data_latest(slug) or {}).get("floor_usd") or 0.0

        first = min(h["date_added"].date() for h in holdings)
        start = max(first, today - timedelta(days=MAX_DAYS))

        last_price: dict[str, float] = {}
        rows = 0
        d = start
        while d <= today:
            key = d.isoformat()
            total = 0.0
            for h in holdings:
                if h["date_added"].date() > d:
                    continue
                if h.get("asset_type") == "crypto":
                    sym = h.get("symbol")
                    price = closes.get(sym, {}).get(key, last_price.get(sym))
                    if price is not None:
                        last_price[sym] = price
                        total += price * (h.get("quantity") or 0.0)
                elif h.get("asset_type") == "nft":
                    total += nft_floor.get(h.get("nft_collection_slug"), 0.0) * (h.get("quantity") or 1)
            if total > 0:
                result = db.portfolio_snapshots.update_one(
                    {"user_id": user_id, "snapshot_date": _day_key(d)},
                    {"$setOnInsert": {
                        "total_value_usd": round(total, 2),
                        "source": "backfill", "nft_at_current_floor": True,
                    }},
                    upsert=True,
                )
                rows += 1 if result.upserted_id else 0
            d += timedelta(days=1)

        total_rows += rows
        print(f"[portfolio_snapshots] user {user_id}: {rows} new row(s) from {start} to {today}")

    print(f"[portfolio_snapshots] {total_rows} row(s) inserted.")


if __name__ == "__main__":
    seed()
