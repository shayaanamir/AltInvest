"""Derived NFT tables from the collected base tables. The ONE place they are built, for the frozen snapshot
(ml.nft.snapshot) and for serving (ml.serving.nft_responses), so both use the same definitions.

Base tables in a directory: floor_points, eth_1d.csv (Binance bars), sales_raw, traits, tokens.
Derived: eth_usd (ETH-USD at 00:00 UTC per date), floor (one row per collection and date: D55 floor in ETH
and USD, that date's wash-filtered sales, and the D58 liquidity as of that date 00:00 UTC), sales_marked
(every sale with its floor and wash_rule) and tokens with rarity.
"""

from pathlib import Path

import pandas as pd

from ml import config
from ml.data.loader import load_raw
from ml.nft import floor as fl, liquidity as lq, sales as sl, store, traits as tr


def eth_usd(directory: Path) -> pd.DataFrame:
    return fl.eth_at_midnight(load_raw("eth", raw_dir=directory))


def last_floor_day(points: pd.DataFrame, eth: pd.DataFrame) -> str:
    """The latest date D with a floor point at or before D 00:00 UTC and an ETH-USD price at D 00:00."""
    newest = pd.Timestamp(float(points["time"].max()), unit="s", tz="UTC").strftime("%Y-%m-%d")
    return min(newest, eth["date"].iloc[-1])


def floor_table(points: pd.DataFrame, eth: pd.DataFrame, last_day: str) -> pd.DataFrame:
    parts = [fl.add_usd(fl.daily_floor(p, last_day), eth).assign(slug=slug)
             for slug, p in points.groupby("slug", sort=True)]
    return pd.concat(parts, ignore_index=True)


def mark_sales(sales_raw: pd.DataFrame, floor: pd.DataFrame, last_day: str) -> pd.DataFrame:
    """Sales up to the end of `last_day` with floor_eth_asof and wash_rule. Later sales have no floor yet."""
    s = sales_raw[sales_raw["date"] <= last_day]
    return sl.wash_filter(sl.dedupe(s), floor)


def add_liquidity(floor: pd.DataFrame, marked: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    kept = marked[marked["wash_rule"] == ""]
    complete = lq.first_complete_dates(config.NFT_SALES_START)
    parts = []
    for slug, f in floor.groupby("slug", sort=True):
        act = lq.daily_activity(kept[kept["slug"] == slug], f["date"].tolist(), eth)
        parts.append(f.merge(act, on="date").merge(lq.windows(act, complete), on="date"))
    return lq.add_scores(pd.concat(parts, ignore_index=True))


def build(directory: Path, last_day: str | None = None, with_items: bool = True) -> dict[str, pd.DataFrame]:
    """Every derived table of `directory`. `last_day` defaults to the latest date the data covers."""
    d = Path(directory)
    points = store.read_table(d, "floor_points")
    eth = eth_usd(d)
    last_day = last_day or last_floor_day(points, eth)
    floor = floor_table(points, eth, last_day)
    if (d / "floor_intraday.csv").exists():                     # display only (D55); collected live, never backfilled
        intraday = store.read_csv(d / "floor_intraday.csv")[["slug", "date", "floor_intraday_median_eth"]]
        floor = floor.merge(intraday, on=["slug", "date"], how="left")
    else:
        floor["floor_intraday_median_eth"] = float("nan")
    out = {"eth_usd": eth[eth["date"] <= last_day].reset_index(drop=True), "floor_points": points}
    if store.has_table(d, "sales_raw"):
        marked = mark_sales(store.read_table(d, "sales_raw"), floor, last_day)
        out["sales_marked"] = marked
        floor = add_liquidity(floor, marked, eth)
    out["floor"] = floor
    if with_items and store.has_table(d, "tokens"):
        tokens, traits = store.read_table(d, "tokens"), store.read_table(d, "traits")
        out["traits"] = traits
        out["tokens"] = tokens.merge(tr.rarity_all(tokens, traits), on=["slug", "token_id"])
    return out
