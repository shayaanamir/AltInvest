"""NFT sentiment: storage rules, the refresh controller and the read-only routes.
The engine and the database are faked: no network, no Mongo, no Groq."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from controllers import nft_sentiment_controller as ctl
from routes import nft as nft_route

NOW = datetime.now(timezone.utc)


def _reading(slug="azuki", score=0.4, placeholder=False, when=NOW):
    return {
        "slug": slug, "name": slug.title(), "sentiment_score": 0.0 if placeholder else score,
        "source": None if placeholder else "LLM (gpt-oss-120b on Groq)", "confidence": 0.0 if placeholder else 0.6,
        "confidence_label": "low" if placeholder else "medium", "signal_strength": "moderate", "trend": "unknown",
        "last_updated": when.isoformat(), "article_count": 0 if placeholder else 3,
        "story_count": 0 if placeholder else 2, "source_count": 1,
        "source_breakdown": {"news_nlp": 0.7, "market_signals": None}, "sentiment_distribution": {},
        "top_headlines": [] if placeholder else [{"title": "Azuki deal", "score": 0.6, "contribution": 0.4,
                                                  "label": "positive", "reason": "r", "source": "CoinDesk",
                                                  "copies": 2, "age_hours": 3.0, "link": "https://x"}],
        "market_signals": {}, "articles_by_source": {"CoinDesk": 3},
        "data_quality": {"reason": "no_articles"} if placeholder else {"llm_unavailable": False},
        "validated": False, "validation_note": "not validated",
    }


# ── storage ──────────────────────────────────────────────────────────────────

class FakeCollection:
    def __init__(self):
        self.updates, self.inserts = [], []

    def update_one(self, flt, update, upsert=False):
        self.updates.append((flt, update, upsert))

    def insert_one(self, doc):
        self.inserts.append(doc)


@pytest.fixture
def fake_db(monkeypatch):
    db = SimpleNamespace(nft_sentiment=FakeCollection(), nft_sentiment_history=FakeCollection())
    monkeypatch.setattr(queries, "get_db", lambda: db)
    return db


def test_real_reading_replaces_latest_and_appends_slim_history(fake_db):
    assert queries.save_nft_sentiment(_reading()) == "saved"
    flt, update, upsert = fake_db.nft_sentiment.updates[0]
    assert flt == {"slug": "azuki"} and "$set" in update and upsert
    assert isinstance(update["$set"]["timestamp"], datetime)
    (hist,) = fake_db.nft_sentiment_history.inserts
    assert hist["sentiment_score"] == 0.4 and hist["story_count"] == 2
    assert "top_headlines" not in hist                       # history stays small


def test_placeholder_never_overwrites_and_never_enters_history(fake_db):
    assert queries.save_nft_sentiment(_reading(placeholder=True)) == "placeholder"
    (_, update, upsert), = fake_db.nft_sentiment.updates
    assert list(update) == ["$setOnInsert"] and upsert
    assert fake_db.nft_sentiment_history.inserts == []


# ── controller ───────────────────────────────────────────────────────────────

def test_only_recent_ml_rows_feed_the_market_signal():
    fresh = {"source": "ml-service", "timestamp": NOW - timedelta(hours=10)}
    assert ctl.usable_ml_row(fresh, NOW) is fresh
    assert ctl.usable_ml_row({**fresh, "source": None}, NOW) is None                      # old seeded numbers
    assert ctl.usable_ml_row({**fresh, "timestamp": NOW - timedelta(days=4)}, NOW) is None
    naive = {"source": "ml-service", "timestamp": (NOW - timedelta(hours=1)).replace(tzinfo=None)}
    assert ctl.usable_ml_row(naive, NOW) is naive                                         # Mongo returns naive UTC
    assert ctl.usable_ml_row(None, NOW) is None


class Unavailable(Exception):
    pass


@pytest.fixture
def fake_engine(monkeypatch):
    calls = {"signals": [], "pipeline": []}
    cfg = SimpleNamespace(
        NFT_COLLECTIONS={"azuki": {"name": "Azuki"}, "milady": {"name": "Milady Maker"}, "doodles-official": {"name": "Doodles"}},
        NFT_MARKET_ID="nft-market", NFT_MARKET={"name": "NFT market"})
    collector = SimpleNamespace(collect=lambda slugs, include_market: {
        "azuki": [{"title": "a"}], "milady": [{"title": "m"}], "doodles-official": [], "nft-market": [{"title": "n"}]})

    def build_market_signal(market, liquidity):
        calls["signals"].append((market, liquidity))
        return {"score": 0.5, "is_fallback": market is None}

    def run_collection_pipeline(slug, name, items, market_signal=None, history=None):
        calls["pipeline"].append((slug, name, market_signal, history))
        if slug == "milady":
            raise Unavailable("no scorer")
        if slug == "doodles-official":
            raise RuntimeError("boom")
        return _reading(slug)

    monkeypatch.setattr(ctl, "_engine", lambda: (cfg, collector, SimpleNamespace(build_market_signal=build_market_signal),
                                                 Unavailable, run_collection_pipeline))
    monkeypatch.setattr(queries, "get_nft_collections_by_slug", lambda slugs: {"azuki": {"name": "Azuki (DB)"}})
    monkeypatch.setattr(queries, "get_nft_market_data_latest_by_slug", lambda slugs: {
        "azuki": {"source": "ml-service", "timestamp": NOW, "change_7d": 3.0},
        "milady": {"source": None, "timestamp": NOW, "change_7d": 99.0}})
    monkeypatch.setattr(queries, "get_nft_liquidity", lambda slug: None)
    monkeypatch.setattr(queries, "get_nft_sentiment_baseline", lambda slug: [{"slug": slug}])
    saved = []
    monkeypatch.setattr(queries, "save_nft_sentiment", lambda r: saved.append(r) or "saved")
    calls["saved"] = saved
    return calls


def test_refresh_runs_every_target_and_isolates_failures(fake_engine):
    out = ctl.refresh_all()
    assert out == {"azuki": "saved", "milady": "scoring_unavailable",
                   "doodles-official": "failed: RuntimeError", "nft-market": "saved"}
    assert [r["slug"] for r in fake_engine["saved"]] == ["azuki", "nft-market"]


def test_refresh_passes_names_market_rows_and_history(fake_engine):
    ctl.refresh_all()
    by_slug = {slug: (name, signal, history) for slug, name, signal, history in fake_engine["pipeline"]}
    assert by_slug["azuki"][0] == "Azuki (DB)" and by_slug["milady"][0] == "Milady Maker"
    assert by_slug["nft-market"][1] is None                        # the market has no market signal
    assert by_slug["azuki"][2] == [{"slug": "azuki"}]
    markets = [m for m, _ in fake_engine["signals"]]
    assert markets[0]["change_7d"] == 3.0
    assert markets[1] is None                                      # milady's row is not from the ML pull


def test_refresh_is_skipped_while_one_is_running(fake_engine):
    ctl._run_lock.acquire()
    try:
        assert ctl.refresh_all() == {"skipped": "already running"}
    finally:
        ctl._run_lock.release()


# ── routes ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(nft_route.router)
    return TestClient(app)


def _stored(reading):
    return {**reading, "timestamp": datetime.fromisoformat(reading["last_updated"]).replace(tzinfo=None)}


def test_collection_sentiment_with_history(client, monkeypatch):
    monkeypatch.setattr(nft_route, "get_nft_sentiment", lambda slug: _stored(_reading(slug)))
    monkeypatch.setattr(nft_route, "get_nft_sentiment_history", lambda slug, days: [
        {"timestamp": NOW - timedelta(hours=1), "sentiment_score": 0.3, "confidence": 0.5, "story_count": 2},
        {"timestamp": NOW, "sentiment_score": None, "confidence": 0.0}])
    r = client.get("/nft/collections/azuki/sentiment?days=3")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["sentiment_score"] == 0.4 and body["stale"] is False
    assert body["top_headlines"][0]["copies"] == 2 and body["validated"] is False
    assert len(body["history"]) == 1 and body["history"][0]["timestamp"].endswith("Z")


def test_unknown_collection_is_404(client, monkeypatch):
    monkeypatch.setattr(nft_route, "get_nft_sentiment", lambda slug: None)
    monkeypatch.setattr(nft_route, "get_nft_sentiment_history", lambda slug, days: pytest.fail("not needed"))
    assert client.get("/nft/collections/nope/sentiment").status_code == 404


def test_placeholder_has_no_score_and_old_reading_is_stale(client, monkeypatch):
    old = _reading("milady", placeholder=True, when=NOW - timedelta(hours=5))
    monkeypatch.setattr(nft_route, "get_nft_sentiment", lambda slug: _stored(old))
    monkeypatch.setattr(nft_route, "get_nft_sentiment_history", lambda slug, days: [])
    body = client.get("/nft/collections/milady/sentiment").json()
    assert body["status"] == "no_articles" and body["sentiment_score"] is None and body["stale"] is True


def test_list_puts_the_market_last(client, monkeypatch):
    monkeypatch.setattr(nft_route, "get_all_nft_sentiment", lambda: [
        _stored(_reading("nft-market")), _stored(_reading("milady")), _stored(_reading("azuki"))])
    assert [d["slug"] for d in client.get("/nft/sentiment").json()] == ["azuki", "milady", "nft-market"]


def test_days_is_bounded(client, monkeypatch):
    monkeypatch.setattr(nft_route, "get_nft_sentiment", lambda slug: _stored(_reading()))
    monkeypatch.setattr(nft_route, "get_nft_sentiment_history", lambda slug, days: [])
    assert client.get("/nft/collections/azuki/sentiment?days=365").status_code == 422
