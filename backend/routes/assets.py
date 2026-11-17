# backend/routes/assets.py
import path_setup  # noqa
from utils.price_freshness import price_freshness
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
    # Database errors become a 503 (main.py); an empty collection is an empty list.
    from db.queries import get_supported_assets
    return [{"asset": r["asset_id"], "name": r["name"]} for r in get_supported_assets()]


# ── GET /assets/{symbol}/detail ─────────────────────────────────────────────

def _risk_level(safety: float) -> str:
    """Risk level words (riskLevelTone) from a D96 safety score, where higher = safer."""
    return "low" if safety >= 65 else "medium" if safety >= 35 else "high"


def risk_overview_rows(breakdown: dict | None) -> list[dict]:
    """
    The Risk Overview rows from a measured D96 breakdown: Volatility, Liquidity and Market risk, each with its
    safety score (higher = safer), raw value, source and as_of. A metric without a value is listed as not
    available (value null). Any other row (the seeded breakdown D94 removed) gives no rows.
    """
    from controllers.risk_breakdown_controller import METRICS, SOURCE
    if not breakdown or breakdown.get("source") != SOURCE:
        return []
    rows = []
    for key in METRICS:
        m = (breakdown.get("metrics") or {}).get(key) or {}
        score = m.get("score")
        rows.append({
            "key": key, "label": m.get("label") or METRICS[key][0],
            "value": score, "level": _risk_level(score) if score is not None else None,
            "status": m.get("status") or "not available", "why": m.get("why"),
            "raw": m.get("raw"), "raw_label": m.get("raw_label"),
            "source": m.get("source"), "as_of": m.get("as_of"), "ranked_among": m.get("ranked_among"),
            "direction": "higher = safer",
        })
    return rows


@router.get("/assets/{symbol}/detail")
def get_asset_detail(symbol: str, user_id: Optional[ObjectId] = Depends(get_optional_user_id)):
    """
    Everything the Asset Detail page renders, in one call. Every value comes
    from the database; a section with no backing row is null (or empty) rather
    than estimated:
      (no forecast: no price model is approved, ml/docs/DECISIONS.md D35; the chart draws a volatility cone, D52)
      aai_panel      -> null when `aai_scores` has no row
      about           -> description / website / ATH; fields are null where the asset row has none
      related/similar -> see controllers/asset_detail_controller.py (each item carries a `reason`)
      risk_overview   -> [] when no measured `risk_breakdown` row is stored (D96); risk_covered false for DAI / BASE
    """
    from datetime import date
    from controllers.market_controller import (
        aai_rating, aai_signal, build_crypto_items, live_sentiment_by_symbol, sentiment_confidence_label, stored_sentiment,
    )
    from db.queries import (
        get_asset, get_asset_market_data_latest, get_daily_price_series,
        get_latest_aai_score, get_latest_prediction, get_latest_risk_breakdown,
        get_price_sparklines, get_user_flags,
    )
    from controllers.asset_detail_controller import related_and_similar
    from db.mongo_connection import get_db
    from utils.ml_rows import with_stale_note

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
            from controllers.portfolio_controller import _num
            quantity_held = sum(_num(r.get("quantity")) or 0 for r in rows)

        universe = build_crypto_items(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise db_unavailable(exc)

    aai_panel = None
    sentiment = None
    if aai:
        score = aai.get("aai_score")
        aai_panel = {
            "score": score,
            "signal": aai_signal(score),
            "rating": aai_rating(score),
            "confidence": aai.get("confidence"),
            "pred_score": aai.get("pred_score"),
            "sentiment_score": aai.get("sentiment_score"),
            "risk_score": aai.get("risk_score"),
            "model_version": aai.get("model_version"),
            "note": aai.get("note"),
            "stale_inputs": aai.get("stale_inputs") or [],     # G-20: score is null and the card says "inputs stale"
            "as_of": aai.get("as_of"),
        }

    # Sentiment: the engine's live reading when it has one, else the reading (-1..1) aai_scores stored. Never the
    # row's 0-100 AAI component, which is on another scale (audit G-12).
    reading = live_sentiment_by_symbol().get(symbol) or stored_sentiment(aai)
    if reading:
        sentiment = {
            "score": reading["score"], "confidence": reading["confidence"],
            "confidence_label": sentiment_confidence_label(reading["confidence"]),
            "trend": reading.get("trend"),
        }

    from db.queries import ML_COVERED_ASSETS
    risk_covered = symbol in ML_COVERED_ASSETS          # DAI, BASE: "Not covered" (D94, D96)
    risk_overview = risk_overview_rows(breakdown) if risk_covered else []

    related, similar = related_and_similar(asset, universe)
    try:
        sparks = get_price_sparklines([x["id"] for x in related + similar])
        for x in related + similar:
            x["sparkline"] = sparks.get(x["id"], [])
    except Exception:
        pass   # sparklines are decoration; the lists still render without them

    return {
        "symbol": symbol,
        "header": {
            "symbol": asset["symbol"], "name": asset["name"],
            "category": asset.get("category"), "subcategory": asset.get("subcategory"),
            "logo_color": asset.get("logo_color"),
            "price": market.get("price"), "change_24h": market.get("change_24h"),
            **price_freshness(market),       # price_as_of, price_delayed (audit N-05)
            "held": symbol in flags["held"], "quantity_held": quantity_held,
            "watching": symbol in flags["watching"],
        },
        "price_history": history,
        # The ML service's own signal and note (null when no prediction is stored). While ml_signal is
        # UNCERTAIN the frontend must not present the AAI-derived BUY/HOLD/SELL as the model's call.
        "ml_signal": (prediction or {}).get("signal"),
        "ml_note": with_stale_note((prediction or {}).get("note"), (prediction or {}).get("timestamp"))
        if prediction else None,
        "aai_panel": aai_panel,
        "risk_overview": risk_overview,
        "risk_covered": risk_covered,
        "market_stats": {
            "market_rank": market.get("market_rank"),
            "market_cap": market.get("market_cap"),
            "volume_24h": market.get("volume_24h"),
            "circulating_supply": market.get("circulating_supply"),
            "all_time_high": asset.get("all_time_high"),
        },
        "sentiment": sentiment,
        "about": {
            "description": asset.get("description"),
            "website": asset.get("website"),
            "all_time_high": asset.get("all_time_high"),
            "ath_date": asset.get("ath_date"),
            "category": asset.get("category"),
            "subcategory": asset.get("subcategory"),
            "source": asset.get("profile_source"),
        },
        "related": related,
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
        **price_freshness(market),
        change_24h=market.get("change_24h"),
        market_cap=market.get("market_cap"),
        market_rank=market.get("market_rank"),
    )


# ── GET /assets/{symbol}/performance ────────────────────────────────────────

@router.get("/assets/{symbol}/performance")
def get_asset_performance(
    symbol: str,
    # Price only: the "AI Prediction" mode drew stored predicted prices as a line, and only seeded rows ever had
    # one (no price model is approved, ml/docs/DECISIONS.md D35; removed with D94).
    mode: str = Query("Price", pattern="^Price$"),
    filter: str = Query("1M", pattern="^(1D|1W|1M|3M|1Y)$"),
):
    from db.queries import get_price_history

    symbol = symbol.upper()
    days_map = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}
    days = days_map[filter]

    try:
        # `prices` is hourly; cap the row count so 1Y doesn't pull 400 days of hourly data.
        n_rows = min(days * 24, 24 * 400)
        history = get_price_history(symbol, days=n_rows)
        points = [{"timestamp": h["timestamp"], "value": h["price"]} for h in reversed(history)]
    except Exception as exc:
        raise db_unavailable(exc)

    return {"asset": symbol, "mode": mode, "filter": filter, "points": points}


