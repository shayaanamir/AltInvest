"""
backend/controllers/trending_controller.py

"Trending" = moving unusually for that asset, not simply the biggest move. A 6% day is ordinary
for a meme coin and remarkable for Bitcoin, so each asset is measured against its own history
(the hourly `prices` rows):

  move score    |24h change| / the asset's typical daily move (std. dev. of its last 30 daily
                returns), capped at 5. 1 = an ordinary day, 3 = three times its usual swing.
  volume score  log2(last 24h volume / its average daily volume over the 7 days before), floored
                at 0, capped at 3. 1 = double its usual volume.
  trend score   move score + volume score (either part is left out when its history is missing)

Each item carries `reasons` saying what stood out, so the card can explain itself.
"""
import math
import statistics

from db.mongo_connection import get_db

HOURS_PER_DAY = 24
VOL_WINDOW_DAYS = 30
VOLUME_BASE_DAYS = 7


def _recent_rows(symbols: list[str]) -> dict:
    """{ASSET: [(price, volume), ...] newest first}: the last ~31 days of hourly rows, one aggregation."""
    if not symbols:
        return {}
    n = (VOL_WINDOW_DAYS + 1) * HOURS_PER_DAY
    out = {}
    for g in get_db().prices.aggregate([
        {"$match": {"asset": {"$in": symbols}}},
        {"$sort": {"asset": 1, "timestamp": -1}},
        {"$group": {"_id": "$asset", "rows": {"$firstN": {"input": {"p": "$price", "v": "$volume"}, "n": n}}}},
    ], allowDiskUse=True):
        out[g["_id"]] = [(r.get("p"), r.get("v")) for r in g["rows"]]
    return out


def _typical_daily_move_pct(rows) -> float | None:
    closes = [p for i, (p, _) in enumerate(rows) if i % HOURS_PER_DAY == 0 and isinstance(p, (int, float)) and p > 0]
    if len(closes) < 10:
        return None
    returns = [(closes[i] / closes[i + 1] - 1) * 100 for i in range(len(closes) - 1)]   # newest first
    sd = statistics.pstdev(returns)
    return sd if sd > 0 else None


def _volume_ratio(rows) -> float | None:
    vols = [v for _, v in rows]
    need = HOURS_PER_DAY * (1 + VOLUME_BASE_DAYS)
    if len(vols) < need or any(not isinstance(v, (int, float)) for v in vols[:need]):
        return None
    today = sum(vols[:HOURS_PER_DAY])
    base_days = [sum(vols[HOURS_PER_DAY * d: HOURS_PER_DAY * (d + 1)]) for d in range(1, 1 + VOLUME_BASE_DAYS)]
    base = sum(base_days) / len(base_days)
    return today / base if base > 0 else None


def score_assets(market_latest: list[dict]) -> list[dict]:
    """Each market row plus trend_score, move_vs_usual, volume_vs_usual and reasons; highest score first."""
    rows = _recent_rows([m["asset_id"] for m in market_latest])
    scored = []
    for m in market_latest:
        change = m.get("change_24h")
        r = rows.get(m["asset_id"], [])
        typical = _typical_daily_move_pct(r)
        vratio = _volume_ratio(r)

        move = min(abs(change) / typical, 5.0) if change is not None and typical else None
        vol = min(max(math.log2(vratio), 0.0), 3.0) if vratio else None
        parts = [x for x in (move, vol) if x is not None]
        score = sum(parts) if parts else None

        reasons = []
        if move is not None and move >= 1.5:
            reasons.append(f"{abs(change) / typical:.1f}× its usual daily move")
        if vratio is not None and vratio >= 1.5:
            reasons.append(f"volume {vratio:.1f}× its 7-day average")
        if not reasons and change is not None:
            reasons.append(f"{'up' if change >= 0 else 'down'} {abs(change):.1f}% in 24h")

        scored.append({
            **m,
            "trend_score": round(score, 2) if score is not None else None,
            "move_vs_usual": round(abs(change) / typical, 2) if move is not None else None,
            "volume_vs_usual": round(vratio, 2) if vratio is not None else None,
            "reasons": reasons,
        })
    # Assets with no history to judge by go last, ordered by the size of their move.
    scored.sort(key=lambda x: (x["trend_score"] is not None, x["trend_score"] or 0, abs(x.get("change_24h") or 0)), reverse=True)
    return scored
