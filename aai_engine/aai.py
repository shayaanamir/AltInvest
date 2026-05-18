"""
AAI Engine — Alternative Asset Index computation.

This is the core formula for the platform. It lives in /aai_engine so it
can be imported by both the backend controller and any standalone test scripts
without creating circular dependencies.

Formula (Phase 4 final weights):
    AAI = (0.40 × pred_score) + (0.30 × sentiment_score) + (0.30 × risk_score)

All inputs must be pre-normalised to [0, 100] before calling compute_aai().
Output is clamped to [0, 100].
"""


def compute_aai(
    pred_score: float,
    sentiment_score: float,
    risk_score: float,
) -> float:
    """
    Computes the AAI score from three normalised component scores.

    Args:
        pred_score:       ML prediction score, normalised to [0, 100].
        sentiment_score:  Sentiment score, normalised to [0, 100].
        risk_score:       Risk score, normalised to [0, 100]. Higher = safer.

    Returns:
        AAI score clamped to [0, 100], rounded to 2 decimal places.

    Phase 3 note: uses a provisional 2-component formula (pred 60%, risk 40%)
    until sentiment is integrated. Switch to the full formula in Phase 4.
    """
    # Phase 3 provisional (comment out and use full formula in Phase 4):
    # aai = (0.60 * pred_score) + (0.40 * risk_score)

    # Phase 4 final formula:
    aai = (0.40 * pred_score) + (0.30 * sentiment_score) + (0.30 * risk_score)

    return round(min(max(aai, 0.0), 100.0), 2)


def normalise_sentiment(compound: float) -> float:
    """
    Maps a VADER compound score from [-1, +1] to [0, 100].

    -1.0 → 0.0   (maximally negative)
     0.0 → 50.0  (neutral)
    +1.0 → 100.0 (maximally positive)
    """
    return round((compound + 1.0) * 50.0, 2)


def normalise_price(price: float, min_price: float, max_price: float) -> float:
    """
    Min-max normalises a predicted price to [0, 100] using
    the historical price range from the dataset.

    Use this in Phase 3+ when real price data is available.
    """
    if max_price == min_price:
        return 50.0
    score = ((price - min_price) / (max_price - min_price)) * 100.0
    return round(min(max(score, 0.0), 100.0), 2)


def normalise_sharpe(sharpe_scaled: float, observed_min: float, observed_max: float) -> float:
    """
    Normalises a scaled Sharpe ratio to [0, 100].
    Use this in Phase 4 when the Sharpe ratio is available from the risk engine.
    """
    if observed_max == observed_min:
        return 50.0
    score = ((sharpe_scaled - observed_min) / (observed_max - observed_min)) * 100.0
    return round(min(max(score, 0.0), 100.0), 2)
