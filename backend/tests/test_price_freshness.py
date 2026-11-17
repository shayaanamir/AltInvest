"""Audit N-05: every crypto price the API returns carries price_as_of (the price's own time) and price_delayed
(True when it is more than 15 minutes old)."""
from datetime import datetime, timedelta, timezone

import pytest

import controllers.market_controller as mc
from models.schemas import AssetHeader, DiscoverItem
from utils.price_freshness import PRICE_DELAYED_AFTER, price_freshness

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("age, delayed", [(timedelta(minutes=2), False), (PRICE_DELAYED_AFTER, False),
                                          (PRICE_DELAYED_AFTER + timedelta(seconds=1), True), (timedelta(days=2), True)])
def test_delayed_only_past_the_threshold(age, delayed):
    out = price_freshness({"price": 100.0, "timestamp": NOW - age}, NOW)
    assert out["price_delayed"] is delayed
    assert out["price_as_of"] == (NOW - age).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_naive_mongo_time_is_utc_and_fetched_at_is_the_fallback():
    naive = (NOW - timedelta(minutes=30)).replace(tzinfo=None)
    assert price_freshness({"price": 1.0, "fetched_at": naive}, NOW) == {
        "price_as_of": "2026-11-17T09:30:00Z", "price_delayed": True}


@pytest.mark.parametrize("row", [None, {}, {"price": None, "timestamp": NOW}, {"price": 5.0}])
def test_no_price_or_no_time_gives_nothing(row):
    assert price_freshness(row, NOW) == {"price_as_of": None, "price_delayed": None}


def test_list_items_carry_the_fields_through_the_response_model(monkeypatch):
    fresh = datetime.now(timezone.utc) - timedelta(minutes=1)
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    monkeypatch.setattr(mc, "get_supported_assets", lambda: [{"asset_id": "BTC"}, {"asset_id": "ETH"}])
    monkeypatch.setattr(mc, "get_asset_market_data_all_latest", lambda: [
        {"asset_id": "BTC", "price": 90000.0, "timestamp": fresh},
        {"asset_id": "ETH", "price": 3000.0, "timestamp": old}])
    for name in ("get_all_latest_aai_scores", "get_all_latest_predictions", "get_all_latest_risk_scores",
                 "get_all_latest_risk_breakdowns"):
        monkeypatch.setattr(mc, name, lambda *a: {})
    monkeypatch.setattr(mc, "get_user_flags", lambda u: {"held": set(), "watching": set()})
    monkeypatch.setattr(mc, "live_sentiment_by_symbol", lambda: {})
    items = {i["id"]: DiscoverItem(**i) for i in mc.build_crypto_items()}
    assert items["BTC"].price_delayed is False and items["BTC"].price_as_of
    assert items["ETH"].price_delayed is True


def test_header_model_accepts_the_fields():
    h = AssetHeader(asset_id="BTC", symbol="BTC", name="Bitcoin", category="crypto", price=1.0,
                    **price_freshness({"price": 1.0, "timestamp": NOW}, NOW))
    assert h.price_as_of == "2026-11-17T10:00:00Z" and h.price_delayed is False


# ── N-05, the rest: NFT floors, search, trending, watchlists ──────────────────

from utils.price_freshness import FLOOR_DELAYED_AFTER, floor_freshness  # noqa: E402


@pytest.mark.parametrize("age, delayed", [(timedelta(hours=10), False), (FLOOR_DELAYED_AFTER, False),
                                          (FLOOR_DELAYED_AFTER + timedelta(seconds=1), True)])
def test_floor_uses_the_48h_limit_and_floor_usd(age, delayed):
    out = floor_freshness({"floor_usd": 900.0, "timestamp": NOW - age}, NOW)
    assert out["price_delayed"] is delayed
    assert floor_freshness({"price": 1.0, "timestamp": NOW}, NOW)["price_delayed"] is None   # no floor_usd


def _fresh_and_old():
    now = datetime.now(timezone.utc)
    return now - timedelta(minutes=1), now - timedelta(hours=1), now - timedelta(days=3)


