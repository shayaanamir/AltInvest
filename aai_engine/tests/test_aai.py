# aai_engine/tests/test_aai.py
from aai_engine.aai import normalise_sentiment, compute_aai


def test_normalise_sentiment_bounds():
    assert normalise_sentiment(-1.0) == 0.0
    assert normalise_sentiment(0.0) == 50.0
    assert normalise_sentiment(1.0) == 100.0


def test_compute_aai_not_bullish_biased():
    # A genuinely bearish sentiment input (-0.8 on the real [-1,1] scale)
    # must be able to pull AAI down, not floor out at 50+.
    aai = compute_aai(pred_score=20.0, sentiment_score=normalise_sentiment(-0.8), risk_score=20.0)
    assert aai < 30.0
