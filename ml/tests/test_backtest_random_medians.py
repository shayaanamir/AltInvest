"""Tests for the random baseline's median max drawdown and median in-market hit rate (Phase 6a Step 0a).

All fixtures below are small HAND-MADE numbers, NOT market data. p_buy of 1 or 0 makes every run identical.
"""

import pytest

from ml.evaluation import backtest as bt


def test_medians_by_hand_when_always_in_market():
    # Always long, no fee: equity 1 -> 1.1 -> 0.99, so max drawdown 0.99 / 1.1 - 1 = -0.1; rose in 1 of 2 windows.
    out = bt.random_baseline([0.1, -0.1], fee=0.0, runs=5, p_buy=1.0, seed=0)
    assert out["max_drawdown_median"] == pytest.approx(-0.1)
    assert out["hit_rate_median"] == pytest.approx(0.5)


# Every run has a null Sharpe here, so the existing Sharpe percentiles warn on an all-NaN slice.
@pytest.mark.filterwarnings("ignore:All-NaN slice encountered")
def test_hit_rate_median_is_null_when_never_in_market():
    out = bt.random_baseline([0.1, -0.1], fee=0.001, runs=5, p_buy=0.0, seed=0)
    assert out["hit_rate_median"] is None
    assert out["max_drawdown_median"] == 0.0
