"""
Audit Step 4 (robustness): Mongo client settings, /health, scheduler claims, sentiment_history TTL,
one database variable, and the sentiment-DB migration. No database is needed: everything that would
touch Mongo is replaced with small fakes.
"""
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import db.mongo_connection as mc


# ── N-06 / G-26 / G-29: the Mongo client ──────────────────────────────────────

def test_client_is_tz_aware_with_bounded_timeouts(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, uri, **kwargs):
            seen["uri"], seen["kwargs"] = uri, kwargs

    monkeypatch.setattr(mc, "MongoClient", FakeClient)
    monkeypatch.setattr(mc, "_client", None)
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017")
    mc.get_client()
    kw = seen["kwargs"]
    assert kw["tz_aware"] is True
    for key in ("serverSelectionTimeoutMS", "connectTimeoutMS", "socketTimeoutMS"):
        assert 0 < kw[key] <= 30_000, key
    assert kw["serverSelectionTimeoutMS"] <= 5000


def test_missing_uri_or_db_name_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(mc, "_client", None)
    monkeypatch.delenv("MONGO_URI", raising=False)
    with pytest.raises(mc.MongoConfigError, match="MONGO_URI"):
        mc.get_client()
    monkeypatch.delenv("MONGO_DB_NAME", raising=False)
    monkeypatch.delenv("MONGO_DB", raising=False)
    with pytest.raises(mc.MongoConfigError, match="MONGO_DB_NAME"):
        mc.db_name()


def test_db_name_prefers_mongo_db_name(monkeypatch):
    monkeypatch.setenv("MONGO_DB_NAME", "main_db")
    monkeypatch.setenv("MONGO_DB", "old_db")
    assert mc.db_name() == "main_db"
    monkeypatch.delenv("MONGO_DB_NAME")
    assert mc.db_name() == "old_db"


def test_aai_cache_hits_for_a_tz_aware_timestamp(monkeypatch):
    """With tz_aware reads the cached AAI row is fresh, so the route serves it without recomputing."""
    import db.queries as q
    import controllers.aai_controller as aai
    from routes.assets import get_asset_intelligence

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(q, "get_asset", lambda s: {"asset_id": s})
    monkeypatch.setattr(q, "get_latest_aai_score", lambda t, s: {
        "aai_score": 61.0, "pred_score": 55.0, "sentiment_score": 60.0, "risk_score": 40.0,
        "timestamp": now - timedelta(minutes=5),
    })
    monkeypatch.setattr(aai, "compute_aai_response", lambda *a, **k: pytest.fail("cache should have hit"))
    out = get_asset_intelligence("btc")
    assert out["aai_score"] == 61.0
    assert out["timestamp"].endswith("Z")


# ── G-26: /health ─────────────────────────────────────────────────────────────

@pytest.fixture
def health_client():
    from fastapi import FastAPI
    from routes import health
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app), health


def test_health_ok_reports_job_runs(monkeypatch, health_client):
    client, health = health_client
    last = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)

    class Runs:
        def find(self, *_a, **_k):
            return self

        def limit(self, _n):
            return [{"_id": "alerts", "last_run": last}, {"_id": "fx-rates"}]

    monkeypatch.setattr(health, "ping", lambda: None)
    monkeypatch.setattr(health, "get_db", lambda: SimpleNamespace(scheduler_runs=Runs()))
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["jobs"] == {"alerts": "2026-11-16T10:00:00Z", "fx-rates": None}
    assert "owner" not in r.text


def test_health_is_503_when_the_database_is_down(monkeypatch, health_client):
    client, health = health_client

    def down():
        raise RuntimeError("mongodb://user:secret@host: timed out")

    monkeypatch.setattr(health, "ping", down)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "unavailable" and r.json()["database"] == "unreachable"
    assert "secret" not in r.text


# ── G-13: every scheduler claims its run ──────────────────────────────────────

class _Stop(BaseException):
    """Ends a scheduler loop at its first non-zero sleep (BaseException: the loops catch Exception)."""


