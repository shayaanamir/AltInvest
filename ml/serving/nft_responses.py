"""Response bodies for the NFT endpoints (Phase 10 step 10.4; D59, D61, D66, D67). No FastAPI, no models.

Reads the live/serving NFT directory (config.ML_NFT_DIR) through ml.nft.build, the same builder the frozen
snapshot used, so serving and evaluation share every definition. Served:
- floor: the D55 daily floor in ETH and USD (null on gap days), plus the display-only intraday median;
- risk: the served floor volatility, persistence vol_30d of the raw floor (D73: the 10.3 EWMA approval was
  withdrawn), from the same ml.nft.risk_data rows as the evaluation, x sqrt(365); risk_score = the D59 pooled
  percentile of today's value among the 7 NFT collections' history (a separate NFT pool);
- liquidity: the D58 rule-based fields as of the last floor date 00:00 UTC;
- sales: wash-filtered sales (D57).
Staleness (D38 applied to the floor): the note says 'data stale' when the last floor date's 00:00 UTC is more
than STALE_DATA_HOURS old. Tables are rebuilt only when a source file changes.
"""

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.serving_gate import NotServable
from ml.features.features import ewma_vol
from ml.nft import build, risk_data, store
from ml.serving.responses import iso_utc, pooled_risk_score

SOURCE_FILES = ("floor_points.csv", "sales_raw.csv", "eth_1d.csv", "floor_intraday.csv", "collections.json")
_CACHE: dict = {}


def _num(x, digits: int = 6):
    if x is None:
        return None
    x = float(x)
    return None if not math.isfinite(x) else round(x, digits)


def _signature() -> tuple:
    d = config.ML_NFT_DIR
    return (str(d),) + tuple((d / f).stat().st_mtime_ns if (d / f).exists() else None for f in SOURCE_FILES)


def served_vol(floor_one: pd.DataFrame) -> pd.Series:
    """The served daily volatility per date for one collection: exactly the evaluation's rows (risk_data) and
    EWMA function; NaN during the warm-up."""
    feats = risk_data.features(risk_data.floor_series(floor_one, config.NFT_MODEL_FLOOR_COLUMN))
    if config.NFT_RISK_VOL_COLUMN == "ewma_vol":
        vol = ewma_vol(feats["close"])
    else:
        vol = feats["vol_30d"]
    return pd.Series(vol.to_numpy(), index=feats.index.strftime("%Y-%m-%d"))


def tables() -> dict:
    """{floor, sales_marked, meta, vol: {slug: Series}}, cached on the source files' modification times."""
    sig = _signature()
    if _CACHE.get("sig") == sig:
        return _CACHE["tables"]
    d = config.ML_NFT_DIR
    if not (store.has_table(d, "floor_points") and (d / "eth_1d.csv").exists() and (d / "collections.json").exists()):
        raise NotServable(f"NFT data missing in {d}; run python -m ml.nft.refresh")
    built = build.build(d, with_items=False)
    floor = built["floor"]
    meta = json.loads((d / "collections.json").read_text(encoding="utf-8"))
    vols = {}
    for slug, g in floor.groupby("slug", sort=True):
        if len(g) >= config.NFT_MIN_CONE_DAYS:
            try:
                vols[slug] = served_vol(g)
            except ValueError:
                pass                                            # no volatility served for a broken series
    out = {"floor": floor, "sales_marked": built.get("sales_marked"), "meta": meta, "vol": vols}
    _CACHE.update(sig=sig, tables=out)
    return out


def _check_slug(slug: str) -> str:
    s = slug.lower()
    if s not in config.NFT_SLUGS:
        raise KeyError(f"collection '{slug}' is not covered; covered: {list(config.NFT_SLUGS)}")
    return s


def _own(t: dict, slug: str) -> pd.DataFrame:
    g = t["floor"][t["floor"]["slug"] == slug].sort_values("date")
    if g.empty:
        raise NotServable(f"{slug}: no floor data")
    return g


