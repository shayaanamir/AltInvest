"""
backend/controllers/asset_detail_controller.py

The parts of GET /assets/{symbol}/detail that are worked out rather than read straight from a row:
related and similar assets.

  related  - assets the database lists as related (assets.related_assets); if none are listed,
             the other assets in the same subcategory. Each says why it's there.
  similar  - the assets whose profile is closest: AAI score, risk score, volatility index and
             market-cap size (log scale), each scaled 0-1 across the universe; distance is the
             mean absolute gap over the features both assets have. Related assets are left out so
             the two lists don't repeat. Only assets at least MIN_SIMILARITY alike are shown, and
             each says which features are closest.
  No forecast is built: no price model is approved (ml/docs/DECISIONS.md D35), and the old builder only
  ever drew the seeded predictions as a line (removed with D94).
"""
import math

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
        # related_assets / related_basis come from shared CoinGecko tags (controllers/asset_profile_controller.py)
        basis = asset.get("related_basis") or {}
        related = [{**by_id[r], "reason": f"Both tagged “{basis[r][0]}” on CoinGecko" if basis.get(r) else "Listed as related"}
                   for r in curated]
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
