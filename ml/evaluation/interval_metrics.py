"""Interval metrics for the 80% range of the h-day log return (D43). Pure functions, no I/O.

Winkler (interval) score per row, alpha = 1 - nominal coverage:
    (U - L) + (2 / alpha) x (L - y) if y < L,  + (2 / alpha) x (y - U) if y > U.   Lower is better.
"""

import numpy as np

from ml import config

ALPHA = 1 - config.RANGE_COVERAGE


def ordered(lo, hi) -> tuple[np.ndarray, np.ndarray, int]:
    """(L, U, n_crossed): bounds sorted per row; quantile models can cross, which is counted, not hidden."""
    lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
    return np.minimum(lo, hi), np.maximum(lo, hi), int(np.sum(lo > hi))


def winkler(lo, hi, y, alpha: float = ALPHA) -> np.ndarray:
    lo, hi, _ = ordered(lo, hi)
    y = np.asarray(y, dtype=float)
    return (hi - lo) + (2 / alpha) * np.clip(lo - y, 0, None) + (2 / alpha) * np.clip(y - hi, 0, None)


def summary(lo, hi, y, high_vol) -> dict:
    """Coverage, tail misses (each should be about alpha / 2), width, and coverage on high-volatility rows."""
    lo, hi, crossed = ordered(lo, hi)
    y, high_vol = np.asarray(y, dtype=float), np.asarray(high_vol, dtype=bool)
    inside = (y >= lo) & (y <= hi)
    return {
        "n": int(len(y)),
        "mean_interval_score": float(np.mean(winkler(lo, hi, y))),
        "coverage": float(np.mean(inside)),
        "lower_tail_miss": float(np.mean(y < lo)),
        "upper_tail_miss": float(np.mean(y > hi)),
        "mean_width": float(np.mean(hi - lo)),
        "n_high_vol": int(high_vol.sum()),
        "coverage_high_vol": float(np.mean(inside[high_vol])) if high_vol.any() else None,
        "n_crossed": crossed,
    }


def passes(s: dict) -> dict:
    """D44 coverage and tail conditions on a summary (the paired-CI condition is checked separately)."""
    lo, hi = config.RANGE_COVERAGE_BOUNDS
    cov_ok = lo <= s["coverage"] <= hi
    tails_ok = max(s["lower_tail_miss"], s["upper_tail_miss"]) <= config.RANGE_TAIL_MISS_MAX
    return {"coverage_in_bounds": bool(cov_ok), "tails_within_max": bool(tails_ok),
            "coverage_bounds": list(config.RANGE_COVERAGE_BOUNDS), "tail_max": config.RANGE_TAIL_MISS_MAX}
