"""PUT /profile/onboarding (audit G-06): the answers are stored, copied to the profile, and used to
start a watchlist; skipping changes nothing else; a second call is a no-op. The database is faked."""
import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.dependencies import get_current_user_id
from routes import profile as profile_routes

UID = ObjectId()
ANSWERS = {"markets": ["crypto", "nfts"], "risk": 55, "goals": ["trading", "longterm"],
           "assets": ["btc", "ETH", "NOPE", "eth"], "layout": "analyst"}


class Fake:
    """In-memory stand-ins for the db.queries functions profile.py imports."""
    def __init__(self):
        self.user = {"_id": UID, "email": "a@x.com", "name": "A", "risk_profile": "balanced",
                     "investment_goal": None, "layout_preference": "ai-first",
                     "onboarding": {"completed": False, "completed_at": None, "skipped": False, "answers": {}}}
        self.settings, self.watchlists = [], []
        self.fail_settings = self.fail_watchlist = False

    def get_user_by_id(self, uid):
        return self.user

    def set_onboarding_if_open(self, uid, onboarding, extra=None):
        if (self.user.get("onboarding") or {}).get("completed"):
            return False
        self.user["onboarding"] = onboarding
        self.user.update(extra or {})
        return True

    def update_user_settings(self, uid, section, payload):
        if self.fail_settings:
            raise RuntimeError("boom")
        self.settings.append((section, payload))

    def get_assets_by_id(self, ids):
        return {i.upper(): {} for i in ids if i.upper() in {"BTC", "ETH"}}

    def watchlist_name_taken(self, uid, name, except_id=None):
        return any(n.lower() == name.lower() for n, _ in self.watchlists)

    def create_watchlist(self, uid, name, items=None):
        if self.fail_watchlist:
            raise RuntimeError("boom")
        self.watchlists.append((name, items))
        return "wl1"


@pytest.fixture
def env(monkeypatch):
    fake = Fake()
    for name in ("get_user_by_id", "set_onboarding_if_open", "update_user_settings", "get_assets_by_id",
                 "watchlist_name_taken", "create_watchlist"):
        monkeypatch.setattr(profile_routes, name, getattr(fake, name))
    monkeypatch.setattr(profile_routes, "get_activity_counts",
                        lambda uid: {"holdings_count": 0, "watchlists_count": len(fake.watchlists), "alerts_count": 0,
                                       "active_alerts_count": 0})
    app = FastAPI()
    app.include_router(profile_routes.router)
    app.dependency_overrides[get_current_user_id] = lambda: UID
    return TestClient(app), fake


def _put(client, **body):
    return client.put("/profile/onboarding", json=body)


def test_finishing_stores_the_answers_and_fills_the_profile(env):
    client, fake = env
    r = _put(client, skipped=False, answers=ANSWERS)
    assert r.status_code == 200
    ob = fake.user["onboarding"]
    assert ob["completed"] is True and ob["skipped"] is False and ob["completed_at"] is not None
    assert ob["answers"] == {"markets": ["crypto", "nfts"], "risk": 55, "goals": ["trading", "longterm"],
                             "assets": ["BTC", "ETH", "NOPE"], "layout": "analyst"}   # upper-cased, de-duplicated
    assert fake.user["risk_profile"] == "balanced"
    assert fake.user["investment_goal"] == "trading"          # the first goal picked
    assert fake.user["layout_preference"] == "analyst"
    assert fake.settings == [("preferences", {"default_dashboard_layout": "analyst"})]
    body = r.json()
    assert body["markets_followed"] == ["crypto", "nfts"] and body["risk_profile"] == "balanced"


@pytest.mark.parametrize("score,expected", [(0, "conservative"), (25, "conservative"), (26, "balanced"),
                                            (65, "balanced"), (66, "aggressive"), (100, "aggressive")])
def test_risk_buckets_match_the_slider(env, score, expected):
    client, fake = env
    _put(client, answers={"risk": score})
    assert fake.user["risk_profile"] == expected


def test_a_starter_watchlist_is_built_from_the_known_coins_only(env):
    client, fake = env
    _put(client, answers=ANSWERS)
    assert fake.watchlists == [("My Watchlist", [("crypto", "BTC"), ("crypto", "ETH")])]   # NOPE dropped


def test_no_known_coins_means_no_watchlist(env):
    client, fake = env
    _put(client, answers={"assets": ["NOPE"]})
    assert fake.watchlists == []


def test_an_existing_my_watchlist_is_left_alone(env):
    client, fake = env
    fake.watchlists.append(("my watchlist", []))
    _put(client, answers=ANSWERS)
    assert len(fake.watchlists) == 1