# ── GET /assets/{symbol}/intelligence ───────────────────────────────────────

@router.get("/assets/{symbol}/intelligence", response_model=AAIResponse)
def get_asset_intelligence(symbol: str):
    from db.queries import get_asset, get_latest_aai_score, upsert_aai_score_generalized
    from controllers.aai_controller import compute_aai_response, is_complete

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
            "aai_score": cached.get("aai_score"),
            "pred_score": cached.get("pred_score"),
            "expected_return_30d": cached.get("expected_return_30d"),
            "sentiment_score": cached.get("sentiment_score"),
            "sentiment_confidence": cached.get("sentiment_confidence"),
            "risk_score": cached.get("risk_score"),
            "missing_inputs": cached.get("missing_inputs") or [],
            "stale_inputs": cached.get("stale_inputs") or [],      # G-20
            "inputs_as_of": cached.get("inputs_as_of") or {},
            "as_of": cached.get("as_of"),
            "note": cached.get("note"),
            "model_version": cached.get("model_version"),
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(ts, "strftime") else ts,
        }

    result = compute_aai_response(symbol)
    if not is_complete(result):
        # Missing a prediction or risk score, or built with a neutral stand-in for sentiment:
        # serve it, but never store it in aai_scores, where it would look like a real score.
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
    """The latest measured breakdown (D96): 404 for an asset the ML service doesn't cover, or with no measured row."""
    from controllers.risk_breakdown_controller import SOURCE
    from db.queries import ML_COVERED_ASSETS, get_latest_risk_breakdown
    from utils.serialization import serialize_dates

    symbol = symbol.upper()
    if symbol not in ML_COVERED_ASSETS:
        raise HTTPException(status_code=404, detail=f"{symbol} is not covered by the risk breakdown.")
    try:
        breakdown = get_latest_risk_breakdown(symbol)
    except Exception as exc:
        raise db_unavailable(exc)

    if not breakdown or breakdown.get("source") != SOURCE:
        raise HTTPException(status_code=404, detail=f"No risk breakdown found for '{symbol}'.")
    return serialize_dates(breakdown)


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