def age_hours(last_date: str, now: datetime) -> float:
    """Hours since 00:00 UTC of the last floor date (the time the D55 floor of that date describes)."""
    return (pd.Timestamp(now) - pd.Timestamp(last_date, tz="UTC")) / pd.Timedelta(hours=1)


def stale_note(last_date: str, now: datetime) -> str | None:
    return f"data stale: last floor {last_date}" if age_hours(last_date, now) > config.STALE_DATA_HOURS else None


def _pct_change(series: pd.Series, days: int) -> float | None:
    if len(series) <= days:
        return None
    return _num((series.iloc[-1] / series.iloc[-1 - days] - 1) * 100, 4)


def collections(now: datetime) -> dict:
    """NftCollectionsResponse: one row per covered collection with its latest floor."""
    t = tables()
    rows = []
    for slug in config.NFT_SLUGS:
        m = t["meta"].get(slug) or {}
        g = t["floor"][t["floor"]["slug"] == slug].sort_values("date")
        last = g.iloc[-1] if len(g) else None
        prev = g.iloc[-2] if len(g) > 1 else None
        rows.append({
            "slug": slug, "name": m.get("name") or slug, "symbol": m.get("symbol"),
            "contract": m.get("contract"), "total_supply": m.get("total_supply"),
            "image_url": m.get("image_url") or None, "verified": bool(m.get("verified")),
            "description": m.get("description") or None,
            "last_floor_date": None if last is None else last["date"],
            "floor_eth": None if last is None else _num(last["floor_eth"]),
            "floor_usd": None if last is None else _num(last["floor_usd"], 2),
            "change_24h": _pct_change(g["floor_eth_asof"], 1),
            "change_7d": _pct_change(g["floor_eth_asof"], 7),
            "volume_1d_eth": None if prev is None else _num(prev.get("volume_eth")),
            "sales_1d": None if prev is None or pd.isna(prev.get("sales_count")) else int(prev["sales_count"]),
        })
    return {"collections": rows, "marketplaces_counted": config.NFT_MARKETPLACES_LABEL, "timestamp": iso_utc(now)}


def floor(slug: str, now: datetime, days: int = 365) -> dict:
    """NftFloorResponse: the last `days` daily floor rows, oldest first."""
    slug = _check_slug(slug)
    g = _own(tables(), slug).tail(max(1, min(int(days), 2000)))
    rows = [{"date": r["date"], "floor_eth": _num(r["floor_eth"]), "floor_usd": _num(r["floor_usd"], 2),
             "eth_usd": _num(r["eth_usd"], 2), "floor_source": r["floor_source"],
             "floor_age_hours": _num(r["floor_age_hours"], 2),
             "floor_intraday_median_eth": _num(r.get("floor_intraday_median_eth"))} for _, r in g.iterrows()]
    return {"slug": slug, "rows": rows, "timestamp": iso_utc(now),
            "note": stale_note(g["date"].iloc[-1], now)}


