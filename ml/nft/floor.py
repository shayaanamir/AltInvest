"""Daily floor series (D55). Pure functions, no I/O.

floor_eth(D) = the OpenSea floor point with the latest time <= D 00:00:00 UTC, if that point is at most
NFT_FLOOR_MAX_AGE_HOURS old; otherwise null (the day is a gap). The same rule serves backfill and live.
floor_eth_asof(D) = the same as-of value with no age limit (D63), so every day has a value.
floor_eth_model(D) = floor_eth_asof with one-day spikes held back (D66): the modelling series for volatility,
the wash-filter price rule and the fair-value premium. A value more than NFT_FLOOR_SPIKE_FACTOR away from the
last accepted floor is accepted only once two consecutive daily values agree with each other; until then the
last accepted floor is kept. Every value is a floor OpenSea reported; the rule looks at past days only.
floor_usd(D) = floor_eth(D) x ETH-USD at D 00:00 UTC (the open of Binance daily bar D).
Nothing here uses a point or a price from after D 00:00 UTC.
"""

import numpy as np
import pandas as pd

from ml import config

DAY = 86400
FLOOR_SOURCE = "opensea_floor"


def eth_at_midnight(bars: pd.DataFrame) -> pd.DataFrame:
    """ETH-USD at 00:00 UTC of each date: the open of that day's bar ('open'); for the day after the last
    closed bar, that bar's close ('prev_close'; the same instant, the bar of the running day is not closed)."""
    b = bars.sort_values("timestamp")
    dates = b["timestamp"].dt.strftime("%Y-%m-%d").tolist()
    nxt = (b["timestamp"].iloc[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": dates + [nxt],
                         "eth_usd": b["open"].astype(float).tolist() + [float(b["close"].iloc[-1])],
                         "eth_usd_source": ["open"] * len(b) + ["prev_close"]})


def guard_spikes(asof: np.ndarray, factor: float = config.NFT_FLOOR_SPIKE_FACTOR) -> tuple[np.ndarray, np.ndarray]:
    """(accepted floor per day, True where the day's own value was held back) (D66).

    Day D's value x is accepted if it is within [1/factor, factor] x the last accepted floor, or within that
    band of the previous day's raw value (the new level is confirmed by a second day). Otherwise the last
    accepted floor is carried. Uses days <= D only."""
    x = np.asarray(asof, dtype=float)
    out, held = x.copy(), np.zeros(len(x), dtype=bool)
    lo, hi = 1.0 / factor, factor
    for i in range(1, len(x)):
        if lo <= x[i] / out[i - 1] <= hi or lo <= x[i] / x[i - 1] <= hi:
            continue
        out[i], held[i] = out[i - 1], True
    return out, held


def daily_floor(points: pd.DataFrame, last_day: str) -> pd.DataFrame:
    """One row per UTC date from the day after the first point to `last_day`, for one collection.

    `points`: time (unix s), token_unit (ETH), usd_price. Columns: date, floor_eth, floor_eth_asof,
    floor_eth_model, floor_spike, floor_usd_source (OpenSea's own usd_price of the same point; consistency
    test only), floor_point_time, floor_age_hours, floor_source.
    """
    p = points.sort_values("time")
    t = p["time"].to_numpy(dtype=float)
    first = (int(t[0]) // DAY + 1) * DAY
    last = int(pd.Timestamp(last_day, tz="UTC").timestamp())
    midnights = np.arange(first, last + 1, DAY)
    idx = np.searchsorted(t, midnights, side="right") - 1          # latest point with time <= midnight
    age_h = (midnights - t[idx]) / 3600
    fresh = age_h <= config.NFT_FLOOR_MAX_AGE_HOURS
    eth = p["token_unit"].to_numpy(dtype=float)[idx]
    usd = pd.to_numeric(p["usd_price"], errors="coerce").to_numpy(dtype=float)[idx]
    model, held = guard_spikes(eth)
    return pd.DataFrame({
        "date": pd.to_datetime(midnights, unit="s", utc=True).strftime("%Y-%m-%d"),
        "floor_eth": np.where(fresh, eth, np.nan),
        "floor_eth_asof": eth,
        "floor_eth_model": model,
        "floor_spike": held,
        "floor_usd_source": np.where(fresh & (usd > 0), usd, np.nan),
        "floor_point_time": t[idx],
        "floor_age_hours": age_h,
        "floor_source": FLOOR_SOURCE,
    })


def add_usd(floor: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    """floor_usd = floor_eth x ETH-USD at 00:00 UTC of the same date (D55). Raises if a date has no ETH price."""
    out = floor.merge(eth, on="date", how="left")
    if out["eth_usd"].isna().any():
        missing = out.loc[out["eth_usd"].isna(), "date"]
        raise ValueError(f"no ETH-USD price for {len(missing)} floor date(s), first {missing.iloc[0]}")
    out["floor_usd"] = out["floor_eth"] * out["eth_usd"]
    return out


def gaps(floor: pd.DataFrame) -> list[str]:
    """Dates whose floor is null under D55 (no point within the age limit)."""
    return floor.loc[floor["floor_eth"].isna(), "date"].tolist()


def intraday_median(points: pd.DataFrame, day: str) -> tuple[float | None, int]:
    """Display only (D55): median of the points in [day - 1 00:00, day 00:00) UTC, and how many there were."""
    end = int(pd.Timestamp(day, tz="UTC").timestamp())
    t = points["time"].to_numpy(dtype=float)
    v = points["token_unit"].to_numpy(dtype=float)[(t >= end - DAY) & (t < end)]
    return (float(np.median(v)) if len(v) else None), len(v)
