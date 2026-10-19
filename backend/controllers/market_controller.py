"""
backend/controllers/market_controller.py

One place that joins the per-asset / per-collection collections into the flat
"universe" rows used by /discover, /compare and /dashboard/trending*.

Every field comes from the database. A field with no backing data is None —
nothing is estimated here.
"""
from db.queries import (
    get_all_latest_aai_scores,
    get_all_latest_nft_liquidity,
    get_all_latest_predictions,
    get_all_latest_risk_breakdowns,
    get_all_latest_risk_scores,
    get_asset_market_data_all_latest,
    get_nft_collections,
    get_nft_market_data_all_latest,
    get_price_sparklines,
    get_supported_assets,
    get_user_flags,
)


def aai_signal(score: float | None) -> str | None:
    """BUY / HOLD / SELL from a 0-100 AAI score (same cut-offs as the frontend's scoring.js)."""
    if score is None:
        return None
    if score >= 55:
        return "BUY"
    if score >= 45:
        return "HOLD"
    return "SELL"


def sentiment_confidence_label(conf: float | None) -> str | None:
    if conf is None:
        return None
    return "high" if conf >= 0.7 else "medium" if conf >= 0.4 else "low"


def live_sentiment_by_symbol() -> dict:
    """
    {SYMBOL: {score, confidence, trend}} from the sentiment engine's own collection,
    which its scheduler refreshes continuously. Neutral placeholders (confidence 0 —
    written when no articles were found) are skipped. Returns {} if the engine or its
    database is unavailable, so callers fall back to the stored aai_scores values.
    """
    try:
        try:
            from sentiment_engine.storage.mongo_handler import get_all_latest
        except ImportError:
            from storage.mongo_handler import get_all_latest
        docs = get_all_latest()
    except Exception as exc:
        print(f"[market_controller] live sentiment unavailable ({exc})")
        return {}

    out = {}
    for d in docs:
        asset_id, score, conf = d.get("asset_id"), d.get("sentiment_score"), d.get("confidence") or 0.0
        if asset_id and score is not None and conf > 0:
            out[asset_id.upper()] = {"score": score, "confidence": conf, "trend": d.get("trend")}
    return out


def _aai_fields(aai: dict | None, live: dict | None = None) -> dict:
    """AAI + sentiment fields. Live sentiment (when present) wins over the value stored in aai_scores."""
    aai = aai or {}
    score = aai.get("aai_score")
    live = live or {}
    sent_score = live.get("score", aai.get("sentiment_score"))
    conf = live.get("confidence", aai.get("sentiment_confidence"))
    return {
        "aai_score": score,
        "signal": aai_signal(score),
        "sentiment_score": sent_score,
        "sentiment_confidence": conf,
        "sentiment_confidence_label": sentiment_confidence_label(conf),
        "sentiment_trend": live.get("trend", aai.get("sentiment_trend")),
    }


def build_crypto_items(user_id=None, with_sparklines: bool = False) -> list[dict]:
    assets = {a["asset_id"]: a for a in get_supported_assets()}
    market = {m["asset_id"]: m for m in get_asset_market_data_all_latest()}
    aai_scores = get_all_latest_aai_scores("crypto")
    predictions = get_all_latest_predictions()
    risk_scores = get_all_latest_risk_scores()
    risk_breakdowns = get_all_latest_risk_breakdowns()
    flags = get_user_flags(user_id)
    sparks = get_price_sparklines(list(market)) if with_sparklines else {}
    live_sentiment = live_sentiment_by_symbol()

    items = []
    for asset_id, m in market.items():
        meta = assets.get(asset_id, {})
        pred = predictions.get(asset_id) or {}
        risk = risk_scores.get(asset_id) or {}
        breakdown = risk_breakdowns.get(asset_id) or {}
        items.append({
            "category": "crypto",
            "id": asset_id,
            "symbol": meta.get("symbol", asset_id),
            "name": meta.get("name", asset_id),
            "subcategory": meta.get("subcategory"),
            "logo_color": meta.get("logo_color"),
            "price": m.get("price"),
            "floor_eth": None,
            "change_24h": m.get("change_24h"),
            "change_7d": m.get("change_7d"),
            "market_cap": m.get("market_cap"),
            "volume_24h": m.get("volume_24h"),
            "risk_score": risk.get("risk_score"),
            "volatility": breakdown.get("volatility_index"),
            "expected_return": pred.get("prediction_30d"),
            "verified": None,
            "held": asset_id in flags["held"],
            "watching": asset_id in flags["watching"],
            "sparkline": sparks.get(asset_id, []),
            **_aai_fields(aai_scores.get(asset_id), live_sentiment.get(asset_id)),
        })
    return items


def build_nft_items(user_id=None) -> list[dict]:
    collections = {c["slug"]: c for c in get_nft_collections()}
    market = {m["slug"]: m for m in get_nft_market_data_all_latest()}
    aai_scores = get_all_latest_aai_scores("nft")
    liquidity = get_all_latest_nft_liquidity()
    flags = get_user_flags(user_id)

    items = []
    for slug, m in market.items():
        meta = collections.get(slug, {})
        liq = liquidity.get(slug) or {}
        supply = meta.get("supply")
        floor_usd = m.get("floor_usd")
        items.append({
            "category": "nft",
            "id": slug,
            "symbol": meta.get("symbol"),
            "name": meta.get("name", slug),
            "subcategory": meta.get("subcategory"),
            "logo_color": meta.get("banner_color"),
            "price": floor_usd,
            "floor_eth": m.get("floor_eth"),
            "change_24h": m.get("change_24h"),
            "change_7d": m.get("change_7d"),
            "market_cap": floor_usd * supply if floor_usd and supply else None,
            "volume_24h": m.get("volume_24h_eth"),
            "risk_score": None,
            "volatility": liq.get("illiquidity_risk_score"),
            "expected_return": None,
            "verified": meta.get("verified"),
            "held": slug in flags["held"],
            "watching": slug in flags["watching"],
            "sparkline": [],
            **_aai_fields(aai_scores.get(slug)),
        })
    return items