def _schedulers():
    import controllers.snapshot_controller as snap
    import controllers.fx_controller as fx
    import controllers.aai_controller as aai
    import controllers.alert_controller as alerts
    import controllers.ml_pull_controller as ml
    return [
        ("portfolio-snapshots", snap, "record_snapshots", lambda: 0, snap.run_snapshot_scheduler),
        ("fx-rates", fx, "refresh_rates", lambda: {"base": "USD", "as_of": "2026-11-16"}, fx.run_fx_scheduler),
        ("aai-refresh", aai, "refresh_all_aai_scores", lambda: {"stored": [], "skipped": []},
         lambda: aai.run_aai_refresh_scheduler(0)),
        ("alerts", alerts, "evaluate_alerts", lambda: {"triggered": 0}, lambda: alerts.run_alert_scheduler(0)),
        ("ml-pull", ml, "pull_all", lambda: {}, lambda: ml.run_ml_pull_scheduler(0)),
    ]


@pytest.mark.parametrize("claimed", [True, False])
@pytest.mark.parametrize("index", range(5))
def test_scheduler_runs_its_job_only_when_it_wins_the_claim(monkeypatch, index, claimed):
    import utils.scheduler_gate as gate

    name, module, job_attr, job_result, loop = _schedulers()[index]
    claims, runs = [], []

    def fake_claim(job_name, gap):
        claims.append((job_name, gap))
        return claimed

    def job():
        runs.append(1)
        return job_result()

    def fake_sleep(seconds):
        if seconds:
            raise _Stop

    monkeypatch.setattr(gate, "claim_run", fake_claim)
    monkeypatch.setattr(module, job_attr, job)
    monkeypatch.setattr(time, "sleep", fake_sleep)
    import controllers.risk_breakdown_controller as rb
    monkeypatch.setattr(rb, "refresh_risk_breakdowns", lambda: {"rows": [], "not_available": {}})
    monkeypatch.setenv("RISK_BREAKDOWN_WRITES", "1")
    with pytest.raises(_Stop):
        loop()
    # D96: after a pull it runs, the ML pull loop also claims the risk breakdown (its own job, own claim).
    follow_up = ["risk-breakdown"] if name == "ml-pull" and claimed else []
    assert [c[0] for c in claims] == [name] + follow_up
    assert claims[0][1] > 0
    assert runs == ([1] if claimed else [])


def test_alert_claim_gap_is_just_under_the_interval():
    import controllers.alert_controller as alerts
    assert 0 < alerts.EVAL_SECONDS - 30 < alerts.EVAL_SECONDS


# ── G-22: sentiment_history TTL ───────────────────────────────────────────────

def test_sentiment_history_ttl_matches_in_both_places():
    from db import indexes
    from sentiment_engine.utils import config
    from sentiment_engine.storage import mongo_handler

    assert indexes.SENTIMENT_HISTORY_TTL_SECONDS == config.SENTIMENT_HISTORY_TTL_SECONDS
    assert config.SENTIMENT_HISTORY_TTL_SECONDS > 90 * 24 * 3600   # longer than the API's longest window
    backend_specs = indexes.INDEXES["sentiment_history"]
    engine_specs = [([(k, int(d)) for k, d in keys], opts) for keys, opts in mongo_handler.HISTORY_INDEXES]
    assert [([(k, int(d)) for k, d in keys], opts) for keys, opts in backend_specs] == engine_specs


def test_history_ts_parses_the_iso_timestamp():
    from sentiment_engine.storage.mongo_handler import history_ts
    assert history_ts("2026-11-16T10:00:00.123456+00:00") == datetime(2026, 11, 16, 10, 0, 0, 123456, tzinfo=timezone.utc)
    assert history_ts("2026-11-16T10:00:00Z").tzinfo is not None
    assert history_ts("2026-11-16T10:00:00").tzinfo is not None
    assert history_ts("garbage").tzinfo is not None


def test_save_sentiment_writes_ts_to_history(monkeypatch):
    from sentiment_engine.storage import mongo_handler

    class Coll:
        def __init__(self):
            self.inserts = []

        def update_one(self, *a, **k):
            pass

        def insert_one(self, doc):
            self.inserts.append(doc)

    db = {"sentiment": Coll(), "sentiment_history": Coll()}
    monkeypatch.setattr(mongo_handler, "_get_db", lambda: db)
    ok = mongo_handler.save_sentiment({
        "asset_id": "btc", "sentiment_score": 0.2, "confidence": 0.7,
        "last_updated": "2026-11-16T10:00:00+00:00",
    })
    assert ok
    (row,) = db["sentiment_history"].inserts
    assert row["timestamp"] == "2026-11-16T10:00:00+00:00"
    assert row["ts"] == datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)


