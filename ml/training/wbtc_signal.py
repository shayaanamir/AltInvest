# wbtc_signal.py
# BUY / SELL / HOLD signal combination for the WBTC pipeline.
# Single transparent function -- no abstraction layer.

UP_THRESHOLD   = 0.50   # minimum P(UP) to trigger BUY
DOWN_THRESHOLD = 0.50   # minimum P(DOWN) to trigger SELL
RISK_THRESHOLD = 70.0   # max risk_score (0-100) to allow a trade


def generate_signal(
    prob_up,
    prob_down,
    trend_return,
    risk_score,
    up_threshold=UP_THRESHOLD,
    down_threshold=DOWN_THRESHOLD,
    risk_threshold=RISK_THRESHOLD,
):
    """
    Generate BUY / SELL / HOLD from DirectionClassifier + trend + risk inputs.

    Parameters
    ----------
    prob_up       : P(UP) from DirectionClassifier [0..1]
    prob_down     : P(DOWN) from DirectionClassifier [0..1]
    trend_return  : return_30d (backward-looking log-return, leakage-free).
                    Positive = bullish, negative = bearish.
    risk_score    : 0-100 from RiskClassifier (lower = less risky)
    up_threshold   : minimum prob_up   to trigger BUY  (default 0.50)
    down_threshold : minimum prob_down to trigger SELL (default 0.50)
    risk_threshold : maximum risk_score to allow a trade (default 70)

    Returns
    -------
    str : 'BUY' | 'SELL' | 'HOLD'

    Rules
    -----
    BUY  : prob_up   >= up_threshold   AND trend_return > 0 AND risk_ok
    SELL : prob_down >= down_threshold AND trend_return < 0 AND risk_ok
    HOLD : otherwise
    """
    risk_ok = risk_score <= risk_threshold

    if prob_up >= up_threshold and trend_return > 0 and risk_ok:
        return "BUY"

    if prob_down >= down_threshold and trend_return < 0 and risk_ok:
        return "SELL"

    return "HOLD"
