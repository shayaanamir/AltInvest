"""Fair-value walk-forward and approval protocol (Phase 10 step 10.6a, D76), fixed before any model or baseline run.

FOLDS: expanding window over development sales (before 2026-01-25). Test months 2025-05 .. 2026-01 (9 folds; the
last one ends at 2026-01-25). Fold k trains on clean sales with timestamp < test_start - 7 days (the 7-day
embargo) and tests on clean sales with timestamp in [test_start, test_end). Inputs known at t (features) may use
sales in the embargo and earlier in the test month (D48: the embargo is for labels, not inputs).
METRIC: APE = |exp(y_hat - y) - 1| = |fair value / price - 1|; MdAPE = the median APE, pooled over collections.
SELECTION (D25/D44 as written, D65i top-only; D32): rank ALL candidates together by pooled MdAPE on the first
floor(0.6 x 9) = 5 folds; only the top-ranked one is confirmed on the last 4. Baseline to beat = B0 or B1, the
one with the lower MdAPE on the confirmation folds (D44). Approved only if (a) the paired 95% CI of
MdAPE(baseline) - MdAPE(model) on the confirmation rows excludes 0 with a positive estimate, by a moving-block
bootstrap of calendar dates (block 7 days; every collection's rows of a date move together; 1000 resamples,
seed 0), and (b) the model's ranking MdAPE is below the better baseline's ranking MdAPE (D32).
RANGE (D44 range rule; plan step 10.6): the 80% range of the approved model is approved only if, on the
confirmation rows, coverage is in [0.75, 0.85], each tail miss is <= 0.15, and the paired date-block CI of mean
interval score (the B0/B1 range with the lower confirmation interval score minus the model) excludes 0 with a
positive estimate. Bounds are in y (log premium) space, so coverage is the same in price.
AMENDED (10.6a review, before any run): baselines are B0, B1 and B2 (the trailing 90-day decile median); the
better baseline is the best of the three (D44). RANGE FALLBACK: D44 says only 'A part that is not served keeps
its baseline'; it does not say which of several baseline ranges, or whether it must be calibrated. Declared: if
the point model is approved but its range is not, the point estimate is served with the range of the baseline
with the lower confirmation interval score (the 'baseline range to beat'), only if that range's confirmation
coverage is in [0.75, 0.85]; otherwise no range. PER-COLLECTION SERVING GUARD: approval stays pooled. If the top
candidate is approved, a collection is served the model only if its confirmation MdAPE on that collection is <=
the best of B0/B1/B2 on that collection; otherwise it serves that best baseline, with that baseline's own range
only if the range's coverage on the collection's confirmation rows is in [0.75, 0.85] (otherwise no range).
Collections served the model take the pooled range decision. With no approved model nothing is chosen here.
Pure functions, no I/O.
"""

import math

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation import interval_metrics as im
from ml.evaluation.nft_approval import date_block_ci

FIRST_TEST_MONTH = "2025-05"            # D60: 6 months of sales before it
EMBARGO_DAYS = 7
BLOCK_DAYS = 7                          # D60, checkpoint 10.5c handoff
N_BOOT = 1000
SEED = 0
RANK_SHARE = 0.6                        # D25
BASELINES = ("B0_floor", "B1_rarity_decile", "B2_decile_90d")


def dev_end() -> pd.Timestamp:
    return pd.Timestamp(config.NFT_FV_SEALED_START, tz="UTC") - pd.Timedelta(days=EMBARGO_DAYS)


def folds() -> list[dict]:
    """The declared folds: test months from FIRST_TEST_MONTH until the development end (2026-01-25)."""
    end, out = dev_end(), []
    start = pd.Timestamp(f"{FIRST_TEST_MONTH}-01", tz="UTC")
    while start < end:
        nxt = start + pd.offsets.MonthBegin(1)
        out.append({"fold": len(out) + 1, "train_end": start - pd.Timedelta(days=EMBARGO_DAYS), "test_start": start,
                    "test_end": min(nxt, end)})
        start = nxt
    n_rank = math.floor(RANK_SHARE * len(out))
    for f in out:
        f["part"] = "rank" if f["fold"] <= n_rank else "confirm"
    return out


def fold_rows(frame: pd.DataFrame, fold: dict) -> tuple[np.ndarray, np.ndarray]:
    """(train mask, test mask) over `frame` (clean rows with a `timestamp` column in Unix seconds)."""
    t = frame["timestamp"].to_numpy()
    cut = lambda ts: int(ts.timestamp())                                   # noqa: E731
    train = t < cut(fold["train_end"])
    test = (t >= cut(fold["test_start"])) & (t < cut(fold["test_end"]))
    return train, test


def ape(y_hat, y) -> np.ndarray:
    return np.abs(np.exp(np.asarray(y_hat, dtype=float) - np.asarray(y, dtype=float)) - 1)


