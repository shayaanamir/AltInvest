"""
tools/cleanup_fictional_assets.py

Removes the made-up assets that early seed scripts wrote: the four fictional NFT collections (Astral Cats,
Neon Drifters, Pixel Wardens, Genesis Punks) and the fictional "Base Ecosystem Index" coin (BASE), with every
row tied to them: NFT market data, sales, tokens, traits, risk, liquidity, holder stats, sentiment, AAI scores,
alerts and their triggers, notifications, portfolio holdings and their transactions, and watchlist items.

Dry run by default: prints how many rows match, per collection and per target, and changes nothing.

    python tools/cleanup_fictional_assets.py                           # dry run (counts only)
    python tools/cleanup_fictional_assets.py --backup                  # dry run + JSON backup of every matched row
    python tools/cleanup_fictional_assets.py --confirm                 # backup, then delete, then re-count

--confirm always writes the backup first and stops if it can't. Like the seed scripts, it refuses a non-local
MongoDB (Atlas) unless --allow-remote is given. Watchlists are user lists: only the fictional items are pulled
out of them; the lists themselves stay. Nothing is ever printed from the connection string but its host.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
try:
    import db.mongo_connection  # noqa: F401  (PYTHONPATH may point at another checkout on purpose)
except ImportError:
    sys.path.insert(0, ROOT)

from bson import json_util  # noqa: E402

FICTIONAL_SLUGS = ["astralcats", "neondrifters", "pixelwardens", "genesispunks"]
FICTIONAL_SYMBOLS = ["BASE"]
DEFAULT_BACKUP_DIR = os.path.join(ROOT, "..", "backups")

# Collections keyed by an NFT slug (every one of them holds per-collection rows only).
NFT_SLUG_COLLECTIONS = [
    "nft_collections", "nft_market_data", "nft_sales", "nft_tokens", "nft_traits", "nft_item_values",
    "nft_holder_stats", "nft_liquidity", "nft_risk_breakdown", "nft_sentiment", "nft_sentiment_history",
    "nft_token_sale_history", "nft_token_ownership_history",
]
# Collections keyed by a coin symbol.
COIN_COLLECTIONS = [
    "assets", "asset_market_data", "prices", "predictions", "risk_scores", "risk_breakdown", "sentiment",
    "sentiment_history",
]
COIN_FIELDS = ("asset_id", "symbol", "asset")


def _sym_variants(symbols):
    return sorted({v for s in symbols for v in (s, s.upper(), s.lower())})


def plan(db, slugs, symbols):
    """[(collection, target, filter, action)]. action is "delete" or ("pull", array_field, item_filter)."""
    syms = _sym_variants(symbols)
    out = []
    for c in NFT_SLUG_COLLECTIONS:
        for s in slugs:
            out.append((c, s, {"slug": s}, "delete"))
    for c in COIN_COLLECTIONS:
        for s in symbols:
            v = [x for x in syms if x.upper() == s.upper()]
            out.append((c, s, {"$or": [{f: {"$in": v}} for f in COIN_FIELDS]}, "delete"))
    for t in slugs + symbols:
        v = [t] if t in slugs else [x for x in syms if x.upper() == t.upper()]
        out.append(("aai_scores", t, {"asset_id": {"$in": v}}, "delete"))
        alert_f = {"target_slug": t} if t in slugs else {"target_symbol": {"$in": v}}
        out.append(("alerts", t, alert_f, "delete"))
        alert_ids = [a["_id"] for a in db.alerts.find(alert_f, {"_id": 1})]
        alert_ids += [str(i) for i in alert_ids]
        out.append(("alert_triggers", t, {"alert_id": {"$in": alert_ids}}, "delete"))
        link_f = {"link.slug": t} if t in slugs else {"link.symbol": {"$in": v}}
        out.append(("notifications", t, link_f, "delete"))
        hold_f = {"collection_slug": t} if t in slugs else {"asset_type": "crypto", "symbol": {"$in": v}}
        out.append(("portfolio_holdings", t, hold_f, "delete"))
        hold_ids = [h["_id"] for h in db.portfolio_holdings.find(hold_f, {"_id": 1})]
        hold_ids += [str(i) for i in hold_ids]
        txn_f = {"$or": [{"holding_id": {"$in": hold_ids}},
                         ({"collection_slug": t} if t in slugs else {"symbol": {"$in": v}})]}
        out.append(("portfolio_transactions", t, txn_f, "delete"))
        out.append(("watchlists", t, {"items.symbol_or_slug": {"$in": v}},
                    ("pull", "items", {"symbol_or_slug": {"$in": v}})))
    return out


def count(db, steps):
    """{(collection, target): n} — for pulls, the number of lists that hold the item."""
    return {(c, t): db[c].count_documents(f) for c, t, f, _ in steps}


def print_table(counts, title):
    print(f"\n{title}")
    print(f"{'collection':32} {'target':16} {'rows':>6}")
    total = 0
    for (c, t), n in sorted(counts.items()):
        if n:
            print(f"{c:32} {t:16} {n:>6}")
            total += n
    print(f"{'total':49} {total:>6}")
    return total


def backup(db, steps, backup_dir):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.abspath(os.path.join(backup_dir, f"fictional-assets-{stamp}.json"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    for c, t, f, action in steps:
        rows = list(db[c].find(f))
        if rows:
            data.setdefault(c, {})[t] = {"action": action if action == "delete" else "pull", "rows": rows}
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json_util.dumps({"created_at": stamp, "collections": data}, indent=1))
    # Read it back: a backup that can't be parsed is no backup.
    with open(path, encoding="utf-8") as fh:
        back = json_util.loads(fh.read())
    n = sum(len(v["rows"]) for per in back["collections"].values() for v in per.values())
    return path, n


def apply(db, steps):
    done = {}
    for c, t, f, action in steps:
        if action == "delete":
            done[(c, t)] = db[c].delete_many(f).deleted_count
        else:
            _, field, item_f = action
            done[(c, t)] = db[c].update_many(f, {"$pull": {field: item_f}}).modified_count
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backup", action="store_true", help="write a JSON backup of every matched row")
    ap.add_argument("--confirm", action="store_true", help="back up, then delete")
    ap.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR)
    ap.add_argument("--allow-remote", action="store_true", help="allow a non-local MongoDB (Atlas)")
    args = ap.parse_args(argv)

    from db.seed_guard import require_local_target, uri_hosts
    require_local_target(["cleanup"] + (["--allow-remote"] if args.allow_remote else []))
    from db.mongo_connection import get_db
    db = get_db()
    scheme, hosts = uri_hosts(os.getenv("MONGO_URI"))
    print(f"target: {scheme}://{','.join(hosts)} / {db.name}   mode: {'DELETE' if args.confirm else 'dry run'}")

    steps = plan(db, FICTIONAL_SLUGS, FICTIONAL_SYMBOLS)
    before = count(db, steps)
    total = print_table(before, "Matching rows (watchlists: lists holding the item; only the item is removed)")

    if args.backup or args.confirm:
        path, n = backup(db, steps, args.backup_dir)
        print(f"\nbackup: {path}  ({n} rows, read back OK)")
        if n < total:
            sys.exit("backup has fewer rows than matched; nothing deleted")

    if not args.confirm:
        print("\ndry run: nothing changed. Re-run with --confirm to delete.")
        return 0

    done = apply(db, steps)
    print_table(done, "Deleted / pulled")
    left = print_table(count(db, plan(db, FICTIONAL_SLUGS, FICTIONAL_SYMBOLS)), "Re-count (expect 0)")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
