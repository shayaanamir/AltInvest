"""
backend/controllers/asset_detail_controller.py

The parts of GET /assets/{symbol}/detail that are worked out rather than read straight from a row:
related and similar assets, and the forecast with its band and past runs.

  related  - assets the database lists as related (assets.related_assets); if none are listed,
             the other assets in the same subcategory. Each says why it's there.
  similar  - the assets whose profile is closest: AAI score, risk score, volatility index and
             market-cap size (log scale), each scaled 0-1 across the universe; distance is the
             mean absolute gap over the features both assets have. Related assets are left out so
             the two lists don't repeat. Only assets at least MIN_SIMILARITY alike are shown, and
             each says which features are closest.
  forecast - the latest model run's 30-day target with its lower/upper band, plus earlier runs and,
             for runs whose target date has passed, the actual price that day and the error.
"""
import math
from datetime import datetime, timedelta, date

MIN_SIMILARITY = 0.5   # 1 = identical profile; below this an asset isn't shown as "similar"

_FEATURES = [
    ("aai_score", "AAI score"),
    ("risk_score", "risk score"),
    ("volatility", "volatility"),
    ("log_cap", "market size"),
]


def _scaled(universe: list[dict]) -> dict:
    """{id: {feature: 0..1}} using min-max over the universe; missing values stay missing."""
    rows = {}
    for i in universe:
        cap = i.get("market_cap")
        rows[i["id"]] = {
            "aai_score": i.get("aai_score"),
            "risk_score": i.get("risk_score"),
            "volatility": i.get("volatility"),
            "log_cap": math.log10(cap) if cap and cap > 0 else None,
        }
    out = {k: {} for k in rows}
    for f, _ in _FEATURES:
        vals = [r[f] for r in rows.values() if r[f] is not None]
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        for k, r in rows.items():
            if r[f] is not None:
                out[k][f] = 0.5 if hi == lo else (r[f] - lo) / (hi - lo)
    return out


def related_and_similar(asset: dict, universe: list[dict], limit: int = 4) -> tuple[list, list]:
    symbol = asset["asset_id"]
    by_id = {i["id"]: i for i in universe}

    curated = [r.upper() for r in (asset.get("related_assets") or []) if r and r.upper() in by_id and r.upper() != symbol]
    if curated:
        related = [{**by_id[r], "reason": "Listed as related"} for r in curated]
    else:
        sub = asset.get("subcategory")
        peers = [i for i in universe if sub and i.get("subcategory") == sub and i["id"] != symbol]
        peers.sort(key=lambda i: i.get("market_cap") or 0, reverse=True)
        related = [{**p, "reason": f"Also {sub}"} for p in peers]
    related = related[:limit]

    scaled = _scaled(universe)
    me = scaled.get(symbol, {})
    taken = {symbol, *(r["id"] for r in related)}
    scored = []
    for other in universe:
        if other["id"] in taken:
            continue
        theirs = scaled.get(other["id"], {})
        shared = [f for f, _ in _FEATURES if f in me and f in theirs]
        if len(shared) < 2:
            continue   # not enough in common to call it similar
        gaps = {f: abs(me[f] - theirs[f]) for f in shared}
        closest = sorted(gaps, key=gaps.get)[:2]
        labels = dict(_FEATURES)
        scored.append((sum(gaps.values()) / len(gaps), {
            **other,
            "similarity": round(1 - sum(gaps.values()) / len(gaps), 2),
            "reason": "Similar " + " and ".join(labels[f] for f in closest),
        }))
    scored = [t for t in scored if t[1]["similarity"] >= MIN_SIMILARITY]
    scored.sort(key=lambda t: t[0])
    return related, [s for _, s in scored[:limit]]


def _price_on(history_by_day: dict, day: str):
    return history_by_day.get(day)


def build_forecast(prediction: dict | None, runs: list[dict], history: list[dict]) -> dict | None:
    if not prediction or prediction.get("predicted_price") is None or not history:
        return None
    last = history[-1]
    target_day = (datetime.strptime(last["date"], "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")
    by_day = {h["date"]: h["price"] for h in history}
    today = date.today().isoformat()

    past = []
    for r in runs:
        ts = r.get("timestamp")
        made = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else (str(ts)[:10] if ts else None)
        if not made or r.get("predicted_price") is None:
            continue
        due = (datetime.strptime(made, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")
        actual = _price_on(by_day, due) if due <= today else None
        past.append({
            "made_on": made,
            "target_date": due,
            "predicted_price": r["predicted_price"],
            "lower_bound": r.get("lower_bound"),
            "upper_bound": r.get("upper_bound"),
            "actual_price": actual,
            "error_pct": round((r["predicted_price"] - actual) / actual * 100, 2) if actual else None,
            "model_version": r.get("model_version"),
        })
    scored = [p for p in past if p["error_pct"] is not None]

    return {
        # The model gives one 30-day target per run, not a path; the chart draws a straight
        # branch from today's price to it, with the band at the target.
        "points": [
            {"date": last["date"], "price": last["price"]},
            {"date": target_day, "price": prediction["predicted_price"]},
        ],
        "lower_bound": prediction.get("lower_bound"),
        "upper_bound": prediction.get("upper_bound"),
        "change_30d_pct": prediction.get("prediction_30d"),
        "confidence": prediction.get("confidence"),
        "trend": prediction.get("trend"),
        "model_version": prediction.get("model_version"),
        "runs": past,
        "mean_abs_error_pct": round(sum(abs(p["error_pct"]) for p in scored) / len(scored), 2) if scored else None,
    }
