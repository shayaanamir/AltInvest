"""Tests for the backtest accounting and runner (Phase 5b, D34).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import backtest as bt
from ml.evaluation.run_backtest import backtest, origin_rows
from ml.evaluation.run_walkforward import dev_data

H, W = config.HORIZON_DAYS, config.WARMUP_ROWS
N, B2, MIN_TRAIN = 300, 255, 100                 # fixture geometry: 4 folds, sealed test from row 255
TOP = "logreg_c0.1"


def _raw():
    """Hand-made daily bars (not market data): a trend, two waves and a slowly changing wobble."""
    i = np.arange(N + W, dtype=float)
    close = 100 + 0.2 * i + 15 * np.sin(i / 9) + (2 + 1.5 * np.sin(i / 40)) * np.cos(i * 1.7)
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * (1.02 + 0.005 * np.sin(i / 6)), "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _origins():
    data = dev_data(_raw().iloc[:W + B2].copy())
    return origin_rows(data, B2, TOP, min_train=MIN_TRAIN)


def test_fee_charged_once_per_position_change():
    pos = [0, 1, 1, 0, 1]
    r = [0.1, 0.2, -0.1, 0.05, 0.3]
    fee = 0.01
    # changes 0,1,0,1,1: w0 cash 0; w1 enter 0.99*1.2-1; w2 hold -0.1; w3 exit 0.99-1; w4 enter 0.99*1.3-1
    expected = [0.0, 0.188, -0.1, -0.01, 0.287]
    assert bt.net_window_returns(r, pos, fee) == pytest.approx(expected)
    assert bt.trades(pos) == 3
    assert bt.pct_cash(pos) == pytest.approx(40.0)


def test_sell_hold_uncertain_are_cash_with_zero_return():
    pos = bt.positions(["SELL", "HOLD", "UNCERTAIN"])
    assert pos.tolist() == [0, 0, 0]
    assert bt.net_window_returns([0.3, -0.2, 0.1], pos, 0.001).tolist() == [0.0, 0.0, 0.0]
    assert bt.positions(["BUY", "SELL"]).tolist() == [1, 0]
    with pytest.raises(ValueError):
        bt.positions(["STRONG_BUY"])


def test_hit_rate_null_without_trades():
    block = bt.strategy_block([0.1, -0.2, 0.3], [0, 0, 0], 0.001)
    assert block["hit_rate"] is None and block["trades"] == 0 and "no trades" in block["note"]
    assert bt.hit_rate([0.1, -0.2, 0.3], [1, 1, 0]) == pytest.approx(0.5)     # rose in 1 of 2 long windows


def test_random_baseline_reproducible():
    r = 0.05 * np.sin(np.arange(40) / 3)
    a = bt.random_baseline(r, 0.001, runs=200, p_buy=0.5, seed=0)
    assert a == bt.random_baseline(r, 0.001, runs=200, p_buy=0.5, seed=0)
    assert a != bt.random_baseline(r, 0.001, runs=200, p_buy=0.5, seed=1)
    assert bt.random_positions(40, 200, 0.5, 0).mean() == pytest.approx(0.5, abs=0.03)


def test_percentile_rank():
    assert bt.percentile_rank([1, 2, 3, 4], 3) == pytest.approx(62.5)            # 2 below, 1 tie -> 2.5/4
    assert bt.percentile_rank([1, 2, np.nan], 5) == pytest.approx(100.0)
    assert bt.percentile_rank([1, 2], None) is None


def test_windows_are_fold_origins_30_apart_and_before_b2():
    at, folds, _ = _origins()
    rows = at["row"].tolist()
    assert rows == [f.origin for f in folds]
    assert all(b - a == H for a, b in zip(rows, rows[1:]))
    assert max(rows) + H < B2                                                    # labels end before b2


def test_served_policy_equals_always_hold():
    at, _, _ = _origins()
    res = backtest("eth", at, TOP)
    assert res["strategies"]["served"]["signal_counts"] == {"UNCERTAIN": len(at)}
    assert res["checks"] == {"served_trades": 0, "served_equals_always_hold": True}


def test_backtest_calls_generate_signal(monkeypatch):
    at, _, _ = _origins()
    monkeypatch.setattr("ml.signal.signal_logic.generate_signal",
                        lambda *args, **kwargs: {"signal": "BUY", "confidence": None, "note": "test"})
    res = backtest("eth", at, TOP)
    raw = np.exp(at["fwd_return_30d"].to_numpy()) - 1
    expected = raw.copy()
    expected[0] = (1 - config.BACKTEST_FEE_PER_SIDE) * (1 + raw[0]) - 1         # buy-and-hold minus the entry fee
    for name in ("served", "reference"):
        assert res["strategies"][name]["window_returns"] == pytest.approx(expected.tolist(), abs=1e-15)
        assert res["strategies"][name]["window_returns"] == res["baselines"]["buy_and_hold"]["window_returns"]
