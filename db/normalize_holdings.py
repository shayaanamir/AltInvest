"""
db/normalize_holdings.py

One-off cleanup of portfolio_holdings written before the server normalised them:
  - crypto symbols upper-cased ("btc" -> "BTC"), so they match prices and stop valuing at nothing;
  - NFT slugs lower-cased;
  - a user's duplicate rows for the same crypto merged into one (quantities added, weighted
    average buy price, cost basis recomputed as quantity x average price);
  - cost basis recomputed everywhere it can be (it used to be typed in by hand).
Each merge is written to portfolio_transactions so the history explains it. Safe to re-run.

Run: python db/normalize_holdings.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collections import defaultdict
from datetime import datetime, timezone

from db.mongo_connection import get_db


def main():
    db = get_db()
    now = datetime.now(timezone.utc)
    fixed = merged = 0

    for h in db.portfolio_holdings.find({}):
        update = {}
        if h.get("asset_type") == "crypto" and h.get("symbol") and h["symbol"] != h["symbol"].strip().upper():
            update["symbol"] = h["symbol"].strip().upper()
        if h.get("asset_type") == "nft" and h.get("nft_collection_slug") and h["nft_collection_slug"] != h["nft_collection_slug"].strip().lower():
            update["nft_collection_slug"] = h["nft_collection_slug"].strip().lower()
        if update:
            db.portfolio_holdings.update_one({"_id": h["_id"]}, {"$set": update})
            fixed += 1

    groups = defaultdict(list)
    for h in db.portfolio_holdings.find({"asset_type": "crypto"}):
        groups[(h["user_id"], h.get("symbol"))].append(h)
    for (user_id, symbol), rows in groups.items():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: r.get("date_added") or now)
        keep, rest = rows[0], rows[1:]
        qty = sum(float(r.get("quantity") or 0) for r in rows)
        priced = [(float(r.get("quantity") or 0), r["avg_buy_price_usd"]) for r in rows if r.get("avg_buy_price_usd") is not None]
        pq = sum(q for q, _ in priced)
        avg = sum(q * p for q, p in priced) / pq if pq else None
        db.portfolio_holdings.update_one({"_id": keep["_id"]}, {"$set": {
            "quantity": qty, "avg_buy_price_usd": avg, "updated_at": now}})
        db.portfolio_holdings.delete_many({"_id": {"$in": [r["_id"] for r in rest]}})
        db.portfolio_transactions.insert_one({
            "user_id": user_id, "holding_id": str(keep["_id"]), "asset_type": "crypto", "symbol": symbol,
            "type": "adjust", "timestamp": now, "note": f"merged {len(rows)} duplicate rows",
            "after": {"quantity": qty, "avg_buy_price_usd": avg},
        })
        merged += len(rest)

    recomputed = 0
    for h in db.portfolio_holdings.find({}):
        q = h.get("quantity")
        if h.get("asset_type") == "crypto" and q is not None and h.get("avg_buy_price_usd") is not None:
            cost = round(q * h["avg_buy_price_usd"], 2)
        elif h.get("asset_type") == "nft" and q is not None and h.get("avg_buy_price_eth") is not None and h.get("avg_buy_eth_usd_rate"):
            cost = round(q * h["avg_buy_price_eth"] * h["avg_buy_eth_usd_rate"], 2)
        else:
            continue
        if h.get("cost_basis_usd") != cost:
            db.portfolio_holdings.update_one({"_id": h["_id"]}, {"$set": {"cost_basis_usd": cost}})
            recomputed += 1

    print(f"[holdings] normalised {fixed} row(s), merged away {merged} duplicate(s), recomputed {recomputed} cost basis value(s)")


if __name__ == "__main__":
    main()
