"""Past ranges (Phase 11, D87): for each past day d, the illustrative 30-day cone (D52) as it would have been drawn
on day t0 = d - PAST_RANGE_LAG_DAYS. Pure: no FastAPI, no models, no artifacts, no labels.

- centre: the close of bar t0 (the ML's own daily close, the data the served volatility is computed from);
- volatility: the served volatility as known at t0 (config.RISK_VOL_COLUMN, persistence vol_30d since D82),
  annualised and rounded exactly as /risk serves it (responses.risk). vol_30d at t0 uses closes <= t0 only, so
  every band value depends on data up to t0 only (tested against data cut at t0, ml/tests/test_past_ranges.py);
- bands: the cone formula of frontend/src/utils/volCone.js coneBand at d = LAG days:
  centre x exp(-/+ z x (volatility / sqrt(365)) x sqrt(LAG)), z = CONE_Z_INNER (50%) and CONE_Z_OUTER (80%).
- close: the close of bar d, the outcome the band is compared with (calibration line, D88).
No direction, no drift and no new model: descriptive only, "not a price prediction".
"""

import math
from collections.abc import Iterable, Mapping
from datetime import datetime

import pandas as pd

from ml import config
from ml.serving import responses as rs

LAG = pd.Timedelta(days=config.PAST_RANGE_LAG_DAYS)
NOTE = (f"Each day's range is the illustrative {config.PAST_RANGE_LAG_DAYS}-day volatility range drawn "
        f"{config.PAST_RANGE_LAG_DAYS} days earlier: centred on that day's close, width from the 30-day volatility "
        f"served then (persistence, D82). Not a price prediction (D87).")


def served_volatility(daily_vol: float) -> float:
    """The annualised volatility /risk serves for a daily vol (responses.risk: vol x sqrt(365), 6 decimals)."""
    return round(daily_vol * math.sqrt(config.ANNUALISATION_DAYS), 6)


def band(centre: float, annual_vol: float, z: float, days: int = config.PAST_RANGE_LAG_DAYS) -> tuple[float, float]:
    """volCone.js coneBand(centre, dailyVol(annual), days, z): centre x exp(-/+ z x sd x sqrt(days))."""
    k = z * (annual_vol / math.sqrt(config.ANNUALISATION_DAYS)) * math.sqrt(days)
    return centre * math.exp(-k), centre * math.exp(k)


def range_made_on(centre: float, daily_vol: float) -> dict | None:
    """The cone's 30-day ranges from a close and the served daily vol of one day; None if either is unusable."""
    if not (isinstance(daily_vol, float) and math.isfinite(daily_vol) and daily_vol > 0 and centre > 0):
        return None
    vol = served_volatility(daily_vol)
    if vol <= 0:
        return None
    il, iu = band(centre, vol, config.CONE_Z_INNER)
    ol, ou = band(centre, vol, config.CONE_Z_OUTER)
    return {"centre": centre, "volatility": vol, "inner_lower": il, "inner_upper": iu,
            "outer_lower": ol, "outer_upper": ou}


def series(raw: pd.DataFrame, feats: pd.DataFrame | None = None) -> list[dict]:
    """Past-range points, oldest first, for every bar d whose t0 = d - LAG has a served vol.

    `feats` is responses.serving_table(raw) (built here if not given); `raw` gives the closes."""
    feats = rs.serving_table(raw) if feats is None else feats
    close = raw.sort_values("timestamp").set_index("timestamp")["close"]
    vol = feats[config.RISK_VOL_COLUMN]
    out = []
    for d in close.index:
        t0 = d - LAG
        if t0 not in vol.index:
            continue
        r = range_made_on(float(close.loc[t0]), float(vol.loc[t0]))
        if r is None:
            continue
        out.append({"date": d.strftime("%Y-%m-%d"), "made_on": t0.strftime("%Y-%m-%d"), **r,
                    "close": float(close.loc[d])})
    return out


def coverage(points: Iterable[Mapping]) -> dict:
    """Share of points whose close lies inside the 50% and 80% bands (bounds inclusive). Descriptive (D88)."""
    pts = list(points)
    n = len(pts)
    in50 = sum(p["inner_lower"] <= p["close"] <= p["inner_upper"] for p in pts)
    in80 = sum(p["outer_lower"] <= p["close"] <= p["outer_upper"] for p in pts)
    return {"days": n, "inside_50": in50, "inside_80": in80,
            "share_50": in50 / n if n else None, "share_80": in80 / n if n else None}


def response(asset: str, now: datetime, days: int | None = None) -> dict:
    """PastRangesResponse body (docs/CONTRACT_PAST_RANGES.md). `days`: only the last `days` points (None = all).
    Uses the serving gate (D40): data that fails it raises NotServable."""
    raw = rs.servable_raw(asset)
    try:
        feats = rs.serving_table(raw)
    except ValueError as e:
        raise rs.NotServable(f"{asset}: bars cannot be served ({e})") from None
    pts = series(raw, feats)
    if days is not None:
        pts = pts[-days:] if days > 0 else []
    return {
        "asset": asset.upper(),
        "timestamp": rs.iso_utc(now),
        "lag_days": config.PAST_RANGE_LAG_DAYS,
        "volatility_measure": config.RISK_VOL_COLUMN,
        "note": NOTE,
        "points": pts,
    }
