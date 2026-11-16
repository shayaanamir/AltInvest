"""NFT aggregator: relevance filter, story weighting, market blend, fallback, trend. Scorers are faked."""
from datetime import datetime, timedelta, timezone

import pytest

from nft_sentiment import config as cfg
from nft_sentiment.aggregator import (
    ScoringUnavailable,
    compute_confidence,
    is_placeholder,
    run_collection_pipeline,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def _art(title, score, story=None, relevant=True, age=1.0, trust=1.0, source="CoinDesk"):
    return {"title": title, "summary": "", "age_hours": age, "trust_weight": trust, "source": source,
            "_score": score, "_story": story, "_relevant": relevant}


def llm(articles_in):
    """A fake LLM scorer: reads the verdict planted in each article."""
    def scorer(slug, name, articles):
        done = []
        for i, a in enumerate(articles):
            done.append({**a, "nlp_score": a["_score"], "relevant": a["_relevant"],
                         "llm_label": "positive" if a["_score"] > 0 else "negative" if a["_score"] < 0 else "neutral",
                         "llm_reason": "because", "story_id": i if a["_story"] is None else a["_story"]})
        return done, []
    return scorer


def run(articles, **kw):
    kw.setdefault("scorer", llm(articles))
    kw.setdefault("fallback", lambda arts: pytest.fail("fallback should not run"))
    return run_collection_pipeline("azuki", "Azuki", articles, now=NOW, **kw)


def test_no_articles_is_a_placeholder():
    out = run([])
    assert out["confidence"] == 0.0 and out["data_quality"]["reason"] == "no_articles" and is_placeholder(out)
    assert out["validated"] is False


def test_irrelevant_articles_are_dropped():
    out = run([_art("Azuki deal", 0.6), _art("Azuki price page", -0.9, relevant=False)])
    assert out["article_count"] == 1 and out["data_quality"]["irrelevant_dropped"] == 1
    assert out["sentiment_score"] == pytest.approx(0.6)
    assert not is_placeholder(out)


def test_only_irrelevant_articles_is_a_placeholder():
    out = run([_art("Azuki price page", 0.6, relevant=False)])
    assert is_placeholder(out) and out["data_quality"]["irrelevant_dropped"] == 1


def test_a_reworded_story_counts_once():
    arts = [_art("Azuki sold at a loss", -0.6), _art("Loss sale of Azuki", -0.6, story=0),
            _art("Azuki holder sells cheap", -0.6, story=0), _art("Azuki new anime deal", 0.6)]
    out = run(arts)
    assert out["sentiment_score"] == pytest.approx(0.0)      # one negative story vs one positive story
    assert out["article_count"] == 4 and out["story_count"] == 2
    assert out["confidence"] == compute_confidence(2)
    assert out["sentiment_distribution"] == {"positive": 1, "negative": 1, "neutral": 0}
    heads = out["top_headlines"]
    assert len(heads) == 2 and sorted(h["copies"] for h in heads) == [1, 3]
    assert sum(h["contribution"] for h in heads) == pytest.approx(0.0, abs=1e-3)


def test_recency_and_trust_weight_articles():
    fresh = _art("Azuki fresh good news", 0.6, age=0)
    old = _art("Azuki old bad news", -0.6, age=cfg.NFT_RECENCY_HALF_LIFE_HOURS)    # half weight
    out = run([fresh, old])
    assert out["sentiment_score"] == pytest.approx((0.6 * 1 - 0.6 * 0.5) / 1.5, abs=1e-3)


def test_market_signal_is_blended():
    market = {"score": 1.0, "is_fallback": False, "price_change_24h": 5.0, "price_change_7d": 10.0,
              "activity_ratio": 1.2, "as_of": "2026-11-15"}
    out = run([_art("Azuki neutral update", 0.0)], market_signal=market)
    expected_01 = cfg.NFT_NEWS_WEIGHT * 0.5 + cfg.NFT_MARKET_SIGNAL_WEIGHT * 1.0
    assert out["sentiment_score"] == pytest.approx(expected_01 * 2 - 1, abs=1e-4)
    assert out["source_breakdown"] == {"news_nlp": 0.5, "market_signals": 1.0}
    assert out["market_signals"]["price_change_7d"] == 10.0
    assert out["data_quality"]["market_fallback"] is False


def test_fallback_market_signal_is_left_out_and_flagged():
    out = run([_art("Azuki good news", 0.6)], market_signal={"score": 0.5, "is_fallback": True})
    assert out["sentiment_score"] == pytest.approx(0.6)
    assert out["source_breakdown"]["market_signals"] is None and out["data_quality"]["market_fallback"] is True


def test_unscored_articles_go_to_the_fallback_scorer():
    arts = [_art("Azuki a", 0.6), _art("Azuki b", 0.0)]

    def half(slug, name, articles):
        done, _ = llm(articles)(slug, name, articles[:1])
        return done, articles[1:]

    out = run(arts, scorer=half, fallback=lambda xs: [{**x, "nlp_score": -0.4, "relevant": None} for x in xs])
    assert out["article_count"] == 2 and out["story_count"] == 2
    assert out["data_quality"]["llm_scored"] == 1 and out["data_quality"]["fallback_scored"] == 1
    assert out["data_quality"]["llm_unavailable"] is True and "partly VADER + FinBERT" in out["source"]


def test_no_scorer_at_all_raises():
    with pytest.raises(ScoringUnavailable):
        run([_art("Azuki a", 0.6)], scorer=lambda s, n, a: ([], list(a)), fallback=lambda xs: [])


def test_fallback_crash_with_nothing_scored_raises():
    def boom(xs):
        raise RuntimeError("torch missing")
    with pytest.raises(ScoringUnavailable):
        run([_art("Azuki a", 0.6)], scorer=lambda s, n, a: ([], list(a)), fallback=boom)


def test_article_cap_keeps_the_newest(monkeypatch):
    monkeypatch.setattr(cfg, "NFT_MAX_ARTICLES_SCORED", 2)
    seen = []

    def scorer(slug, name, articles):
        seen.extend(a["title"] for a in articles)
        return llm(articles)(slug, name, articles)

    run([_art("Azuki old", 0.1, age=50), _art("Azuki new", 0.1, age=1), _art("Azuki mid", 0.1, age=10)], scorer=scorer)
    assert seen == ["Azuki new", "Azuki mid"]


def test_trend_compares_with_the_reading_a_day_ago():
    history = [{"timestamp": (NOW - timedelta(hours=24)).isoformat(), "sentiment_score": 0.0, "confidence": 0.5}]
    assert run([_art("Azuki great news", 0.9)], history=history)["trend"] == "improving"
    assert run([_art("Azuki great news", 0.9)], history=[])["trend"] == "unknown"


def test_confidence_curve():
    assert compute_confidence(0) == 0.0
    assert compute_confidence(1) < 0.4 < compute_confidence(3) < 0.7 < compute_confidence(5)
    assert compute_confidence(cfg.NFT_CONFIDENCE_FULL_ARTICLES) == 1.0
    assert compute_confidence(100) == 1.0
