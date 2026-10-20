"""Backtest accounting (D34; docs/EVALUATION.md rules 4-5). Pure functions, no I/O.

Windows are non-overlapping 30-day periods. Long-only spot: BUY = long for the window; HOLD, SELL and
UNCERTAIN = cash (0 return). A fee of `fee` per side is charged on each change of position. Every strategy
and baseline starts in cash, and there is no exit fee at the end (the final position is marked to market).
Net window return = (1 - fee * |position change|) * (1 + position * asset return) - 1.
"""

import numpy as np

from ml import config
from ml.evaluation import metrics as m
from ml.evaluation.run_baselines import WINDOWS_PER_YEAR, _add_note, strategy_stats


def positions(signals) -> np.ndarray:
    """1 = long (BUY), 0 = cash (HOLD, SELL, UNCERTAIN)."""
    bad = [s for s in signals if s not in config.SIGNALS]
    if bad:
        raise ValueError(f"unknown signals: {sorted(set(bad))}")
    return np.array([1 if s == "BUY" else 0 for s in signals], dtype=int)


def position_changes(pos) -> np.ndarray:
    """|position change| at the start of each window, starting from cash."""
    pos = np.asarray(pos, dtype=int)
    return np.abs(pos - np.r_[0, pos[:-1]])


def net_window_returns(asset_returns, pos, fee: float) -> np.ndarray:
    r, pos = np.asarray(asset_returns, dtype=float), np.asarray(pos, dtype=int)
    return (1 - fee * position_changes(pos)) * (1 + pos * r) - 1


def trades(pos) -> int:
    """Number of position changes (each entry and each exit counts once)."""
    return int(position_changes(pos).sum())


def pct_cash(pos) -> float:
    """Percent (0-100) of windows in cash."""
    return float(100 * np.mean(np.asarray(pos) == 0))


def hit_rate(asset_returns, pos) -> float | None:
    """Share of in-market windows where the asset rose (before fees). None if never in the market."""
    long = np.asarray(pos) == 1
    return float(np.mean(np.asarray(asset_returns, dtype=float)[long] > 0)) if long.any() else None


def strategy_block(asset_returns, pos, fee: float) -> dict:
    """strategy_stats of the net window returns, plus trades, pct_cash and the in-market hit rate."""
    res = strategy_stats(net_window_returns(asset_returns, pos, fee))
    res.update({"trades": trades(pos), "pct_cash": pct_cash(pos), "hit_rate": hit_rate(asset_returns, pos),
                "positions": [int(p) for p in pos]})
    if res["hit_rate"] is None:
        _add_note(res, "hit_rate is null: no window with a position (no trades)")
    return res


def random_positions(n_windows: int, runs: int, p_buy: float, seed: int) -> np.ndarray:
    """runs x n_windows matrix of 0/1 positions; each window is BUY with probability p_buy."""
    return (np.random.default_rng(seed).random((runs, n_windows)) < p_buy).astype(int)


def percentile_rank(values, x: float | None) -> float | None:
    """Percent of values below x (ties count half). NaN values are ignored."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if x is None or not len(v):
        return None
    return float(100 * (np.mean(v < x) + 0.5 * np.mean(v == x)))


def random_baseline(asset_returns, fee: float, runs: int, p_buy: float, seed: int,
                    reference: dict | None = None) -> dict:
    """Random-signal baseline: percentiles of cumulative return and Sharpe over `runs` seeded runs."""
    pos = random_positions(len(asset_returns), runs, p_buy, seed)
    nets = [net_window_returns(asset_returns, p, fee) for p in pos]
    cum = np.array([m.cumulative_return(r) for r in nets])
    sh = np.array([np.nan if (s := m.sharpe(r, WINDOWS_PER_YEAR)) is None else s for r in nets])
    pct = (5, 50, 95)
    out = {
        "runs": runs, "p_buy": p_buy, "seed": seed,
        "cumulative_return_percentiles": {f"p{q}": float(np.percentile(cum, q)) for q in pct},
        "sharpe_percentiles": {f"p{q}": float(np.nanpercentile(sh, q)) for q in pct},
        "runs_with_null_sharpe": int(np.isnan(sh).sum()),
        "trades_median": float(np.median([trades(p) for p in pos])),
    }
    if reference is not None:
        out["reference_percentile_rank"] = {
            "cumulative_return": percentile_rank(cum, reference["cumulative_return"]),
            "sharpe": percentile_rank(sh, reference["sharpe_annualised"]),
        }
    return out
