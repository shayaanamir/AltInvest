"""Crypto sentiment aggregator: the news + market blend, and what happens with no market data."""
import pytest

from aggregator import sentiment_aggregator as agg

ARTICLE = {"title": "Bitcoin rallies", "summary": "s", "source": "CoinDesk", "trust_weight": 1.0,
           "age_hours": 0.0, "link": "https://x", "published": "2026-11-16T05:00:00+00:00", "asset_id": "btc"}


def market(score, **overrides):
    base = {
        "source": "coingecko+binance",
        "quote": {"price_change_24h": 2.0, "price_change_7d": -3.0, "volume_change_24h": 20.0,
                  "is_fallback": score is None},
        "global": {"btc_dominance": 56.1, "is_fallback": False},
        "is_trending": False, "market_score": score,
        "quote_fallback": score is None, "global_fallback": False, "volume_fallback": False,
        "trending_fallback": False, "degraded": score is None,
    }
    base.update(overrides)
    return base


@pytest.fixture
def run(monkeypatch):
    def scored(articles):
        return [{**a, "nlp_score": 0.4, "vader_score": 0.3, "finbert_score": 0.45, "trust_weighted_score": 0.4,
                 "nlp_models": "vader+finbert"} for a in articles]
    monkeypatch.setattr(agg, "ensemble_score", scored)

    def go(market_data, articles=(ARTICLE,)):
        monkeypatch.setattr(agg, "fetch_articles_for_asset", lambda asset_id: list(articles))
        monkeypatch.setattr(agg, "fetch_market_signals", lambda asset_id: market_data)
        return agg.run_pipeline("btc", history=[])
    return go


def test_with_market_data_the_score_is_70_percent_news_30_percent_market(run):
    out = run(market(0.9))
    news_01 = (0.4 + 1) / 2                                 # 0.7
    assert out["sentiment_score"] == pytest.approx((0.7 * news_01 + 0.3 * 0.9) * 2 - 1, abs=1e-3)   # 0.52
    assert out["source_breakdown"] == {"news_nlp": 0.7, "market_signals": 0.9}
    assert out["data_quality"]["market_unavailable"] is False
    assert out["data_quality"]["market_source"] == "coingecko+binance"


def test_with_no_market_data_the_score_is_the_news_alone_not_pulled_toward_neutral(run):
    out = run(market(None))
    assert out["sentiment_score"] == pytest.approx(0.4, abs=1e-3)      # the news score, unshrunk
    assert out["source_breakdown"]["market_signals"] is None
    assert out["data_quality"]["market_unavailable"] is True and out["data_quality"]["degraded"] is True


def test_the_old_neutral_placeholder_would_have_changed_the_answer(run):
    # news 0.4 blended with a placeholder 0.5 gives 0.7*0.7 + 0.3*0.5 = 0.64 -> 0.28 instead of 0.4
    assert run(market(None))["sentiment_score"] > run(market(0.5))["sentiment_score"]


def test_figures_that_could_not_be_fetched_are_none_not_zero(run):
    out = run(market(0.6, quote={"price_change_24h": None, "price_change_7d": None, "volume_change_24h": None},
                     is_trending=None, volume_fallback=True, trending_fallback=True,
                     **{"global": {"btc_dominance": None}}))
    assert out["market_signals"] == {"price_change_24h": None, "price_change_7d": None, "volume_change_24h": None,
                                     "is_trending": None, "btc_dominance": None}
    assert out["data_quality"]["volume_fallback"] is True and out["data_quality"]["trending_fallback"] is True


def test_real_market_figures_are_passed_through(run):
    out = run(market(0.6, is_trending=True))
    assert out["market_signals"] == {"price_change_24h": 2.0, "price_change_7d": -3.0, "volume_change_24h": 20.0,
                                     "is_trending": True, "btc_dominance": 56.1}


def test_no_articles_is_a_neutral_placeholder_with_no_fake_breakdown(run):
    out = run(market(0.9), articles=())
    assert out["confidence"] == 0.0 and out["data_quality"]["reason"] == "no_articles"
    assert out["source_breakdown"] == {"news_nlp": None, "market_signals": None}
    assert not any(k.startswith("cmc") for k in out["data_quality"])


def test_no_coinmarketcap_leftovers():
    import collectors
    import importlib.util
    assert importlib.util.find_spec("collectors.cmc_collector") is None
    from utils import config
    assert not hasattr(config, "CMC_API_KEY") and not hasattr(config, "CMC_BASE_URL")
    assert all("cmc_id" not in a and "cmc_symbol" not in a for a in config.ASSETS.values())
