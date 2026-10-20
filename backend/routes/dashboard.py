"""
routes/dashboard.py

DASH-01 — Dashboard stats, performance chart, insights feed, trending assets.
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.http_errors import db_unavailable
from controllers.market_controller import aai_signal
from controllers.portfolio_controller import get_valued_holdings

from auth.dependencies import get_current_user_id, get_optional_user_id
from models.schemas import DashboardStats, MarketInsightItem
from db.queries import (
    get_portfolio_holdings,
    get_portfolio_snapshots,
    get_all_latest_aai_scores,
    get_asset_market_data_all_latest,
    get_market_insights,
    get_nft_collections,
    get_nft_market_data_all_latest,
    get_price_sparklines,
    get_supported_assets,
    get_user_flags,
)
from db.mongo_connection import get_db

router = APIRouter(tags=["Dashboard"])

_FILTER_DAYS = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}


def _as_number(value):
    """A finite float, or None (missing, null, text, NaN)."""
    from controllers.portfolio_controller import _num
    return _num(value)


# ── GET /dashboard/stats ────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(user_id: ObjectId = Depends(get_current_user_id)):
    try:
        valued_holdings = get_valued_holdings(user_id)
        market_latest = get_asset_market_data_all_latest()
        nft_market = get_nft_market_data_all_latest()
        crypto_aai = get_all_latest_aai_scores("crypto")
        nft_aai = get_all_latest_aai_scores("nft")
    except Exception as exc:
        raise db_unavailable(exc)

    portfolio_value = sum(h.get("current_value_usd") or 0.0 for h in valued_holdings)
    unpriced_holdings = sum(1 for h in valued_holdings if h.get("valuation_status") != "ok")
    volume_24h = sum(m.get("volume_24h") or 0.0 for m in market_latest)

    # Sentiment engine output, restricted to usable readings: covered assets only, recent,
    # and real (no neutral no-articles placeholders or error rows, which would drag the
    # average toward zero).
    sentiment_scores, confidences = [], []
    try:
        from routes.sentiment import usable_sentiment_records
        for doc in usable_sentiment_records():
            sentiment_scores.append(doc["sentiment_score"])
            confidences.append(doc["confidence"])
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
        holdings_count=len(valued_holdings),
        assets_count=len(market_latest),
        collections_count=len(nft_market),
        crypto_score_count=len(crypto_aai),
        nft_score_count=len(nft_aai),
        market_mood_confidence=round(sum(confidences) / len(confidences) * 100, 1) if confidences else None,
        sentiment_asset_count=len(sentiment_scores),
        unpriced_holding_count=unpriced_holdings,
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

        # The last 24 hourly prices of every held asset in one aggregation (was one query per holding),
        # walking the (asset, timestamp) index.
        db = get_db()
        symbols = sorted({h["symbol"] for h in crypto_holdings if h.get("symbol")})
        recent = {
            g["_id"]: g["rows"]
            for g in db.prices.aggregate([
                {"$match": {"asset": {"$in": symbols}}},
                {"$sort": {"asset": 1, "timestamp": -1}},
                {"$group": {"_id": "$asset", "rows": {"$firstN": {"input": {"timestamp": "$timestamp", "price": "$price"}, "n": 24}}}},
            ])
        } if symbols else {}

        points_map: dict[str, float] = {}
        for h in crypto_holdings:
            for p in recent.get(h.get("symbol"), []):
                ts = p["timestamp"]
                key = ts.strftime("%Y-%m-%dT%H:00:00Z") if hasattr(ts, "strftime") else str(ts)
                price, quantity = _as_number(p.get("price")), _as_number(h.get("quantity"))
                if price is None or quantity is None:
                    continue  # an unreadable row is skipped rather than failing the whole chart
                points_map[key] = points_map.get(key, 0.0) + price * quantity

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
def get_dashboard_trending(
    limit: int = Query(6, ge=1, le=20),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    """
    Trending = moving unusually for that asset: its 24h move against its own typical daily move,
    plus its 24h volume against its own 7-day average (controllers/trending_controller.py).
    Each row says why it's there (`reasons`), with the latest AAI score and a 7-day sparkline.
    """
    from controllers.trending_controller import score_assets
    try:
        market_latest = get_asset_market_data_all_latest()
        assets = {a["asset_id"]: a for a in get_supported_assets()}
        aai_scores = get_all_latest_aai_scores("crypto")
        top = score_assets(market_latest)[:limit]
        sparks = get_price_sparklines([m["asset_id"] for m in top])
        watching = get_user_flags(user_id)["watching"]
    except Exception as exc:
        raise db_unavailable(exc)

    results = []
    for m in top:
        asset_id = m["asset_id"]
        asset = assets.get(asset_id) or {}
        aai = aai_scores.get(asset_id) or {}
        score = aai.get("aai_score")
        results.append({
            "asset_id": asset_id,
            "symbol": asset.get("symbol", asset_id),
            "name": asset.get("name", asset_id),
            "logo_color": asset.get("logo_color"),
            "price": m.get("price"),
            "change_24h": m.get("change_24h"),
            "aai_score": score,
            "signal": aai_signal(score),
            "sparkline": sparks.get(asset_id, []),
            "watching": asset_id in watching,
            "trend_score": m.get("trend_score"),
            "move_vs_usual": m.get("move_vs_usual"),
            "volume_vs_usual": m.get("volume_vs_usual"),
            "reasons": m.get("reasons", []),
        })
    return results


# ── GET /dashboard/trending-collections ──────────────────────────────────────

@router.get("/dashboard/trending-collections")
def get_dashboard_trending_collections(limit: int = Query(4, ge=1, le=20)):
    """
    Trending collections = biggest 24h floor moves, with 24h trading volume breaking ties.
    No per-collection floor history is stored, so unlike assets these can't be measured against
    their own normal range, and there is no sparkline.
    """
    try:
        market_latest = get_nft_market_data_all_latest()
        collections = {c["slug"]: c for c in get_nft_collections()}
        aai_scores = get_all_latest_aai_scores("nft")
    except Exception as exc:
        raise db_unavailable(exc)

    market_latest.sort(key=lambda m: (abs(m.get("change_24h") or 0.0), m.get("volume_24h_eth") or 0.0), reverse=True)
    results = []
    for m in market_latest[:limit]:
        slug = m["slug"]
        c = collections.get(slug) or {}
        aai = aai_scores.get(slug) or {}
        results.append({
            "slug": slug,
            "name": c.get("name", slug),
            "symbol": c.get("symbol"),
            "banner_color": c.get("banner_color"),
            "floor_eth": m.get("floor_eth"),
            "floor_usd": m.get("floor_usd"),
            "change_24h": m.get("change_24h"),
            "volume_24h_eth": m.get("volume_24h_eth"),
            "aai_score": aai.get("aai_score"),
        })
    return results
