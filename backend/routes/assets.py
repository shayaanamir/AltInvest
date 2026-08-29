# backend/routes/assets.py
import path_setup  # noqa
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query
from models.schemas import AssetItem, AssetHeader, AAIResponse
from typing import List

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


# ── GET /assets/{symbol}/header ─────────────────────────────────────────────

@router.get("/assets/{symbol}/header", response_model=AssetHeader)
def get_asset_header(symbol: str):
    from db.queries import get_asset, get_asset_market_data_latest

    symbol = symbol.upper()
    try:
        asset = get_asset(symbol)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if not market:
        raise HTTPException(status_code=404, detail=f"No market data found for '{symbol}'.")
    return market