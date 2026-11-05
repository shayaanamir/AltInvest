"""D44 approval for Phase 9 (D25 applied with a per-row loss): rank configs on the first 60% of folds, confirm
the top config on the last 40% against the strongest baseline with a paired moving-block bootstrap 95% CI
(block = h). Approved only if the CI of baseline loss minus model loss excludes 0 and the estimate is positive.
No minimum margin, no Diebold-Mariano test. Pure functions on pooled walk-forward rows, no I/O.
"""

import numpy as np
import pandas as pd

from ml.evaluation import metrics as m
from ml.evaluation.run_walkforward_risk import split_folds
from ml.evaluation.walkforward import Fold


def _mean(x: np.ndarray) -> float:
    return float(np.mean(x))


def _dates(p: pd.DataFrame) -> list[str]:
    return [p.index[0].strftime("%Y-%m-%d"), p.index[-1].strftime("%Y-%m-%d")]


def rank_and_confirm(pooled: pd.DataFrame, folds: list[Fold], losses: dict[str, np.ndarray],
                     configs: list[str], baselines: list[str], horizon: int) -> dict:
    """`losses` maps every config and baseline name to its per-row loss on `pooled` (lower is better).

    Ranking: configs by mean loss on the ranking folds. Confirmation: the top config against the baseline
    with the lower mean loss on the confirmation folds (D44 'strongest baseline').
    """
    rank_folds, conf_folds = split_folds(folds)
    in_rank = pooled["origin"].isin([f.origin for f in rank_folds]).to_numpy()
    for name, loss in losses.items():
        if len(loss) != len(pooled) or np.isnan(loss).any():
            raise ValueError(f"loss of {name} has {len(loss)} rows or NaNs; pooled has {len(pooled)} rows")
    rank_loss = {k: _mean(v[in_rank]) for k, v in losses.items()}
    conf_loss = {k: _mean(v[~in_rank]) for k, v in losses.items()}
    order = sorted(configs, key=lambda c: rank_loss[c])
    top = order[0]
    bar = min(baselines, key=lambda b: conf_loss[b])
    diff = m.paired_bootstrap_ci(losses[bar][~in_rank], losses[top][~in_rank], _mean, block_size=horizon)
    approved = bool(diff is not None and diff["estimate"] > 0 and diff["low"] > 0)
    p_rank, p_conf = pooled[in_rank], pooled[~in_rank]
    return {
        "ranking_first_60pct": {"n_folds": len(rank_folds), "n_pooled": len(p_rank),
                                "n_effective": len(p_rank) / horizon, "date_range": _dates(p_rank),
                                "order": order, "mean_loss": rank_loss},
        "confirmation_last_40pct": {"n_folds": len(conf_folds), "n_pooled": len(p_conf),
                                    "n_effective": len(p_conf) / horizon, "date_range": _dates(p_conf),
                                    "mean_loss": conf_loss},
        "verdict": {"top_config": top, "baseline": bar, "model_loss": conf_loss[top],
                    "baseline_loss": conf_loss[bar], "paired_diff_baseline_minus_model": diff,
                    "approved": approved},
    }
