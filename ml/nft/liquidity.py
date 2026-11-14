"""Collection liquidity (D58): rule-based, no model. Pure functions, no I/O.

For a date D everything is counted on wash-filtered sales in the 7 and 30 days that END at D 00:00 UTC, so a
row never uses a sale from D itself or later. liquidity_score = 100 x the mean of four pooled percentile
ranks (ties count half) of sales_7d, sales_30d, volume_7d_usd and volume_30d_usd among ALL collections on
all dates <= D (pooled like D36; higher = more liquid). Illiquid if sales_7d < NFT_ILLIQUID_MIN_SALES_7D.
"""

import numpy as np
import pandas as pd

from ml import config

SCORE_INPUTS = ("sales_7d", "sales_30d", "volume_7d_usd", "volume_30d_usd")
WINDOW_COLUMNS = ("sales_7d", "sales_30d", "volume_7d_eth", "volume_30d_eth", "volume_7d_usd", "volume_30d_usd")


def daily_activity(kept_sales: pd.DataFrame, dates: list[str], eth: pd.DataFrame) -> pd.DataFrame:
    """One collection: per calendar date, the sales that happened ON that date (count, ETH and USD volume).
    USD = price_eth x ETH-USD at 00:00 UTC of the sale's date (D56)."""
    s = kept_sales.merge(eth[["date", "eth_usd"]], on="date", how="left")
    s["price_usd"] = s["price_eth"] * s["eth_usd"]
    g = s.groupby("date").agg(sales_count=("price_eth", "size"), volume_eth=("price_eth", "sum"),
                              volume_usd=("price_usd", "sum"))
    return g.reindex(dates).fillna(0.0).rename_axis("date").reset_index()


def windows(activity: pd.DataFrame, first_complete: dict[int, str]) -> pd.DataFrame:
    """Trailing sums over the 7 and 30 dates BEFORE each date. A window that starts before the sales data
    does (date < first_complete[days]) is NaN, not a small number."""
    out = activity[["date"]].copy()
    for days in (7, 30):
        incomplete = (activity["date"] < first_complete[days]).to_numpy()
        for col, name in (("sales_count", f"sales_{days}d"), ("volume_eth", f"volume_{days}d_eth"),
                          ("volume_usd", f"volume_{days}d_usd")):
            v = activity[col].rolling(days).sum().shift(1)
            out[name] = v.mask(incomplete)
    return out


def first_complete_dates(sales_start: str) -> dict[int, str]:
    start = pd.Timestamp(sales_start)
    return {d: (start + pd.Timedelta(days=d)).strftime("%Y-%m-%d") for d in (7, 30)}


def pooled_percentiles(table: pd.DataFrame, column: str) -> np.ndarray:
    """Percentile rank (0-1, ties count half) of each row's value among every row dated <= its date, all
    collections together. NaN where the value is NaN. `table` has date and `column`."""
    v, d = table[column].to_numpy(dtype=float), table["date"].to_numpy()
    out = np.full(len(v), np.nan)
    ok = ~np.isnan(v)
    order = np.argsort(d[ok], kind="stable")
    vv, dd, pos = v[ok][order], d[ok][order], np.flatnonzero(ok)[order]
    ends = np.searchsorted(dd, dd, side="right")                # rows dated <= this row's date
    for i in range(len(vv)):
        pool = vv[:ends[i]]
        out[pos[i]] = ((pool < vv[i]).sum() + 0.5 * (pool == vv[i]).sum()) / len(pool)
    return out


def label(score: float, is_illiquid: bool) -> str | None:
    if score is None or np.isnan(score):
        return None
    if is_illiquid:
        return "Illiquid"
    lo, hi = config.NFT_LIQUIDITY_LABEL_BOUNDS
    return "High" if score >= hi else "Medium" if score >= lo else "Low"


def add_scores(table: pd.DataFrame) -> pd.DataFrame:
    """Adds liquidity_score, is_illiquid and liquidity_label to rows (slug, date, the window columns) of all
    collections. Rows whose 30-day window is incomplete get NaN / None."""
    out = table.copy()
    ranks = np.column_stack([pooled_percentiles(out, c) for c in SCORE_INPUTS])
    out["liquidity_score"] = 100 * ranks.mean(axis=1)           # NaN if any of the four is NaN
    out["is_illiquid"] = out["sales_7d"] < config.NFT_ILLIQUID_MIN_SALES_7D
    out["liquidity_label"] = [label(s, bool(i)) for s, i in zip(out["liquidity_score"], out["is_illiquid"])]
    return out
