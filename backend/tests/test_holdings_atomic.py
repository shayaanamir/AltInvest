"""Holdings: every change is one atomic MongoDB update (audit G-35).

Two layers:
  * fast tests with a recording fake collection: the filters and update pipelines, and how a refused
    update is explained (404 / 422 / 409);
  * live tests against a real MongoDB, which are what actually prove there is no lost update or
    oversell. They run only when MONGO_TEST_URI is set (a throwaway server, e.g.
    `docker run --rm -p 27099:27017 mongo:7` and MONGO_TEST_URI=mongodb://localhost:27099); each uses
    its own database and drops it afterwards.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from controllers import holdings_controller as hc

USER = ObjectId()
HID = ObjectId()


# ── fake collections ─────────────────────────────────────────────────────────

class Coll:
    """Records calls; `docs` are returned by find_one, `results` by find_one_and_update."""
    def __init__(self, docs=(), results=()):
        self.docs, self.results = list(docs), list(results)
        self.calls = []

    def find_one(self, flt, projection=None):
        self.calls.append(("find_one", flt))
        return next((d for d in self.docs if all(d.get(k) == v for k, v in flt.items())), None)

    def find_one_and_update(self, flt, update, **kw):
        self.calls.append(("find_one_and_update", flt, update, kw))
        return self.results.pop(0) if self.results else None

    def find_one_and_delete(self, flt, **kw):
        self.calls.append(("find_one_and_delete", flt))
        return self.results.pop(0) if self.results else None

    def delete_one(self, flt):
        self.calls.append(("delete_one", flt))
        return SimpleNamespace(deleted_count=1)

    def insert_one(self, doc):
        self.calls.append(("insert_one", doc))
        self.inserted = doc
        return SimpleNamespace(inserted_id=ObjectId())


@pytest.fixture
def fake(monkeypatch):
    db = SimpleNamespace(portfolio_holdings=Coll(), portfolio_transactions=Coll())
    monkeypatch.setattr(hc, "get_db", lambda: db)
    return db


def _stored(**kw):
    return {"_id": HID, "user_id": USER, "asset_type": "crypto", "symbol": "BTC", "quantity": 4.0,
            "avg_buy_price_usd": 100.0, **kw}


def _status(fn, *a):
    with pytest.raises(HTTPException) as e:
        fn(*a)
    return e.value.status_code, e.value.detail


def test_sell_matches_only_while_the_quantity_still_covers_it(fake):
    fake.portfolio_holdings.results = [_stored(quantity=3.0)]
    out = hc.trade(USER, str(HID), "sell", 1.0, 150.0)
    _, flt, pipeline, kw = fake.portfolio_holdings.calls[0]
    assert flt["quantity"]["$gte"] == pytest.approx(1.0 - hc._EPS)
    assert flt["user_id"] == USER and flt["asset_type"] == "crypto"
    assert isinstance(pipeline, list)                       # a pipeline update, evaluated inside Mongo
    assert out == {"status": "sold", "quantity": 3.0, "closed": False, "realised_pnl_usd": 50.0}
    assert fake.portfolio_transactions.inserted["quantity_after"] == 3.0   # history after the holding changed


def test_full_sell_closes_the_holding(fake):
    fake.portfolio_holdings.results = [_stored(quantity=0.0)]
    out = hc.trade(USER, str(HID), "sell", 4.0, 90.0)
    assert out == {"status": "sold", "quantity": 0.0, "closed": True, "realised_pnl_usd": -40.0}
    delete = [c for c in fake.portfolio_holdings.calls if c[0] == "delete_one"][0]
    assert delete[1]["quantity"] == {"$lte": hc._EPS}      # a buy that landed meanwhile keeps the row alive


def test_oversell_is_422_with_the_old_message(fake):
    fake.portfolio_holdings.docs = [_stored(quantity=2.0)]
    assert _status(hc.trade, USER, str(HID), "sell", 5.0, 100.0) == (422, "You hold 2; you can't sell 5.")


def test_someone_elses_or_missing_holding_is_404(fake):
    assert _status(hc.trade, USER, str(HID), "sell", 1.0, 100.0)[0] == 404
    assert _status(hc.trade, USER, str(HID), "buy", 1.0, 5.0)[0] == 404
    assert _status(hc.remove_holding, USER, str(HID))[0] == 404
    assert _status(hc.correct_holding, USER, str(HID), {"quantity": 1.0})[0] == 404


def test_nft_holdings_cannot_be_traded(fake):
    fake.portfolio_holdings.docs = [_stored(asset_type="nft")]
    assert _status(hc.trade, USER, str(HID), "buy", 1.0, 5.0)[0] == 422


def test_buy_is_one_pipeline_update_returning_the_new_document(fake):
    fake.portfolio_holdings.results = [_stored(quantity=6.0, avg_buy_price_usd=110.0)]
    out = hc.trade(USER, str(HID), "buy", 2.0, 130.0)
    _, flt, pipeline, kw = fake.portfolio_holdings.calls[0]
    assert flt == {"_id": HID, "user_id": USER, "asset_type": "crypto"}
    assert isinstance(pipeline, list) and kw["return_document"] is not None
    assert out == {"status": "bought", "quantity": 6.0, "closed": False}


def test_remove_records_history_only_when_it_deleted_something(fake):
    fake.portfolio_holdings.results = [_stored()]
    hc.remove_holding(USER, str(HID))
    assert fake.portfolio_transactions.inserted["type"] == "remove"
    assert fake.portfolio_holdings.calls[0][0] == "find_one_and_delete"


def test_correct_uses_literals_so_values_are_never_read_as_expressions(fake):
    fake.portfolio_holdings.results = [_stored()]
    hc.correct_holding(USER, str(HID), {"quantity": 9.0})
    pipeline = fake.portfolio_holdings.calls[0][2]
    assert pipeline[0] == {"$set": {"quantity": {"$literal": 9.0}}}


# ── live MongoDB ─────────────────────────────────────────────────────────────

MONGO_TEST_URI = os.getenv("MONGO_TEST_URI")
live = pytest.mark.skipif(not MONGO_TEST_URI, reason="set MONGO_TEST_URI to a throwaway MongoDB to run these")


@pytest.fixture
def mongo(monkeypatch):
    from pymongo import MongoClient
    from db.indexes import INDEXES
    client = MongoClient(MONGO_TEST_URI, serverSelectionTimeoutMS=3000, tz_aware=True)
    db = client[f"altinvest_test_{uuid.uuid4().hex[:10]}"]
    for keys, options in INDEXES["portfolio_holdings"]:
        db.portfolio_holdings.create_index(keys, **options)
    db.assets.insert_one({"asset_id": "BTC"})
    db.nft_collections.insert_one({"slug": "azuki"})
    monkeypatch.setattr(hc, "get_db", lambda: db)
    yield db
    client.drop_database(db.name)
    client.close()


def _insert(db, **kw):
    doc = {"user_id": USER, "asset_type": "crypto", "symbol": "BTC", "quantity": 10.0,
           "avg_buy_price_usd": 100.0, "cost_basis_usd": 1000.0, **kw}
    return str(db.portfolio_holdings.insert_one(doc).inserted_id)


def _race(fn, n):
    """Runs fn(i) on n threads at once; returns (results, http status codes of the failures)."""
    from threading import Barrier
    gate = Barrier(n)

    def run(i):
        gate.wait()
        try:
            return fn(i)
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(n) as pool:
        out = list(pool.map(run, range(n)))
    return [o for o in out if isinstance(o, dict)], [o for o in out if isinstance(o, int)]


@live
def test_live_parallel_sells_never_oversell(mongo):
    hid = _insert(mongo)                                   # holds 10
    ok, refused = _race(lambda i: hc.trade(USER, hid, "sell", 3.0, 120.0), 8)
    assert len(ok) == 3 and refused == [422] * 5           # 3 x 3 = 9 sold; the rest refused
    assert mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})["quantity"] == pytest.approx(1.0)
    assert mongo.portfolio_transactions.count_documents({"type": "sell"}) == 3


@live
def test_live_selling_everything_twice_at_once_closes_once(mongo):
    hid = _insert(mongo)
    ok, refused = _race(lambda i: hc.trade(USER, hid, "sell", 10.0, 100.0), 6)
    assert len(ok) == 1 and ok[0]["closed"] is True and len(refused) == 5
    assert mongo.portfolio_holdings.count_documents({}) == 0
    assert mongo.portfolio_transactions.count_documents({"type": "sell"}) == 1


@live
def test_live_parallel_buys_lose_no_update(mongo):
    hid = _insert(mongo, quantity=10.0, avg_buy_price_usd=100.0)
    ok, refused = _race(lambda i: hc.trade(USER, hid, "buy", 1.0, 200.0), 20)
    assert len(ok) == 20 and not refused
    h = mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})
    assert h["quantity"] == pytest.approx(30.0)
    assert h["avg_buy_price_usd"] == pytest.approx((10 * 100 + 20 * 200) / 30)
    assert h["cost_basis_usd"] == round(30 * h["avg_buy_price_usd"], 2)


@live
def test_live_maths_match_the_old_read_modify_write(mongo):
    hid = _insert(mongo, quantity=4.0, avg_buy_price_usd=110.0, cost_basis_usd=440.0)
    out = hc.trade(USER, hid, "buy", 2.0, 130.0)
    new_avg = (4 * 110 + 2 * 130) / 6
    h = mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})
    assert out == {"status": "bought", "quantity": 6.0, "closed": False}
    assert h["avg_buy_price_usd"] == pytest.approx(new_avg) and h["cost_basis_usd"] == round(6 * new_avg, 2)
    out = hc.trade(USER, hid, "sell", 1.5, 160.0)
    h = mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})
    assert out["realised_pnl_usd"] == round((160 - new_avg) * 1.5, 2) and out["quantity"] == pytest.approx(4.5)
    assert h["avg_buy_price_usd"] == pytest.approx(new_avg) and h["cost_basis_usd"] == round(4.5 * new_avg, 2)


@live
def test_live_a_holding_with_no_average_takes_the_buy_price(mongo):
    hid = _insert(mongo, avg_buy_price_usd=None, cost_basis_usd=None)
    hc.trade(USER, hid, "buy", 5.0, 50.0)
    assert mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})["avg_buy_price_usd"] == 50.0


@live
def test_live_parallel_adds_of_the_same_coin_make_one_row(mongo):
    ok, refused = _race(lambda i: hc.add_holding(
        USER, {"asset_type": "crypto", "symbol": "btc", "quantity": 1.0, "avg_buy_price_usd": 100.0 + i}), 12)
    assert len(ok) == 12 and not refused
    assert sum(1 for r in ok if not r["merged"]) == 1       # exactly one insert, the rest merged
    rows = list(mongo.portfolio_holdings.find({}))
    assert len(rows) == 1 and rows[0]["quantity"] == pytest.approx(12.0)
    assert rows[0]["avg_buy_price_usd"] == pytest.approx(sum(100.0 + i for i in range(12)) / 12)


@live
def test_live_parallel_adds_of_the_same_nft_token_succeed_once_and_409_the_rest(mongo):
    payload = {"asset_type": "nft", "nft_collection_slug": "azuki", "nft_token_id": "42", "quantity": 1.0}
    ok, refused = _race(lambda i: hc.add_holding(USER, dict(payload)), 6)
    assert len(ok) == 1 and refused == [409] * 5
    assert mongo.portfolio_holdings.count_documents({"asset_type": "nft"}) == 1


@live
def test_live_correct_recomputes_cost_basis_for_crypto_and_nft(mongo):
    hid = _insert(mongo)
    hc.correct_holding(USER, hid, {"quantity": 2.0, "avg_buy_price_usd": 50.0})
    h = mongo.portfolio_holdings.find_one({"_id": ObjectId(hid)})
    assert h["quantity"] == 2.0 and h["cost_basis_usd"] == 100.0
    adj = mongo.portfolio_transactions.find_one({"type": "adjust"})
    assert adj["before"]["quantity"] == 10.0 and adj["after"]["cost_basis_usd"] == 100.0

    nid = _insert(mongo, asset_type="nft", symbol=None, nft_collection_slug="azuki", nft_token_id="1",
                  quantity=1.0, avg_buy_price_usd=None, avg_buy_price_eth=2.0, avg_buy_eth_usd_rate=3000.0)
    hc.correct_holding(USER, nid, {"avg_buy_price_eth": 3.0})
    assert mongo.portfolio_holdings.find_one({"_id": ObjectId(nid)})["cost_basis_usd"] == 9000.0


@live
def test_live_remove_twice_records_one_removal(mongo):
    hid = _insert(mongo)
    ok, refused = _race(lambda i: hc.remove_holding(USER, hid) or {}, 4)
    assert len(ok) == 1 and refused == [404] * 3
    assert mongo.portfolio_transactions.count_documents({"type": "remove"}) == 1
