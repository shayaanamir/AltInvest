"""NFT market signal: floor change and sales momentum mapped to 0..1."""
import pytest

from nft_sentiment.market_signals import activity_ratio, build_market_signal


def test_no_data_is_a_flagged_neutral_fallback():
    s = build_market_signal(None, None)
    assert s["score"] == 0.5 and s["is_fallback"] is True


def test_flat_market_is_neutral():
    s = build_market_signal({"change_24h": 0.0, "change_7d": 0.0}, {"sales_7d": 7, "sales_30d": 30})
    assert s["score"] == pytest.approx(0.5) and s["is_fallback"] is False
    assert s["activity_ratio"] == pytest.approx(1.0)


def test_extreme_moves_are_clipped():
    up = build_market_signal({"change_24h": 500.0, "change_7d": 900.0}, {"sales_7d": 100, "sales_30d": 10})
    down = build_market_signal({"change_24h": -99.0, "change_7d": -99.0}, {"sales_7d": 0, "sales_30d": 100})
    assert up["score"] == pytest.approx(1.0)
    assert down["score"] == pytest.approx(0.0)


def test_partial_inputs_reweight_what_is_there():
    s = build_market_signal({"change_7d": 15.0, "date": "2026-11-15"}, None)
    assert s["score"] == pytest.approx(0.75)     # +15% of a +-30% range, the only component
    assert s["price_change_24h"] is None and s["as_of"] == "2026-11-15"


def test_activity_ratio_ignores_unusable_values():
    assert activity_ratio({"sales_7d": 5, "sales_30d": 0}) is None
    assert activity_ratio({"sales_7d": None, "sales_30d": 30}) is None
    assert activity_ratio({"sales_7d": True, "sales_30d": 30}) is None
    assert activity_ratio({"sales_7d": 14, "sales_30d": 30}) == pytest.approx(2.0)


def test_nan_is_ignored():
    s = build_market_signal({"change_24h": float("nan"), "change_7d": 0.0}, None)
    assert s["price_change_24h"] is None and s["score"] == pytest.approx(0.5)