def date_block_stat_ci(dates, a, b, stat=np.median, block: int = BLOCK_DAYS, n_boot: int = N_BOOT,
                       seed: int = SEED, level: float = 0.95) -> dict | None:
    """CI of stat(a) - stat(b) with the same moving-block resampling of calendar dates as
    nft_approval.date_block_ci (same random starts): all rows of a resampled date enter together."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    uniq, inv = np.unique(np.asarray(dates), return_inverse=True)
    n = len(uniq)
    if n < block or block < 1:
        return None
    order = np.argsort(inv, kind="stable")
    bounds = np.searchsorted(inv[order], np.arange(n + 1))
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=(n_boot, n_blocks))
    offsets = np.arange(block)
    stats = np.empty(n_boot)
    for i in range(n_boot):
        d = (starts[i][:, None] + offsets).ravel()[:n]
        rows = order[np.concatenate([np.arange(bounds[j], bounds[j + 1]) for j in d])]
        stats[i] = stat(a[rows]) - stat(b[rows])
    alpha = (1 - level) / 2
    return {"estimate": float(stat(a) - stat(b)), "low": float(np.quantile(stats, alpha)),
            "high": float(np.quantile(stats, 1 - alpha)), "level": level, "block_size": block,
            "block_unit": "calendar dates (all collections together)", "n_dates": int(n), "n_boot": n_boot,
            "seed": seed}


def _range(rows: pd.DataFrame, name: str) -> dict:
    lo, hi, y = rows[f"lo:{name}"], rows[f"hi:{name}"], rows["y"]
    s = im.summary(lo, hi, y, np.zeros(len(rows), dtype=bool))
    s = {k: v for k, v in s.items() if k not in ("n_high_vol", "coverage_high_vol")}
    return {**s, **im.passes(s)}


def select(rows: pd.DataFrame, candidates: list[str]) -> dict:
    """`rows`: one row per (fold, test sale) with fold, part, date, y, ape:<name>, lo:<name>, hi:<name> for every
    candidate and baseline. Applies the declared rule; every candidate's numbers are reported, only the top is tested."""
    rank, conf = rows[rows["part"] == "rank"], rows[rows["part"] == "confirm"]
    names = list(candidates) + list(BASELINES)
    md = lambda df, n: float(np.median(df[f"ape:{n}"]))                    # noqa: E731
    rank_md, conf_md = {n: md(rank, n) for n in names}, {n: md(conf, n) for n in names}
    order = sorted(candidates, key=lambda c: (rank_md[c], candidates.index(c)))
    top = order[0]
    best_rank_base = min(BASELINES, key=lambda b: rank_md[b])
    best_conf_base = min(BASELINES, key=lambda b: conf_md[b])
    ci = date_block_stat_ci(conf["date"], conf[f"ape:{best_conf_base}"], conf[f"ape:{top}"])
    ci_ok = bool(ci is not None and ci["estimate"] > 0 and ci["low"] > 0)
    d32_ok = bool(rank_md[top] < rank_md[best_rank_base])
    approved = ci_ok and d32_ok
    ranges = {n: _range(conf, n) for n in [top, *BASELINES]}
    is_ = {n: im.winkler(conf[f"lo:{n}"], conf[f"hi:{n}"], conf["y"]) for n in [top, *BASELINES]}
    best_range_base = min(BASELINES, key=lambda b: ranges[b]["mean_interval_score"])
    is_ci = date_block_ci(conf["date"], is_[best_range_base], is_[top], block=BLOCK_DAYS, n_boot=N_BOOT, seed=SEED)
    is_ok = bool(is_ci is not None and is_ci["estimate"] > 0 and is_ci["low"] > 0)
    r = ranges[top]
    range_ok = bool(approved and is_ok and r["coverage_in_bounds"] and r["tails_within_max"])
    fallback_ok = bool(ranges[best_range_base]["coverage_in_bounds"])
    served_range = (top if range_ok else best_range_base if fallback_ok else None) if approved else None
    n_dates = conf["date"].nunique()
    return {
        "ranking_first_60pct": {"n_rows": len(rank), "n_dates": int(rank["date"].nunique()), "order": order,
                                "mdape": rank_md, "best_baseline": best_rank_base},
        "confirmation_last_40pct": {"n_rows": len(conf), "n_dates": int(n_dates),
                                    "n_effective_dates_over_block": n_dates / BLOCK_DAYS, "mdape": conf_md,
                                    "note": "all candidates reported; only the top-ranked one is tested"},
        "verdict": {"top_candidate": top, "baseline": best_conf_base, "model_mdape": conf_md[top],
                    "baseline_mdape": conf_md[best_conf_base], "paired_diff_baseline_minus_model": ci,
                    "ci_excludes_0_positive": ci_ok, "beats_better_baseline_on_ranking_folds_D32": d32_ok,
                    "approved": approved},
        "range": {"confirmation": ranges, "baseline_range_to_beat": best_range_base,
                  "paired_interval_score_diff_baseline_minus_model": is_ci, "interval_score_ci_ok": is_ok,
                  "approved": range_ok, "fallback_baseline_range_in_band": fallback_ok,
                  "served_range_pooled": served_range},
        "per_collection": per_collection(conf, top, approved, served_range),
    }


def per_collection(conf: pd.DataFrame, top: str, approved: bool, pooled_range: str | None) -> dict:
    """Confirmation MdAPE and range coverage per collection, and (only if approved) what each collection serves."""
    out = {}
    lo_b, hi_b = config.RANGE_COVERAGE_BOUNDS
    for slug, g in conf.groupby("slug"):
        md = {n: float(np.median(g[f"ape:{n}"])) for n in [top, *BASELINES]}
        cov = {n: float(np.mean((g["y"] >= g[f"lo:{n}"]) & (g["y"] <= g[f"hi:{n}"]))) for n in [top, *BASELINES]}
        best = min(BASELINES, key=lambda b: md[b])
        row = {"n": len(g), "mdape": md, "coverage": cov, "best_baseline": best,
               "model_not_worse_than_best_baseline": bool(md[top] <= md[best])}
        if approved:
            model = row["model_not_worse_than_best_baseline"]
            row["serve_point"] = top if model else best
            row["serve_range"] = pooled_range if model else (best if lo_b <= cov[best] <= hi_b else None)
        out[slug] = row
    return out
