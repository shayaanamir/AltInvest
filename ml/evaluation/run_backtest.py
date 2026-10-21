"""Non-overlapping backtest on the walk-forward fold origins (Phase 5b, D33, D34). Pre-test only.

    python -m ml.evaluation.run_backtest --asset btc

Writes ml/reports/{asset}/backtest.json. One 30-day window per fold origin; the signal at origin t comes
from that fold's fit (Phase 4.0 harness, so the test split stays sealed). Every signal comes from
ml.signal.signal_logic.generate_signal. Strategies: served (D33, all UNCERTAIN) and the reference row
(4c top config with serving forced on; evidence only, never served). Nothing here is an approval (D32, D34).
"""

import argparse
import json
from collections import Counter

import numpy as np
import pandas as pd

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation import backtest as bt
from ml.evaluation import metrics as m
from ml.evaluation.baselines import strategy_window_returns
from ml.evaluation.run_baselines import _clean
from ml.evaluation.run_walkforward import load_dev, run_metadata
from ml.evaluation.run_walkforward_direction import prob_columns
from ml.evaluation.walkforward import make_folds, run_folds
from ml.labels.labels import DIRECTION_CLASSES
from ml.models import direction
from ml.signal import signal_logic

FEE = config.BACKTEST_FEE_PER_SIDE


def origin_rows(data: pd.DataFrame, b2: int, top: str, min_train: int = config.MIN_TRAIN_ROWS):
    """(pooled rows at the fold origins, folds, all pooled rows) for the 4c top config. Pre-test only."""
    folds = make_folds(len(data), b2, min_train)
    cache = direction.FitCache({top: direction.CONFIGS[top]})
    pooled, _ = run_folds(data, folds, direction.specs(cache), b2)
    at = pooled[pooled["row"].isin([f.origin for f in folds])]
    return at, folds, pooled


def window_signals(asset: str, at: pd.DataFrame, top: str, serve: bool | None) -> list[dict]:
    """generate_signal for every window. serve=None uses the serving rule (config.DIRECTION_SERVED, D33)."""
    out = []
    for row in at[prob_columns(top)].to_numpy():
        probs = dict(zip(DIRECTION_CLASSES, (float(p) for p in row)))
        out.append(signal_logic.generate_signal(asset, probs) if serve is None
                   else signal_logic.generate_signal(asset, probs, serve=serve))
    return out


def _paired(a: np.ndarray, b: np.ndarray) -> dict:
    ci = m.paired_bootstrap_ci(a, b, np.mean, block_size=1)
    return {**ci, "ci_half_width": (ci["high"] - ci["low"]) / 2} if ci else None


def backtest(asset: str, at: pd.DataFrame, top: str) -> dict:
    """Strategies, baselines and paired CIs for the windows in `at` (one row per fold origin)."""
    r = strategy_window_returns(at["fwd_return_30d"], list(range(len(at))))["buy_and_hold"]   # gross
    signals = {"served": window_signals(asset, at, top, serve=None),
               "reference": window_signals(asset, at, top, serve=True)}
    strategies = {}
    for name, sig in signals.items():
        block = bt.strategy_block(r, bt.positions([s["signal"] for s in sig]), FEE)
        block["signal_counts"] = dict(Counter(s["signal"] for s in sig))
        block["confidence_values"] = sorted({str(s["confidence"]) for s in sig})
        strategies[name] = block
    baselines = {"buy_and_hold": bt.strategy_block(r, np.ones(len(r), dtype=int), FEE),
                 "always_hold": bt.strategy_block(r, np.zeros(len(r), dtype=int), FEE)}
    baselines["random"] = bt.random_baseline(r, FEE, config.RANDOM_BASELINE_RUNS, config.RANDOM_BASELINE_P_BUY,
                                             config.RANDOM_BASELINE_SEED, reference=strategies["reference"])
    ref = np.array(strategies["reference"]["window_returns"])
    paired = {f"reference_minus_{b}": _paired(ref, np.array(baselines[b]["window_returns"]))
              for b in ("buy_and_hold", "always_hold")}
    served_eq = strategies["served"]["window_returns"] == baselines["always_hold"]["window_returns"]
    return {"strategies": strategies, "baselines": baselines,
            "paired_mean_window_return": paired,
            "checks": {"served_trades": strategies["served"]["trades"],
                       "served_equals_always_hold": bool(served_eq and strategies["served"]["trades"] == 0)}}


def run(asset: str) -> dict:
    wf = json.loads((ML_ROOT / "reports" / asset / "walkforward_direction.json").read_text(encoding="utf-8"))
    top = wf["verdict"]["top_config"]
    data, b2, n = load_dev(asset)
    at, folds, pooled = origin_rows(data, b2, top)
    report = {
        "protocol": {
            "decision": "D34", "serving_rule": "D33",
            "windows": "walk-forward fold origins (non-overlapping, 30 rows apart, pre-test only)",
            "positions": "long-only spot; BUY = long for the 30-day window; HOLD, SELL, UNCERTAIN = cash",
            "fee_per_side": FEE,
            "fee_rule": "charged on each change of position; every strategy and baseline starts in cash; "
                        "no exit fee at the end (final position marked to market)",
            "hit_rate": "share of in-market windows where the asset rose (before fees)",
            "reference_config": top, "reference_source": f"ml/reports/{asset}/walkforward_direction.json",
            "n_folds": len(folds), "n_windows": len(at),
            "first_window_date": at.index[0].strftime("%Y-%m-%d"),
            "last_window_date": at.index[-1].strftime("%Y-%m-%d"),
            "window_rows": [int(x) for x in at["row"]],
            "bootstrap_block_size": 1,
        },
        **backtest(asset, at, top),
    }
    half = report["paired_mean_window_return"]["reference_minus_buy_and_hold"]["ci_half_width"]
    report["power"] = {"n_windows": len(at), "ci_half_width_reference_minus_buy_and_hold": half,
                       "note": (f"Only {len(at)} windows: a difference in mean window return smaller than about "
                                f"{half:.4f} cannot be confirmed; a non-significant difference means 'no "
                                "demonstrated gain' (D29, D30). Reported, not used for approval (D32, D34).")}
    report["metadata"] = run_metadata(asset, data, b2, n, pooled)
    report["metadata"]["note"] = ("Backtest on walk-forward fold origins (D21, D34). Signals from "
                                  "ml.signal.signal_logic.generate_signal. Test rows [b2, n) were never built or read.")
    return _clean(report)


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    parser = argparse.ArgumentParser(description="Non-overlapping backtest on the walk-forward fold origins")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    require_validated(asset)
    report = run(asset)
    out = ML_ROOT / "reports" / asset / "backtest.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
