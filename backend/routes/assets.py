# backend/routes/assets.py
import path_setup  # noqa
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.http_errors import db_unavailable
from auth.dependencies import get_optional_user_id
from models.schemas import AssetItem, AssetHeader, AAIResponse
from typing import List, Optional

router = APIRouter(tags=["Assets"])

_AAI_CACHE_TTL_MINUTES = 60


@router.get("/assets", response_model=List[AssetItem])
def get_assets():
    try:
        from db.queries import get_supported_assets
        results = get_supported_assets()
        if results:
            return [{"asset": r["asset_id"], "name": r["name"]} for r in results]
    except Exception:
        pass
    # Fallback if MongoDB isn't up yet
    print("MongoDB not available, returning mock assets")
    return [{"asset": "BTC", "name": "Bitcoin"}, {"asset": "ETH", "name": "Ethereum"}]


# ── GET /assets/{symbol}/detail ─────────────────────────────────────────────

def _risk_level(value: float, higher_is_better: bool = False) -> str:
    """Level words understood by the frontend's riskLevelTone()."""
    if higher_is_better:  # liquidity
        return "excellent" if value >= 80 else "good" if value >= 60 else "fair" if value >= 40 else "high"
    return "low" if value < 35 else "medium" if value < 65 else "high"


@router.get("/assets/{symbol}/detail")
def get_asset_detail(symbol: str, user_id: Optional[ObjectId] = Depends(get_optional_user_id)):
    """
    Everything the Asset Detail page renders, in one call. Every value comes
    from the database; a section with no backing row is null (or empty) rather
    than estimated:
      forecast        -> null when `predictions` has no row for the asset
      aai_panel       -> null when `aai_scores` has no row
      risk_overview   -> [] when `risk_breakdown` has no row
    """
    from datetime import date
    from controllers.market_controller import (
        aai_signal, build_crypto_items, live_sentiment_by_symbol, sentiment_confidence_label,
    )
    from db.queries import (
        get_asset, get_asset_market_data_latest, get_daily_price_series,
        get_latest_aai_score, get_latest_prediction, get_latest_risk_breakdown,
        get_price_sparklines, get_user_flags,
    )
    from db.mongo_connection import get_db

    symbol = symbol.upper()
    try:
        asset = get_asset(symbol)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found.")

        market = get_asset_market_data_latest(symbol) or {}
        history = get_daily_price_series(symbol, 365)
        prediction = get_latest_prediction(symbol)
        aai = get_latest_aai_score("crypto", symbol)
        breakdown = get_latest_risk_breakdown(symbol)
        flags = get_user_flags(user_id)

        quantity_held = None
        if user_id is not None and symbol in flags["held"]:
            rows = get_db().portfolio_holdings.find(
                {"user_id": user_id, "symbol": symbol}, projection={"quantity": 1}
            )
            quantity_held = sum(r.get("quantity") or 0 for r in rows)

        universe = build_crypto_items(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise db_unavailable(exc)

    # Forecast: the single latest model run, drawn from the last known price to
    # its 30-day target. `predictions` holds one target per run, not a curve.
    forecast = None
    if prediction and prediction.get("predicted_price") is not None and history:
        from datetime import datetime, timedelta
        last = history[-1]
        target_day = (datetime.strptime(last["date"], "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")
        forecast = {
            "points": [
                {"date": last["date"], "price": last["price"]},
                {"date": target_day, "price": prediction["predicted_price"]},
            ],
            "lower_bound": prediction.get("lower_bound"),
            "upper_bound": prediction.get("upper_bound"),
            "change_30d_pct": prediction.get("prediction_30d"),
            "model_version": prediction.get("model_version"),
        }

    aai_panel = None
    sentiment = None
    if aai:
        score = aai.get("aai_score")
        aai_panel = {
            "score": score,
            "signal": aai_signal(score),
            "confidence": aai.get("confidence"),
            "pred_score": aai.get("pred_score"),
            "sentiment_score": aai.get("sentiment_score"),
            "risk_score": aai.get("risk_score"),
            "model_version": aai.get("model_version"),
        }

    # Sentiment: the engine's live reading when it has one, else what aai_scores stored.
    live = live_sentiment_by_symbol().get(symbol)
    if live:
        sentiment = {
            "score": live["score"], "confidence": live["confidence"],
            "confidence_label": sentiment_confidence_label(live["confidence"]),
            "trend": live["trend"],
        }
    elif aai and aai.get("sentiment_score") is not None:
        conf = aai.get("sentiment_confidence")
        sentiment = {
            "score": aai["sentiment_score"],
            "confidence": conf,
            "confidence_label": sentiment_confidence_label(conf),
            "trend": aai.get("sentiment_trend"),
        }

    risk_overview = []
    if breakdown:
        for label, key, better in [
            ("Volatility Index", "volatility_index", False),
            ("Liquidity Score", "liquidity_score", True),
            ("Regulatory Risk", "regulatory_risk", False),
            ("Market Risk", "market_risk", False),
        ]:
            if breakdown.get(key) is not None:
                risk_overview.append({
                    "label": label, "value": breakdown[key],
                    "level": _risk_level(breakdown[key], better),
                })

    # Similar assets: the asset's own related_assets first, topped up by market cap.
    by_id = {i["id"]: i for i in universe}
    related_ids = [r for r in (asset.get("related_assets") or []) if r in by_id and r != symbol]
    rest = sorted((i for i in universe if i["id"] != symbol and i["id"] not in related_ids),
                  key=lambda i: i.get("market_cap") or 0, reverse=True)
    similar = [by_id[r] for r in related_ids] + rest
    similar = similar[:4]
    try:
        sparks = get_price_sparklines([s["id"] for s in similar])
        for s in similar:
            s["sparkline"] = sparks.get(s["id"], [])
    except Exception:
        pass

    return {
        "symbol": symbol,
        "header": {
            "symbol": asset["symbol"], "name": asset["name"],
            "category": asset.get("category"), "subcategory": asset.get("subcategory"),
            "logo_color": asset.get("logo_color"),
            "price": market.get("price"), "change_24h": market.get("change_24h"),
            "held": symbol in flags["held"], "quantity_held": quantity_held,
            "watching": symbol in flags["watching"],
        },
        "price_history": history,
        "forecast": forecast,
        "aai_panel": aai_panel,
        "risk_overview": risk_overview,
        "market_stats": {
            "market_rank": market.get("market_rank"),
            "market_cap": market.get("market_cap"),
            "volume_24h": market.get("volume_24h"),
            "circulating_supply": market.get("circulating_supply"),
            "all_time_high": asset.get("all_time_high"),
        },
        "sentiment": sentiment,
        "about": asset.get("description"),
        "similar": similar,
    }


# ── GET /assets/{symbol}/header ─────────────────────────────────────────────

@router.get("/assets/{symbol}/header", response_model=AssetHeader)
def get_asset_header(symbol: str):
    from db.queries import get_asset, get_asset_market_data_latest

    symbol = symbol.upper()
    try:
        asset = get_asset(symbol)
    except Exception as exc:
        raise db_unavailable(exc)

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found.")

    market = get_asset_market_data_latest(symbol) or {}

    return AssetHeader(
        asset_id=asset["asset_id"],
        symbol=asset["symbol"],
        name=asset["name"],
        category=asset["category"],
        subcategory=asset.get("subcategory"),
        logo_color=asset.get("logo_color"),
        logo_url=asset.get("logo_url"),
        price=market.get("price"),
        change_24h=market.get("change_24h"),
        market_cap=market.get("market_cap"),
        market_rank=market.get("market_rank"),
    )


# ── GET /assets/{symbol}/performance ────────────────────────────────────────

@router.get("/assets/{symbol}/performance")
def get_asset_performance(
    symbol: str,
    mode: str = Query("Price", pattern="^(Price|AI Prediction)$"),
    filter: str = Query("1M", pattern="^(1D|1W|1M|3M|1Y)$"),
):
    from db.queries import get_price_history, get_prediction_history

    symbol = symbol.upper()
    days_map = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}
    days = days_map[filter]

    try:
        if mode == "Price":
            # `prices` is hourly; cap the row count so 1Y doesn't pull 400 days of hourly data.
            n_rows = min(days * 24, 24 * 400)
            history = get_price_history(symbol, days=n_rows)
            points = [{"timestamp": h["timestamp"], "value": h["price"]} for h in reversed(history)]
        else:
            history = get_prediction_history(symbol, days=days)
            points = [{"timestamp": h["timestamp"], "value": h["predicted_price"]} for h in reversed(history)]
    except Exception as exc:
        raise db_unavailable(exc)

    return {"asset": symbol, "mode": mode, "filter": filter, "points": points}


# ── GET /assets/{symbol}/intelligence ───────────────────────────────────────

@router.get("/assets/{symbol}/intelligence", response_model=AAIResponse)
def get_asset_intelligence(symbol: str):
    from db.queries import get_asset, get_latest_aai_score, upsert_aai_score_generalized
    from controllers.aai_controller import compute_aai_response

    symbol = symbol.upper()
    try:
        asset = get_asset(symbol)
    except Exception as exc:
        raise db_unavailable(exc)

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found.")

    cached = get_latest_aai_score("crypto", symbol)
    is_fresh = False
    if cached:
        ts = cached.get("timestamp")
        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            is_fresh = (datetime.now(timezone.utc) - ts) < timedelta(minutes=_AAI_CACHE_TTL_MINUTES)

    if cached and is_fresh:
        ts = cached["timestamp"]
        return {
            "asset": symbol,
            "aai_score": cached["aai_score"],
            "pred_score": cached["pred_score"],
            "sentiment_score": cached["sentiment_score"],
            "sentiment_confidence": cached.get("sentiment_confidence"),
            "risk_score": cached["risk_score"],
            "model_version": cached["model_version"],
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(ts, "strftime") else ts,
        }

    result = compute_aai_response(symbol)
    if result.get("sentiment_available") is False:
        # Built with a neutral stand-in for sentiment: serve it, but don't cache it, so the
        # next request tries for real sentiment again.
        return result
    try:
        upsert_aai_score_generalized(
            "crypto", symbol,
            {**result, "target_type": "crypto", "target_id": symbol,
             "timestamp": datetime.now(timezone.utc)},
        )
    except Exception as exc:
        print(f"[assets] failed to cache AAI score for {symbol}: {exc}")

    return result


# ── GET /assets/{symbol}/risk ────────────────────────────────────────────────

@router.get("/assets/{symbol}/risk")
def get_asset_risk_breakdown(symbol: str):
    from db.queries import get_latest_risk_breakdown

    symbol = symbol.upper()
    try:
        breakdown = get_latest_risk_breakdown(symbol)
    except Exception as exc:
        raise db_unavailable(exc)

    if not breakdown:
        raise HTTPException(status_code=404, detail=f"No risk breakdown found for '{symbol}'.")
    return breakdown


# ── GET /assets/{symbol}/market-stats ───────────────────────────────────────

@router.get("/assets/{symbol}/market-stats")
def get_asset_market_stats(symbol: str):
    from db.queries import get_asset_market_data_latest

    symbol = symbol.upper()
    try:
        market = get_asset_market_data_latest(symbol)
    except Exception as exc:
        raise db_unavailable(exc)

    if not market:
        raise HTTPException(status_code=404, detail=f"No market data found for '{symbol}'.")
    return market