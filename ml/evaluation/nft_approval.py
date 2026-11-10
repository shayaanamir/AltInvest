"""Pooled approval across NFT collections (D59 as amended 2026-11-10; D44 applied to all collections at once).

Configs are ranked on the first 60% of every collection's folds together; the top config is confirmed on the
last 40% of every collection's folds together. The paired 95% CI of mean(baseline loss) - mean(model loss)
comes from a moving-block bootstrap BY DATE: blocks of `block` consecutive calendar dates are resampled, and
all collections' rows of a date move together, so the dependence between collections on the same day and
between neighbouring days (overlapping 30-day windows) is kept. Approved only if the CI excludes 0 with a
positive estimate AND every collection's own point estimate is not worse than the baseline.
Pure functions on per-row losses, no I/O.
"""

import math

import numpy as np


def date_block_ci(dates, a, b, block: int = 30, n_boot: int = 1000, seed: int = 0, level: float = 0.95
                  ) -> dict | None:
    """CI of mean(a) - mean(b) over all rows; `dates` gives each row's date. None with fewer dates than a block."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    uniq, inv = np.unique(np.asarray(dates), return_inverse=True)
    n = len(uniq)
    if n < block or block < 1:
        return None
    diff, count = np.bincount(inv, a - b, minlength=n), np.bincount(inv, minlength=n)
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=(n_boot, n_blocks))
    offsets = np.arange(block)
    stats = np.empty(n_boot)
    for i in range(n_boot):
        idx = (starts[i][:, None] + offsets).ravel()[:n]
        stats[i] = diff[idx].sum() / count[idx].sum()
    alpha = (1 - level) / 2
    return {"estimate": float(a.mean() - b.mean()),
            "low": float(np.quantile(stats, alpha)), "high": float(np.quantile(stats, 1 - alpha)),
            "level": level, "block_size": block, "block_unit": "calendar dates (all collections together)",
            "n_dates": int(n), "n_boot": n_boot, "seed": seed}


def pooled_rank_and_confirm(rows: dict, configs: list[str], baseline: str, block: int) -> dict:
    """`rows[slug]` = {"dates": per-row dates, "in_rank": bool per row, "losses": {name: per-row loss}}.

    Returns the ranking and confirmation summaries and the verdict for the top config of `configs`.
    """
    def cat(name, part):
        return np.concatenate([r["losses"][name][r["in_rank"] if part == "rank" else ~r["in_rank"]]
                               for r in rows.values()])

    names = configs + [baseline]
    rank_loss = {c: float(cat(c, "rank").mean()) for c in names}
    conf_loss = {c: float(cat(c, "conf").mean()) for c in names}
    order = sorted(configs, key=lambda c: rank_loss[c])
    top = order[0]
    dates = np.concatenate([np.asarray(r["dates"])[~r["in_rank"]] for r in rows.values()])
    ci = date_block_ci(dates, cat(baseline, "conf"), cat(top, "conf"), block=block)
    per = {slug: float(r["losses"][baseline][~r["in_rank"]].mean() - r["losses"][top][~r["in_rank"]].mean())
           for slug, r in rows.items()}
    ci_ok = bool(ci is not None and ci["estimate"] > 0 and ci["low"] > 0)
    none_worse = all(v >= 0 for v in per.values())
    n_conf, n_dates = len(dates), len(np.unique(dates))
    return {
        "ranking_first_60pct": {"n_pooled": int(sum(r["in_rank"].sum() for r in rows.values())),
                                "order": order, "mean_loss": rank_loss},
        "confirmation_last_40pct": {"n_pooled": n_conf, "n_dates": n_dates,
                                    "n_effective_rows_over_h": n_conf / block,
                                    "n_effective_dates_over_h": n_dates / block,
                                    "date_range": [str(dates.min()), str(dates.max())], "mean_loss": conf_loss},
        "verdict": {"top_config": top, "baseline": baseline, "model_loss": conf_loss[top],
                    "baseline_loss": conf_loss[baseline], "paired_diff_baseline_minus_model": ci,
                    "pooled_ci_excludes_0": ci_ok, "per_collection_baseline_minus_model": per,
                    "every_collection_not_worse": none_worse, "approved": bool(ci_ok and none_worse)},
    }