def test_nft_items_carry_the_floor_freshness(monkeypatch):
    _, _, old_floor = _fresh_and_old()
    monkeypatch.setattr(mc, "get_nft_collections", lambda: [{"slug": "azuki", "name": "Azuki", "supply": 10}])
    monkeypatch.setattr(mc, "get_nft_market_data_all_latest", lambda: [
        {"slug": "azuki", "floor_usd": 900.0, "timestamp": old_floor}])
    for name in ("get_all_latest_aai_scores", "get_all_latest_nft_liquidity"):
        monkeypatch.setattr(mc, name, lambda *a: {})
    monkeypatch.setattr(mc, "get_user_flags", lambda u: {"held": set(), "watching": set()})
    monkeypatch.setattr(mc, "live_nft_sentiment", lambda: {})
    item = DiscoverItem(**mc.build_nft_items()[0])
    assert item.price_delayed is True and item.price_as_of


def test_trending_and_trending_collections(monkeypatch):
    import controllers.trending_controller as tc
    import routes.dashboard as d
    fresh, old, old_floor = _fresh_and_old()
    monkeypatch.setattr(d, "get_asset_market_data_all_latest", lambda: [{"asset_id": "BTC", "price": 1.0, "timestamp": old}])
    monkeypatch.setattr(tc, "score_assets", lambda rows: rows)
    monkeypatch.setattr(d, "get_supported_assets", lambda: [])
    monkeypatch.setattr(d, "get_all_latest_aai_scores", lambda t: {})
    monkeypatch.setattr(d, "get_price_sparklines", lambda ids: {})
    monkeypatch.setattr(d, "get_user_flags", lambda u: {"held": set(), "watching": set()})
    row = d.get_dashboard_trending(limit=6, user_id=None)[0]
    assert row["price_delayed"] is True and row["price_as_of"]
    monkeypatch.setattr(d, "get_nft_market_data_all_latest", lambda: [{"slug": "azuki", "floor_usd": 9.0, "timestamp": fresh}])
    monkeypatch.setattr(d, "get_nft_collections", lambda: [])
    row = d.get_dashboard_trending_collections(limit=4)[0]
    assert row["price_delayed"] is False and row["price_as_of"]


def test_search_rows_carry_price_floor_and_freshness(monkeypatch):
    import routes.search as s
    from models.schemas import SearchResults
    fresh, old, old_floor = _fresh_and_old()
    monkeypatch.setattr(s, "search_all", lambda q, limit: {
        "assets": [{"asset_id": "BTC", "symbol": "BTC", "name": "Bitcoin"}],
        "nft_collections": [{"slug": "azuki", "name": "Azuki"}], "insights": []})
    monkeypatch.setattr(s, "get_asset_market_data_all_latest", lambda: [{"asset_id": "BTC", "price": 9.0, "change_24h": 1.0, "timestamp": fresh}])
    monkeypatch.setattr(s, "get_nft_market_data_all_latest", lambda: [{"slug": "azuki", "floor_usd": 900.0, "timestamp": old_floor}])
    out = SearchResults(**s.search(q="a", limit=10))
    assert out.assets[0]["price"] == 9.0 and out.assets[0]["price_delayed"] is False
    assert out.nft_collections[0]["floor_usd"] == 900.0 and out.nft_collections[0]["price_delayed"] is True


def test_watchlist_items_carry_freshness(monkeypatch):
    import routes.watchlists as w
    from models.schemas import WatchlistOut
    fresh, old, old_floor = _fresh_and_old()
    monkeypatch.setattr(w, "get_assets_by_id", lambda ids: {"BTC": {"name": "Bitcoin"}})
    monkeypatch.setattr(w, "get_asset_market_data_latest_by_id", lambda ids: {"BTC": {"price": 9.0, "timestamp": old}})
    monkeypatch.setattr(w, "get_nft_collections_by_slug", lambda slugs: {"azuki": {"name": "Azuki"}})
    monkeypatch.setattr(w, "get_nft_market_data_latest_by_slug", lambda slugs: {"azuki": {"floor_usd": 900.0, "timestamp": fresh}})
    monkeypatch.setattr(w, "get_latest_aai_scores_for", lambda t, ids: {})
    lists = w._enrich_watchlists([{"id": "1", "user_id": "u", "name": "L", "items": [
        {"type": "crypto", "symbol_or_slug": "BTC"}, {"type": "nft", "symbol_or_slug": "azuki"}]}])
    items = WatchlistOut(**lists[0]).items
    assert items[0].price_delayed is True and items[1].price_delayed is False and items[1].price_as_of
