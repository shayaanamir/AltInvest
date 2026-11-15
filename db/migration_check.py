"""
db/migration_check.py
READ-ONLY comparison before moving all app data to one database (ml/docs/DECISIONS.md D92): which REAL rows
(rows with a `source`) are in the SOURCE database (default: the local container's aaip_db) but missing from the
TARGET database (MONGO_URI / MONGO_DB_NAME, Atlas in the dev setup), or newer in the source. Nothing is written
to either database; only hosts are printed, never credentials.

    python -m db.migration_check                       # inside the backend container (sees both databases)
    python -m db.migration_check --json out.json
    python -m db.migration_check --source-uri mongodb://mongodb:27017 --source-db aaip_db

Rows are matched on the same keys the writers upsert on (db/queries.py, controllers/*). "Newer" compares
pulled_at, then timestamp / fetched_at / updated_at. The proposal column says how to fill each gap: RE-PULL
(the ML or price feed serves that history again) or COPY (only the source database still has it), or SKIP.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json

from db.seed_guard import uri_hosts

# collection: (upsert key, how to fill a gap, why)
SPECS = {
    "ml_past_ranges": (("asset",), "RE-PULL", "the ML serves the whole series on every call (Phase 11 pull)"),
    "predictions": (("asset", "date"), "COPY", "one row per day; the ML serves only today's"),
    "risk_scores": (("asset", "date"), "COPY", "one row per day; the ML serves only today's"),
    "nft_market_data": (("slug", "date"), "RE-PULL", "the ML /nft/{slug}/floor serves the floor history"),
    "nft_liquidity": (("slug", "date"), "COPY", "one row per day; the ML serves only today's"),
    "nft_risk_breakdown": (("slug", "date"), "COPY", "one row per day; the ML serves only today's"),
    "nft_sales": (("slug", "tx", "token_id", "seller", "buyer"), "COPY",
                  "the pull asks for the last 30 days only; older sales exist only here"),
    "nft_item_values": (("slug", "token_id"), "RE-PULL", "latest estimate per held token; the pull refreshes it"),
    "fx_rates": (("base", "as_of"), "SKIP", "only the latest rate is used; the backend refetches it"),
    "prices": (("asset", "timestamp"), "SKIP", "dev-loader daily closes; the price feed backfill replaces them"),
    "portfolio_snapshots": (("user_id", "snapshot_date"), "SKIP", "belong to the local users, not Atlas users"),
}
TIME_FIELDS = ("pulled_at", "timestamp", "fetched_at", "updated_at")


def _when(doc):
    for f in TIME_FIELDS:
        if doc.get(f) is not None:
            return doc[f]
    return None


def _naive(t):
    return t.replace(tzinfo=None) if hasattr(t, "tzinfo") and t.tzinfo is not None else t


def compare(src, dst, coll: str, keys: tuple) -> dict:
    proj = {"_id": 0, **{k: 1 for k in keys}, **{f: 1 for f in TIME_FIELDS}}
    have = {}
    for d in dst[coll].find({}, proj):
        have[tuple(d.get(k) for k in keys)] = _when(d)
    real = missing = newer = 0
    first = last = None
    for d in src[coll].find({"source": {"$exists": True}}, {**proj, "date": 1, "snapshot_date": 1}):
        real += 1
        key = tuple(d.get(k) for k in keys)
        mark = d.get("date") or d.get("snapshot_date") or d.get("timestamp")
        if key not in have:
            missing += 1
            first = mark if first is None or str(mark) < str(first) else first
            last = mark if last is None or str(mark) > str(last) else last
            continue
        t_src, t_dst = _when(d), have[key]
        if t_src is not None and t_dst is not None and _naive(t_src) > _naive(t_dst):
            newer += 1
    return {"real_rows_in_source": real, "missing_in_target": missing, "newer_in_source": newer,
            "missing_from": str(first)[:19] if first else None, "missing_to": str(last)[:19] if last else None}


def build(src, dst) -> dict:
    out, src_names = {}, set(src.list_collection_names())
    for coll, (keys, how, why) in SPECS.items():
        if coll not in src_names:
            continue
        out[coll] = {**compare(src, dst, coll, keys), "key": list(keys), "proposal": how, "why": why}
    unknown = sorted(c for c in src_names - set(SPECS) if src[c].count_documents({"source": {"$exists": True}}))
    return {"collections": out, "real_collections_without_a_rule": unknown}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Read-only: real rows in the source DB missing or newer than in the target")
    p.add_argument("--source-uri", default="mongodb://mongodb:27017")
    p.add_argument("--source-db", default="aaip_db")
    p.add_argument("--json")
    args = p.parse_args(argv)
    from pymongo import MongoClient
    from db.mongo_connection import get_db
    src = MongoClient(args.source_uri, serverSelectionTimeoutMS=10000)[args.source_db]
    dst = get_db()
    s_scheme, s_hosts = uri_hosts(args.source_uri)
    d_scheme, d_hosts = uri_hosts(os.getenv("MONGO_URI"))
    print(f"[migration-check] read-only. source {s_scheme}://{','.join(s_hosts)} / {args.source_db} -> "
          f"target {d_scheme}://{','.join(d_hosts)} / {os.getenv('MONGO_DB_NAME')}")
    rep = build(src, dst)
    print(f"{'collection':22} {'real':>6} {'missing':>8} {'newer':>6}  {'missing dates':25} proposal")
    for c, r in rep["collections"].items():
        span = f"{r['missing_from'] or ''}..{r['missing_to'] or ''}" if r["missing_in_target"] else ""
        print(f"{c:22} {r['real_rows_in_source']:>6} {r['missing_in_target']:>8} {r['newer_in_source']:>6}  "
              f"{span[:25]:25} {r['proposal']}: {r['why']}")
    print(f"real collections without a rule: {rep['real_collections_without_a_rule']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
