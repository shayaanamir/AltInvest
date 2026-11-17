"""tools/cleanup_fictional_assets.py: matches only fictional rows, backs them up, deletes them, pulls watchlist items.

Needs MONGO_TEST_URI pointing at a throwaway MongoDB (like test_holdings_atomic.py); a random database is created and dropped.
"""
import importlib.util
import os
import uuid

import pytest
from bson import ObjectId, json_util

pymongo = pytest.importorskip("pymongo")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_spec = importlib.util.spec_from_file_location("cleanup", os.path.join(ROOT, "tools", "cleanup_fictional_assets.py"))
cleanup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cleanup)


@pytest.fixture
def db():
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        pytest.skip("set MONGO_TEST_URI to a throwaway MongoDB to run these")
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
    name = f"cleanup_test_{uuid.uuid4().hex[:8]}"
    yield client[name]
    client.drop_database(name)


def _fill(db):
    db.assets.insert_many([{"asset_id": "BASE", "symbol": "BASE"}, {"asset_id": "BTC", "symbol": "BTC"}])
    db.nft_collections.insert_many([{"slug": "astralcats"}, {"slug": "azuki"}])
    db.nft_market_data.insert_many([{"slug": "astralcats"}, {"slug": "astralcats"}, {"slug": "azuki"}])
    db.aai_scores.insert_many([{"asset_id": "BASE"}, {"asset_id": "BTC"}])
    hold = db.portfolio_holdings.insert_one({"asset_type": "crypto", "symbol": "BASE"}).inserted_id
    db.portfolio_holdings.insert_one({"asset_type": "crypto", "symbol": "BTC"})
    db.portfolio_transactions.insert_many([{"holding_id": hold, "symbol": "BASE"}, {"holding_id": ObjectId(), "symbol": "BTC"}])
    alert = db.alerts.insert_one({"target_type": "nft", "target_slug": "astralcats"}).inserted_id
    db.alert_triggers.insert_one({"alert_id": alert})
    db.watchlists.insert_one({"name": "mine", "items": [{"type": "nft", "symbol_or_slug": "astralcats"},
                                                        {"type": "crypto", "symbol_or_slug": "BTC"}]})


def test_dry_run_counts_only_fictional_rows(db):
    _fill(db)
    counts = cleanup.count(db, cleanup.plan(db, cleanup.FICTIONAL_SLUGS, cleanup.FICTIONAL_SYMBOLS))
    assert counts[("assets", "BASE")] == 1
    assert counts[("nft_market_data", "astralcats")] == 2
    assert counts[("portfolio_transactions", "BASE")] == 1
    assert counts[("alert_triggers", "astralcats")] == 1
    assert counts[("watchlists", "astralcats")] == 1
    assert sum(counts.values()) == 10
    assert db.assets.count_documents({}) == 2          # counting changed nothing


def test_backup_then_delete_keeps_real_rows(db, tmp_path):
    _fill(db)
    steps = cleanup.plan(db, cleanup.FICTIONAL_SLUGS, cleanup.FICTIONAL_SYMBOLS)
    path, n = cleanup.backup(db, steps, str(tmp_path))
    assert n == 10
    saved = json_util.loads(open(path, encoding="utf-8").read())["collections"]
    assert saved["assets"]["BASE"]["rows"][0]["asset_id"] == "BASE"

    cleanup.apply(db, steps)
    left = cleanup.count(db, cleanup.plan(db, cleanup.FICTIONAL_SLUGS, cleanup.FICTIONAL_SYMBOLS))
    assert sum(left.values()) == 0
    assert [a["asset_id"] for a in db.assets.find()] == ["BTC"]
    assert [c["slug"] for c in db.nft_collections.find()] == ["azuki"]
    assert db.portfolio_transactions.count_documents({}) == 1
    wl = db.watchlists.find_one({"name": "mine"})                    # the list stays, the fictional item goes
    assert [i["symbol_or_slug"] for i in wl["items"]] == ["BTC"]


def test_refuses_atlas_without_allow_remote(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://user:pw@example.mongodb.net/x")
    with pytest.raises(SystemExit) as exc:
        cleanup.main([])
    assert "refusing" in str(exc.value) and "pw" not in str(exc.value)
