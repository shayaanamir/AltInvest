"""
db/cleanup_seeded_ml_rows.py

Removes the prediction, risk, risk-breakdown and AAI rows that older seeds typed in (ml/docs/DECISIONS.md D94):
db/seed_predictions_risk.py and db/seed_aai_scores.py (both deleted) wrote invented forecasts (model_version
"seed-v1", e.g. LINK +5 % to $17.22), risk scores, risk breakdowns and AAI scores. After this the pages show only
what the ML pull and the AAI refresh store, or "not covered" / "missing inputs".

What counts as real, and is kept:
  predictions, risk_scores   rows with source "ml-service" (written only by controllers/ml_pull_controller.py)
  risk_breakdown             rows with a `source` field (none exist before Stage 2 of D94; every older row is seeded)
  aai_scores (crypto)        rows whose model_version is an ML price model ("baseline-last-value"): computed by the
                             AAI refresh from an ML prediction. Rows computed from a seeded prediction carry
                             "seed-v1" and are removed, as are the "mock-v1" rows (db/cleanup_mock_aai.py).
NFT rows are not touched.

    python db/cleanup_seeded_ml_rows.py                          dry run: counts per collection and asset
    python db/cleanup_seeded_ml_rows.py --backup DIR             dry run, and writes the matching rows to DIR
    python db/cleanup_seeded_ml_rows.py --backup DIR --confirm   writes the backup, then deletes
    python db/cleanup_seeded_ml_rows.py --restore FILE           puts a backup's rows back (same _id; existing kept)
    ... --allow-remote                                           needed for any non-local MongoDB (Atlas)

--confirm without --backup is refused. DIR must be outside the repository (the rows are data, never committed,
as for db backups, D93). The backup is MongoDB Extended JSON (canonical), so _ids, dates and numbers come back
exactly.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
REPO_ROOT = Path(__file__).resolve().parent.parent

ML_PRICE_MODEL_VERSIONS = ("baseline-last-value",)    # ml/config.py MODEL_VERSION_PRICE

# collection -> Mongo filter that matches the rows to REMOVE
FILTERS = {
    "predictions": {"source": {"$ne": "ml-service"}},
    "risk_scores": {"source": {"$ne": "ml-service"}},
    "risk_breakdown": {"source": {"$exists": False}},
    "aai_scores": {"target_type": {"$ne": "nft"}, "model_version": {"$nin": list(ML_PRICE_MODEL_VERSIONS)}},
}


def _key(doc: dict) -> str:
    return str(doc.get("asset") or doc.get("target_id") or "?")


def plan(db) -> dict:
    """{collection: {"remove": n, "keep": n, "assets": {asset: n removed}}}; reads only."""
    out = {}
    for name, flt in FILTERS.items():
        coll = db[name]
        assets = {}
        for doc in coll.find(flt, {"asset": 1, "target_id": 1}):
            assets[_key(doc)] = assets.get(_key(doc), 0) + 1
        removed = sum(assets.values())
        out[name] = {"remove": removed, "keep": coll.count_documents({}) - removed, "assets": dict(sorted(assets.items()))}
    return out


def backup_rows(db, out_dir: Path, now: datetime | None = None) -> Path:
    """Writes every row the filters match to out_dir as Extended JSON; returns the file. Refuses a repo folder."""
    from bson import json_util
    out_dir = Path(out_dir).resolve()
    if out_dir == REPO_ROOT or REPO_ROOT in out_dir.parents:
        raise SystemExit(f"refusing to write a backup inside the repository ({out_dir}); choose a folder outside it")
    now = now or datetime.now(timezone.utc)
    rows = {name: list(db[name].find(flt)) for name, flt in FILTERS.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"cleanup_seeded_ml_rows_{db.name}_{now:%Y%m%dT%H%M%SZ}.json"
    body = {"database": db.name, "written_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "filters": FILTERS, "rows": rows}
    path.write_text(json_util.dumps(body, json_options=json_util.CANONICAL_JSON_OPTIONS, indent=1), encoding="utf-8")
    return path


def restore(db, path: Path) -> dict:
    """Inserts a backup's rows again; a row whose _id is already there is left as it is. {collection: n inserted}."""
    from bson import json_util
    body = json_util.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for name, rows in body["rows"].items():
        missing = [r for r in rows if not db[name].find_one({"_id": r["_id"]})]
        if missing:
            db[name].insert_many(missing)
        out[name] = len(missing)
    return out


def run(db, confirm: bool, backup_dir: Path | None = None) -> dict:
    """Dry run unless confirm; confirm needs backup_dir, and the backup is written before anything is deleted."""
    if confirm and backup_dir is None:
        raise SystemExit("--confirm needs --backup DIR: the rows are written there before anything is deleted")
    report = plan(db)
    if backup_dir is not None:
        report["_backup"] = str(backup_rows(db, backup_dir))
    if confirm:
        for name, flt in FILTERS.items():
            report[name]["deleted"] = db[name].delete_many(flt).deleted_count
    return report


def _option(argv, name):
    if name not in argv:
        return None
    i = argv.index(name)
    if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
        raise SystemExit(f"{name} needs a path")
    return Path(argv[i + 1])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from db.seed_guard import require_local_target
    require_local_target(["cleanup", *argv])             # local MongoDB only, unless --allow-remote
    from db.mongo_connection import get_db
    db = get_db()
    restore_file = _option(argv, "--restore")
    if restore_file is not None:
        print(f"database: {db.name}  restored {restore(db, restore_file)}")
        return 0
    confirm, backup_dir = "--confirm" in argv, _option(argv, "--backup")
    if confirm and backup_dir is None:
        raise SystemExit("--confirm needs --backup DIR: the rows are written there before anything is deleted")
    print(f"database: {db.name}  ({'DELETING' if confirm else 'dry run, nothing deleted'})")
    report = run(db, confirm, backup_dir)
    for name in FILTERS:
        r = report[name]
        done = f", deleted {r['deleted']}" if "deleted" in r else ""
        print(f"  {name:15} remove {r['remove']:4}  keep {r['keep']:4}{done}")
        for asset, n in r["assets"].items():
            print(f"      {asset:8} {n}")
    if "_backup" in report:
        print(f"backup: {report['_backup']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
