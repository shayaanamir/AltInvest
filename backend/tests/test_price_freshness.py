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
