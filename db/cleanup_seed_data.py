"""
db/cleanup_seed_data.py
Removes rows that came from the demo seeds (ml/docs/DECISIONS.md D91). DRY RUN BY DEFAULT: it only counts.

Rules (each one names the seed that wrote the rows; real rows carry a `source` such as "ml-service" or
"binance-klines-1h", or a real model_version):
  prices, asset_market_data, risk_scores, risk_breakdown  no `source`        (seed_prices, seed_assets,
                                                                            seed_predictions_risk)
  predictions                                    no `source` or model_version "seed-v1"
  aai_scores                                     model_version "seed-v1"   (real rows are computed daily and
                                                                            carry no source, so "no source"
                                                                            is NOT a rule here)
  market_insights / sentiment_themes             the titles / labels db/seed_insights.py writes
  nft_collections                                the 4 fictional slugs (db/seed_nft.py FICTIONAL_SLUGS)
  nft_market_data, nft_sales, nft_holder_stats,  the fictional slugs, and rows without `source` (the old seed's
  nft_liquidity, nft_risk_breakdown, nft_traits, made-up numbers; db/seed_nft.py SEEDED_NUMBER_TABLES)
  nft_tokens, nft_token_*_history
User collections (users, holdings, transactions, watchlists, alerts, notifications, settings, snapshots) are never
deleted from. References from them to seed items are reported.

Assets with no real price source (in `assets`, not in REAL_PRICE_ASSETS): after the rules they have no price,
chart or market row. --unsourced-assets keep (default: list them only) | hide (set assets.hidden = true; lists,
search and the detail page skip them, holdings still resolve them) | delete (delete the asset documents).
--prune-watchlists also removes watchlist items that point at deleted fictional collections (and, with
--unsourced-assets delete, at the deleted assets). Holdings, transactions and alerts are only reported.

    python -m db.cleanup_seed_data                                   # dry run on MONGO_URI, prints counts
    python -m db.cleanup_seed_data --json out.json                   # also writes the counts as JSON
    python -m db.cleanup_seed_data --confirm                         # deletes, local MongoDB only
    python -m db.cleanup_seed_data --confirm --allow-remote          # deletes on a remote (Atlas) database
Real deletes need --confirm, and on a non-local database also --allow-remote (db/seed_guard.py). Take a
backup first (db/BACKUP.md). Only hosts are printed, never credentials.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json

from db.seed_guard import ALLOW_FLAG, require_local_target, uri_hosts
from db.seed_insights import INSIGHTS, THEMES
from db.seed_nft import FICTIONAL_SLUGS, SEEDED_NUMBER_TABLES

REAL_PRICE_ASSETS = ("BTC", "ETH", "SOL")    # = backend/controllers/price_feed.py SYMBOLS (tested)
NO_SOURCE = {"source": {"$exists": False}}
FICTIONAL = {"slug": {"$in": list(FICTIONAL_SLUGS)}}

RULES = [
    ("prices", NO_SOURCE, "simulated hourly prices (db/seed_prices.py)"),
    ("asset_market_data", NO_SOURCE, "seeded price, change, market cap, rank, supply (db/seed_assets.py)"),
    ("predictions", {"$or": [NO_SOURCE, {"model_version": "seed-v1"}]}, "seeded predictions (seed_predictions_risk)"),
    ("risk_scores", NO_SOURCE, "seeded risk scores (db/seed_predictions_risk.py)"),
    ("risk_breakdown", NO_SOURCE, "seeded 4-part risk breakdown (db/seed_predictions_risk.py)"),
    ("aai_scores", {"model_version": "seed-v1"}, "seeded AAI scores (old seed_aai_scores)"),
    ("market_insights", {"title": {"$in": [i["title"] for i in INSIGHTS]}}, "seeded headlines (db/seed_insights.py)"),
    ("sentiment_themes", {"label": {"$in": [t["label"] for t in THEMES]}}, "seeded themes (db/seed_insights.py)"),
    ("nft_collections", FICTIONAL, "the 4 fictional collections"),
] + [(t, {"$or": [FICTIONAL, NO_SOURCE]}, "fictional collections and the old seed's made-up NFT rows")
     for t in SEEDED_NUMBER_TABLES]

UNSOURCED_LOSES = [
    "price, 24h/7d change, market cap, rank, supply and volume (their only market rows are seeded)",
    "the price chart and sparkline (their only price rows are simulated)",
    "a place in Discover, the dashboard lists, compare and trending (built from asset_market_data)",
    "seeded prediction, risk score, risk breakdown and AAI (no ML coverage, so nothing replaces them)",
]


def plan(db) -> list[dict]:
    """[{collection, matched, total, why}] for every rule; read-only."""
    names = set(db.list_collection_names())
    out = []
    for coll, flt, why in RULES:
        if coll not in names:
            out.append({"collection": coll, "matched": 0, "total": 0, "why": why})
            continue
        out.append({"collection": coll, "matched": db[coll].count_documents(flt),
                    "total": db[coll].count_documents({}), "why": why})
    return out


def _watch_refs(db, kind: str, ids) -> dict:
    """{id: number of watchlist items pointing at it}."""
    refs = {}
    for w in db.watchlists.find({}, {"_id": 0, "items": 1}):
        for item in w.get("items") or []:
            if item.get("type") == kind and item.get("symbol_or_slug") in ids:
                refs[item["symbol_or_slug"]] = refs.get(item["symbol_or_slug"], 0) + 1
    return refs


def unsourced_assets(db) -> list[dict]:
    """Assets without a real price source, with what references them; read-only."""
    ids = sorted(a["asset_id"] for a in db.assets.find({"asset_id": {"$nin": list(REAL_PRICE_ASSETS)}},
                                                      {"_id": 0, "asset_id": 1}))
    watch = _watch_refs(db, "crypto", set(ids))
    out = []
    for a in ids:
        out.append({
            "asset_id": a,
            "watchlist_items": watch.get(a, 0),
            "holdings": db.portfolio_holdings.count_documents({"symbol": a}),
            "transactions": db.portfolio_transactions.count_documents({"symbol": a}),
            "alerts": db.alerts.count_documents({"target_symbol": a}),
            "real_rows_left": {c: db[c].count_documents({"asset": a, "source": {"$exists": True}})
                               for c in ("prices", "predictions", "risk_scores")},
        })
    return out


def fictional_watchlist_refs(db) -> dict:
    return _watch_refs(db, "nft", set(FICTIONAL_SLUGS))


def apply(db, unsourced_mode: str = "keep", prune_watchlists: bool = False) -> dict:
    """Deletes what plan() counts; then the unsourced-asset and watchlist options. Returns what changed."""
    unsourced = [u["asset_id"] for u in unsourced_assets(db)]
    done = {coll: db[coll].delete_many(flt).deleted_count for coll, flt, _ in RULES}
    if unsourced_mode == "hide":
        done["assets hidden"] = db.assets.update_many({"asset_id": {"$in": unsourced}},
                                                      {"$set": {"hidden": True}}).modified_count
    elif unsourced_mode == "delete":
        done["assets deleted"] = db.assets.delete_many({"asset_id": {"$in": unsourced}}).deleted_count
    if prune_watchlists:
        gone = [{"type": "nft", "symbol_or_slug": {"$in": list(FICTIONAL_SLUGS)}}]
        if unsourced_mode == "delete":
            gone.append({"type": "crypto", "symbol_or_slug": {"$in": unsourced}})
        done["watchlists changed"] = sum(
            db.watchlists.update_many({}, {"$pull": {"items": g}}).modified_count for g in gone)
    return done


def report(db) -> dict:
    return {"rules": plan(db), "unsourced_assets": unsourced_assets(db),
            "unsourced_assets_lose": UNSOURCED_LOSES, "fictional_collection_watchlist_items": fictional_watchlist_refs(db)}


def _print(rep: dict) -> None:
    print(f"{'collection':30} {'would delete':>12} {'of':>8}  why")
    for r in rep["rules"]:
        print(f"{r['collection']:30} {r['matched']:>12} {r['total']:>8}  {r['why']}")
    print("\nAssets with no real price source (kept unless --unsourced-assets hide|delete):")
    for u in rep["unsourced_assets"]:
        print(f"  {u['asset_id']:6} watchlist items {u['watchlist_items']}, holdings {u['holdings']}, "
              f"transactions {u['transactions']}, alerts {u['alerts']}, real rows left {u['real_rows_left']}")
    print("  They lose: " + "; ".join(rep["unsourced_assets_lose"]))
    print(f"\nWatchlist items pointing at fictional collections: {rep['fictional_collection_watchlist_items']}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Remove demo seed rows (dry run unless --confirm)")
    p.add_argument("--confirm", action="store_true", help="really delete (default: dry run, counts only)")
    p.add_argument(ALLOW_FLAG, dest="allow_remote", action="store_true", help="allow a non-local database")
    p.add_argument("--unsourced-assets", choices=("keep", "hide", "delete"), default="keep")
    p.add_argument("--prune-watchlists", action="store_true")
    p.add_argument("--json", help="also write the dry-run counts to this file")
    args = p.parse_args(argv)
    from db.mongo_connection import get_db
    scheme, hosts = uri_hosts(os.getenv("MONGO_URI"))
    print(f"[cleanup] target {scheme}://{','.join(hosts)} / {os.getenv('MONGO_DB_NAME')}"
          f" ({'DELETING' if args.confirm else 'dry run: nothing is changed'})")
    db = get_db()
    rep = report(db)
    _print(rep)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, default=str)
    if not args.confirm:
        print("\nDry run. Take a backup (db/BACKUP.md), then re-run with --confirm (and --allow-remote for Atlas).")
        return 0
    require_local_target(["cleanup"] + (["--allow-remote"] if args.allow_remote else []),
                         action="clean up", why="the cleanup deletes rows")
    print(f"\n[cleanup] done: {apply(db, args.unsourced_assets, args.prune_watchlists)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