def _wash_share_30d(t: dict, slug: str, last_date: str) -> float | None:
    s = t.get("sales_marked")
    if s is None:
        return None
    lo = (pd.Timestamp(last_date) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    w = s[(s["slug"] == slug) & (s["date"] >= lo) & (s["date"] < last_date)]
    return None if w.empty else _num((w["wash_rule"] != "").mean())


def liquidity(t: dict, slug: str, last: pd.Series) -> dict:
    def n(c):
        return None if pd.isna(last.get(c)) else _num(last[c])
    return {"sales_7d": n("sales_7d"), "sales_30d": n("sales_30d"), "volume_7d_eth": n("volume_7d_eth"),
            "volume_30d_eth": n("volume_30d_eth"), "liquidity_score": n("liquidity_score"),
            "label": last.get("liquidity_label") if isinstance(last.get("liquidity_label"), str) else None,
            "is_illiquid": None if pd.isna(last.get("sales_7d")) else bool(last["is_illiquid"]),
            "wash_removed_share_30d": _wash_share_30d(t, slug, last["date"]),
            "marketplaces_counted": config.NFT_MARKETPLACES_LABEL}


def risk_inputs(slug: str, now: datetime) -> dict:
    t = tables()
    g = _own(t, slug)
    last = g.iloc[-1]
    today = last["date"]
    vol = t["vol"].get(slug)
    v = None if vol is None or today not in vol.index or pd.isna(vol.loc[today]) else float(vol.loc[today])
    pool = np.concatenate([s[s.index <= today].dropna().to_numpy() for s in t["vol"].values()]) if t["vol"] else []
    score, p = pooled_risk_score(v, pool) if v is not None and len(pool) else (None, None)
    return {"last_floor_date": today, "daily_vol": v, "p": p, "risk_score": score, "pool_size": len(pool),
            "pool_collections": sorted(t["vol"]), "liquidity": liquidity(t, slug, last),
            "stale_note": stale_note(today, now), "age_hours": age_hours(today, now)}


def _risk_note(served: bool) -> str:
    if not served:
        return "No floor volatility: fewer than 60 days of floor history."
    relative = ("risk_score is relative to the other tracked NFT collections (higher = safer) and is not "
                "comparable to crypto risk scores.")
    if config.NFT_RISK_VOL_COLUMN == "ewma_vol":
        return (f"Risk model: EWMA floor volatility (lambda {config.EWMA_LAMBDA}) of the daily floor in ETH, approved "
                f"pooled over the tracked NFT collections in walk-forward (D59). {relative}")
    return ("Risk measure: 30-day volatility of the daily floor in ETH (persistence). No model is served: an earlier "
            f"model approval was withdrawn after a check against sale prices (D72, D73). {relative}")


def risk(slug: str, now: datetime) -> dict:
    """NftRiskResponse."""
    slug = _check_slug(slug)
    x = risk_inputs(slug, now)
    served = x["daily_vol"] is not None
    note = " ".join(p for p in (_risk_note(served), x["stale_note"]) if p)
    return {"slug": slug,
            "volatility": _num(x["daily_vol"] * math.sqrt(config.ANNUALISATION_DAYS)) if served else None,
            "risk_score": _num(x["risk_score"]) if served else None,
            "liquidity": x["liquidity"], "as_of": x["last_floor_date"],
            "model_version": config.MODEL_VERSION_NFT_RISK, "note": note, "timestamp": iso_utc(now)}


def sales(slug: str, now: datetime, days: int = 30) -> dict:
    """NftSalesResponse: wash-filtered sales in the last `days` days before the last floor date's end."""
    slug = _check_slug(slug)
    t = tables()
    g = _own(t, slug)
    s = t.get("sales_marked")
    rows = []
    if s is not None:
        eth = g.set_index("date")["eth_usd"]
        lo = (pd.Timestamp(g["date"].iloc[-1]) - pd.Timedelta(days=max(1, min(int(days), 90)))).strftime("%Y-%m-%d")
        w = s[(s["slug"] == slug) & (s["wash_rule"] == "") & (s["date"] >= lo)].sort_values("timestamp")
        for _, r in w.iterrows():
            rate = eth.get(r["date"])
            rows.append({"token_id": r["token_id"], "timestamp": iso_utc(datetime.fromtimestamp(int(r["timestamp"]),
                                                                                         tz=timezone.utc)),
                         "price_eth": _num(r["price_eth"]),
                         "price_usd": None if rate is None or pd.isna(rate) else _num(r["price_eth"] * rate, 2),
                         "marketplace": r["marketplace"], "buyer": r["buyer"], "seller": r["seller"], "tx": r["tx"]})
    return {"slug": slug, "rows": rows, "marketplaces_counted": config.NFT_MARKETPLACES_LABEL,
            "timestamp": iso_utc(now)}
