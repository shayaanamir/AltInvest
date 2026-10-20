"""
db/normalize_watchlists.py

One-off cleanup of watchlist items written before the server normalised them: crypto symbols
upper-cased, NFT slugs lower-cased, and an item that appears twice on the same list kept once
(the earliest). Safe to re-run.

Run: python db/normalize_watchlists.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.mongo_connection import get_db


def main():
    db = get_db()
    changed = dropped = 0
    for w in db.watchlists.find({}, {"items": 1}):
        items = w.get("items") or []
        seen, cleaned = set(), []
        for it in items:
            key = (it.get("symbol_or_slug") or "").strip()
            key = key.lower() if it.get("type") == "nft" else key.upper()
            if not key or key in seen:
                dropped += 1
                continue
            seen.add(key)
            cleaned.append({**it, "symbol_or_slug": key})
        if cleaned != items:
            db.watchlists.update_one({"_id": w["_id"]}, {"$set": {"items": cleaned}})
            changed += 1
    print(f"[watchlists] cleaned {changed} list(s), dropped {dropped} duplicate/empty item(s)")


if __name__ == "__main__":
    main()