def test_unanswered_steps_leave_those_profile_fields_alone(env):
    client, fake = env
    _put(client, answers={"markets": ["crypto"]})
    assert fake.user["risk_profile"] == "balanced" and fake.user["investment_goal"] is None
    assert fake.user["layout_preference"] == "ai-first" and fake.settings == []


def test_skip_records_the_skip_and_changes_nothing_else(env):
    client, fake = env
    r = _put(client, skipped=True, answers=ANSWERS)        # answers sent with a skip are ignored
    assert r.status_code == 200
    assert fake.user["onboarding"] == {"completed": False, "completed_at": None, "skipped": True, "answers": {}}
    assert fake.user["risk_profile"] == "balanced" and fake.user["layout_preference"] == "ai-first"
    assert fake.watchlists == [] and fake.settings == []


def test_a_second_call_after_finishing_changes_nothing(env):
    client, fake = env
    _put(client, answers=ANSWERS)
    snapshot = (dict(fake.user["onboarding"]), list(fake.watchlists), list(fake.settings))
    r = _put(client, answers={"markets": ["commodities"], "risk": 99, "assets": ["ETH"], "layout": "minimal"})
    assert r.status_code == 200
    assert (fake.user["onboarding"], fake.watchlists, fake.settings) == snapshot
    assert fake.user["risk_profile"] == "balanced"


def test_skipping_after_finishing_does_not_undo_it(env):
    client, fake = env
    _put(client, answers=ANSWERS)
    _put(client, skipped=True)
    assert fake.user["onboarding"]["completed"] is True


def test_finishing_after_a_skip_still_works(env):
    client, fake = env
    _put(client, skipped=True)
    _put(client, answers=ANSWERS)
    assert fake.user["onboarding"]["completed"] is True and len(fake.watchlists) == 1


@pytest.mark.parametrize("answers", [
    {"markets": ["stocks"]}, {"goals": ["getrich"]}, {"layout": "wild"}, {"assets": ["BT C"]},
    {"assets": ["X" * 16]}, {"risk": 101}, {"risk": -1}, {"unknown": 1},
])
def test_bad_answers_are_rejected(env, answers):
    client, fake = env
    assert _put(client, answers=answers).status_code == 422
    assert fake.user["onboarding"]["completed"] is False


def test_unknown_top_level_fields_are_rejected(env):
    client, _ = env
    assert _put(client, answers={}, completed=True).status_code == 422


def test_a_failing_follow_up_does_not_undo_the_saved_answers(env):
    client, fake = env
    fake.fail_settings = fake.fail_watchlist = True
    r = _put(client, answers=ANSWERS)
    assert r.status_code == 200
    assert fake.user["onboarding"]["completed"] is True and fake.user["layout_preference"] == "analyst"


def test_unknown_user_is_404(env):
    client, fake = env
    fake.user = None
    assert _put(client, answers={}).status_code == 404


def test_needs_a_signed_in_user():
    app = FastAPI()
    app.include_router(profile_routes.router)
    assert TestClient(app).put("/profile/onboarding", json={"answers": {}}).status_code in (401, 403)


# ── the real conditional update (needs a throwaway MongoDB: MONGO_TEST_URI) ──

@pytest.mark.skipif(not __import__("os").getenv("MONGO_TEST_URI"), reason="set MONGO_TEST_URI to run")
def test_live_only_the_first_completion_wins(monkeypatch):
    import os, uuid
    from concurrent.futures import ThreadPoolExecutor
    from pymongo import MongoClient
    import db.queries as queries

    client = MongoClient(os.environ["MONGO_TEST_URI"], serverSelectionTimeoutMS=3000)
    db = client[f"altinvest_test_{uuid.uuid4().hex[:10]}"]
    monkeypatch.setattr(queries, "get_db", lambda: db)
    try:
        legacy = db.users.insert_one({"email": "legacy@x.com"}).inserted_id       # no onboarding field at all
        fresh = db.users.insert_one({"email": "f@x.com", "onboarding": {"completed": False}}).inserted_id
        with ThreadPoolExecutor(8) as pool:
            wins = list(pool.map(lambda i: queries.set_onboarding_if_open(
                fresh, {"completed": True, "answers": {"n": i}}, {"risk_profile": "balanced"}), range(8)))
        assert wins.count(True) == 1
        assert db.users.find_one({"_id": fresh})["onboarding"]["completed"] is True
        assert queries.set_onboarding_if_open(legacy, {"completed": True, "answers": {}}) is True
        assert queries.set_onboarding_if_open(legacy, {"completed": False, "skipped": True}) is False
    finally:
        client.drop_database(db.name)
        client.close()