# ── G-18: one database variable ───────────────────────────────────────────────

def test_sentiment_engine_uses_the_backend_database_variable():
    from sentiment_engine.utils.config import resolve_db_name
    assert resolve_db_name({"MONGO_DB_NAME": "aaip_db", "MONGO_DB": "altinvest"}) == "aaip_db"
    assert resolve_db_name({"MONGO_DB": "legacy"}) == "legacy"
    assert resolve_db_name({}) == "aaip_db"


def test_compose_no_longer_sets_a_second_database():
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    with open(os.path.join(root, "docker-compose.yml"), encoding="utf-8") as f:
        lines = [ln.split("#", 1)[0] for ln in f]
    assert not any(ln.strip().startswith("MONGO_DB:") for ln in lines)


# ── Migration script ──────────────────────────────────────────────────────────

class FakeColl:
    def __init__(self, docs=()):
        self.docs = {d["_id"]: dict(d) for d in docs}

    def find(self, query=None, projection=None):
        query = query or {}
        out = []
        for d in self.docs.values():
            if "_id" in query and d["_id"] not in query["_id"]["$in"]:
                continue
            if "ts" in query and ("ts" in d) == (query["ts"]["$exists"] is False):
                continue
            if "asset_id" in query and d.get("asset_id") != query["asset_id"]:
                continue
            out.append(dict(d))
        return out

    def find_one(self, query, projection=None):
        rows = self.find(query)
        return rows[0] if rows else None

    def insert_many(self, docs, ordered=True):
        for d in docs:
            self.docs[d["_id"]] = dict(d)

    def replace_one(self, query, doc, upsert=False):
        current = self.find_one(query)
        _id = current["_id"] if current else f"new-{len(self.docs)}"
        self.docs[_id] = {**doc, "_id": _id}

    def bulk_write(self, ops, ordered=True):
        for op in ops:
            self.docs[op._filter["_id"]].update(op._doc["$set"])


def test_migration_copies_missing_rows_and_keeps_newer_target_rows():
    from db import migrate_sentiment_db as m

    src = {"sentiment": FakeColl([
        {"_id": 1, "asset_id": "btc", "updated_at": "2026-11-10T00:00:00+00:00"},
        {"_id": 2, "asset_id": "eth", "updated_at": "2026-11-10T00:00:00+00:00"},
    ])}
    dst = {"sentiment": FakeColl([{"_id": 9, "asset_id": "btc", "updated_at": "2026-11-16T00:00:00+00:00"}])}
    src_ns, dst_ns = SimpleNamespace(**src), SimpleNamespace(**dst)
    assert m.copy_latest(src_ns, dst_ns, dry_run=False) == 1   # eth only; btc in the target is newer
    assert dst["sentiment"].find_one({"asset_id": "btc"})["updated_at"].startswith("2026-11-16")
    assert dst["sentiment"].find_one({"asset_id": "eth"})

    h_src = FakeColl([{"_id": "a"}, {"_id": "b"}])
    h_dst = FakeColl([{"_id": "a"}])
    assert m.copy_by_id(h_src, h_dst, dry_run=True) == 1
    assert set(h_dst.docs) == {"a"}
    assert m.copy_by_id(h_src, h_dst, dry_run=False) == 1
    assert set(h_dst.docs) == {"a", "b"}
    assert m.copy_by_id(h_src, h_dst, dry_run=False) == 0   # re-runnable


def test_migration_backfills_ts():
    from db import migrate_sentiment_db as m

    coll = FakeColl([
        {"_id": 1, "timestamp": "2026-11-16T10:00:00+00:00"},
        {"_id": 2, "timestamp": "2026-11-15T10:00:00+00:00", "ts": datetime(2026, 11, 15, 10, tzinfo=timezone.utc)},
    ])
    assert m.backfill_ts(coll, dry_run=False) == 1
    assert coll.docs[1]["ts"] == datetime(2026, 11, 16, 10, tzinfo=timezone.utc)
    assert m.backfill_ts(coll, dry_run=False) == 0


def test_migration_refuses_a_remote_database(monkeypatch):
    from db import migrate_sentiment_db as m
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://u:p@cluster0.example.net/")
    with pytest.raises(SystemExit) as exc:
        m.main([])
    assert "cluster0.example.net" in str(exc.value) and "u:p" not in str(exc.value)
