"""
routes/dashboard.py

DASH-01 — Dashboard stats, performance chart, insights feed, trending assets.
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from controllers.portfolio_controller import get_valued_holdings

from auth.dependencies import get_current_user_id
from models.schemas import DashboardStats, MarketInsightItem
from db.queries import (
    get_portfolio_holdings,
    get_portfolio_snapshots,
    get_asset_market_data_all_latest,
    get_nft_market_data_latest,
    get_market_insights,
    get_asset,
    get_latest_aai_score,
)
from db.mongo_connection import get_db

router = APIRouter(tags=["Dashboard"])

_FILTER_DAYS = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}


# ── GET /dashboard/stats ────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(user_id: ObjectId = Depends(get_current_user_id)):
    valued_holdings = get_valued_holdings(user_id)
    portfolio_value = sum(h["current_value_usd"] for h in valued_holdings)

    market_latest = get_asset_market_data_all_latest()
    volume_24h = sum(m.get("volume_24h", 0.0) for m in market_latest)

    sentiment_scores = []
    try:
        try:
            from sentiment_engine.storage.mongo_handler import get_all_latest
        except ImportError:
            from storage.mongo_handler import get_all_latest
        for doc in get_all_latest():
            score = doc.get("sentiment_score")
            if score is not None:
                sentiment_scores.append(score)
    except Exception as exc:
        print(f"[dashboard] sentiment engine unavailable ({exc})")

    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    if avg_sentiment > 0.15:
        label = "Bullish"
    elif avg_sentiment < -0.15:
        label = "Bearish"
    else:
        label = "Neutral"

    return DashboardStats(
        portfolio_value_usd=round(portfolio_value, 2),
        volume_24h_usd=round(volume_24h, 2),
        global_sentiment=round(avg_sentiment, 3),
        global_sentiment_label=label,
    )


# ── GET /dashboard/performance ──────────────────────────────────────────────

@router.get("/dashboard/performance")
def get_dashboard_performance(
    filter: str = Query("1M", pattern="^(1D|1W|1M|3M|1Y)$"),
    user_id: ObjectId = Depends(get_current_user_id),
):
    """
    1D: computed live from hourly `prices` against current crypto holdings
        (no snapshot granularity exists intraday, per the schema notes).
    1W/1M/3M/1Y: read from `portfolio_snapshots`.
    """
    if filter == "1D":
        holdings = get_portfolio_holdings(user_id)
        crypto_holdings = [h for h in holdings if h.get("asset_type") == "crypto"]

        db = get_db()
        points_map: dict[str, float] = {}
        for h in crypto_holdings:
            cursor = db.prices.find(
                {"asset": h["symbol"]},
                sort=[("timestamp", -1)],
                limit=24,
                projection={"_id": 0},
            )
            for p in cursor:
                ts = p["timestamp"]
                key = ts.strftime("%Y-%m-%dT%H:00:00Z") if hasattr(ts, "strftime") else str(ts)
                points_map[key] = points_map.get(key, 0.0) + p["price"] * h["quantity"]

        points = [{"timestamp": ts, "value": round(v, 2)} for ts, v in sorted(points_map.items())]
        return {"filter": filter, "points": points}

    days = _FILTER_DAYS[filter]
    snapshots = get_portfolio_snapshots(user_id, days=days)
    points = [
        {"timestamp": s["snapshot_date"], "value": s["total_value_usd"]}
        for s in reversed(snapshots)
    ]
    return {"filter": filter, "points": points}


# ── GET /dashboard/insights ─────────────────────────────────────────────────

@router.get("/dashboard/insights", response_model=list[MarketInsightItem])
def get_dashboard_insights(limit: int = Query(6, ge=1, le=20)):
    return get_market_insights(limit=limit)


# ── GET /dashboard/trending ──────────────────────────────────────────────────

@router.get("/dashboard/trending")
def get_dashboard_trending(limit: int = Query(6, ge=1, le=20)):
    """
    Trending = biggest absolute 24h movers. `is_trending` from the sentiment
    engine's market_signals could be folded in later; for now this only
    needs asset_market_data, which is always populated.
    """
    market_latest = get_asset_market_data_all_latest()
    market_latest.sort(key=lambda m: abs(m.get("change_24h", 0.0)), reverse=True)
    top = market_latest[:limit]

    results = []
    for m in top:
        asset = get_asset(m["asset_id"]) or {}
        aai = get_latest_aai_score("crypto", m["asset_id"])
        results.append({
            "asset_id": m["asset_id"],
            "symbol": asset.get("symbol", m["asset_id"]),
            "name": asset.get("name", m["asset_id"]),
            "logo_color": asset.get("logo_color"),
            "price": m.get("price"),
            "change_24h": m.get("change_24h"),
            "aai_score": aai.get("aai_score") if aai else None,
        })
    return results