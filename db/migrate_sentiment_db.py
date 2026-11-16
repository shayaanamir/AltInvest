"""
db/migrate_sentiment_db.py

One-off, idempotent migration for audit Step 4 (G-18, G-22).

1. Copies the sentiment engine's collections (sentiment, sentiment_history, raw_articles) from the old
   separate database (default `altinvest`) into the application database (MONGO_DB_NAME). It never
   deletes or changes the source, so it can be re-run, and the old database can be dropped by hand once
   the app looks right.
   - sentiment (latest reading per asset): copied only when the target has no row for that asset, or
     an older one (compared by `updated_at`).
   - sentiment_history, raw_articles: copied by _id; rows already in the target are skipped.
2. Fills `ts` (a real date) on sentiment_history rows that only have the ISO-string `timestamp`, so the
   TTL index can expire them.
3. Creates every index (db/indexes.py), including the sentiment_history TTL.

Refuses a non-local MongoDB (Atlas) unless --allow-remote is given, like the seed scripts.

Run in the backend container:
    docker exec -w /app altinvest-backend python db/migrate_sentiment_db.py
or on the host, from the repo root:
    python db/migrate_sentiment_db.py [--from-db altinvest] [--dry-run] [--allow-remote]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from db.mongo_connection import db_name, get_client
from db.seed_guard import ALLOW_FLAG, is_local, uri_hosts

BATCH = 1000
COPY_BY_ID = ("sentiment_history", "raw_articles")


def _history_ts(timestamp):
    # Imported lazily: the sentiment engine's config pulls in its asset tables.
    from sentiment_engine.storage.mongo_handler import history_ts
    return history_ts(timestamp)


def copy_latest(src, dst, dry_run: bool) -> int:
    """sentiment: newer-or-missing rows only. Returns how many were (or would be) written."""
    n = 0
    for row in src.sentiment.find({}):
        row.pop("_id", None)
        asset_id = row.get("asset_id")
        if not asset_id:
            continue
        current = dst.sentiment.find_one({"asset_id": asset_id}, {"updated_at": 1})
        if current and str(current.get("updated_at") or "") >= str(row.get("updated_at") or ""):
            continue
        n += 1
        if not dry_run:
            dst.sentiment.replace_one({"asset_id": asset_id}, row, upsert=True)
    return n


def copy_by_id(src_coll, dst_coll, dry_run: bool) -> int:
    """Inserts rows whose _id isn't in the target yet. Returns how many were (or would be) inserted."""
    n, batch = 0, []

    def flush():
        nonlocal n
        if not batch:
            return
        ids = [d["_id"] for d in batch]
        present = {d["_id"] for d in dst_coll.find({"_id": {"$in": ids}}, {"_id": 1})}
        new = [d for d in batch if d["_id"] not in present]
        n += len(new)
        if new and not dry_run:
            try:
                dst_coll.insert_many(new, ordered=False)
            except BulkWriteError as exc:   # a concurrent writer got there first: duplicates only
                if any(e.get("code") != 11000 for e in exc.details.get("writeErrors", [])):
                    raise
        batch.clear()

    for doc in src_coll.find({}):
        batch.append(doc)
        if len(batch) >= BATCH:
            flush()
    flush()
    return n


def backfill_ts(coll, dry_run: bool) -> int:
    """Sets `ts` from the string `timestamp` where it's missing. Returns how many rows (would) change."""
    n, ops = 0, []
    for doc in coll.find({"ts": {"$exists": False}}, {"timestamp": 1}):
        n += 1
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"ts": _history_ts(doc.get("timestamp"))}}))
        if len(ops) >= BATCH:
            if not dry_run:
                coll.bulk_write(ops, ordered=False)
            ops = []
    if ops and not dry_run:
        coll.bulk_write(ops, ordered=False)
    return n


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from-db", default="altinvest", help="the sentiment engine's old database (default: altinvest)")
    parser.add_argument("--dry-run", action="store_true", help="count what would change, write nothing")
    parser.add_argument(ALLOW_FLAG, dest="allow_remote", action="store_true", help="allow a non-local MongoDB")
    args = parser.parse_args(argv)

    uri = os.getenv("MONGO_URI")
    if not is_local(uri) and not args.allow_remote:
        scheme, hosts = uri_hosts(uri)
        sys.exit(f"refusing to migrate a non-local MongoDB ({scheme}://{','.join(hosts)}); "
                 f"pass {ALLOW_FLAG} to run it against this database on purpose.")

    client = get_client()
    target = db_name()
    dst = client[target]
    result = {"from": args.from_db, "to": target, "dry_run": args.dry_run}

    if args.from_db == target:
        result["copied"] = "skipped: source and target are the same database"
    elif args.from_db not in client.list_database_names():
        result["copied"] = f"skipped: no database named {args.from_db!r}"
    else:
        src = client[args.from_db]
        copied = {"sentiment": copy_latest(src, dst, args.dry_run)}
        for name in COPY_BY_ID:
            copied[name] = copy_by_id(src[name], dst[name], args.dry_run)
        result["copied"] = copied

    result["ts_backfilled"] = backfill_ts(dst.sentiment_history, args.dry_run)

    if not args.dry_run:
        from db.indexes import ensure_indexes
        idx = ensure_indexes()
        result["indexes"] = {"ok": idx["created_or_present"], "failed": idx["failed"]}

    print(result)
    return result


if __name__ == "__main__":
    main()
