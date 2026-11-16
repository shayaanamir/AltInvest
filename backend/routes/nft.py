"""
routes/nft.py

NFT collection list, collection detail (joins across nft_market_data,
nft_holder_stats, nft_liquidity, nft_risk_breakdown, nft_traits,
nft_sales, aai_scores), and individual token detail.

Public routes — no auth required, same as routes/assets.py.
"""
import path_setup  # noqa: F401

from fastapi import APIRouter, HTTPException, Query
from utils.http_errors import db_unavailable

from models.schemas import NFTCollectionListItem, NFTCollectionDetail, NFTItemValueOut, NFTTokenDetail, NFTSentimentOut
from db.queries import (
    get_all_nft_sentiment,
    get_nft_mood_trend,
    get_nft_sentiment,
    get_nft_sentiment_history,
    get_nft_collections,
    get_nft_collection,
    get_nft_market_data_latest,
    get_nft_market_data_all_latest,
    get_nft_sales,
    get_nft_holder_stats,
    get_nft_liquidity,
    get_nft_risk_breakdown,
    get_nft_traits,
    get_nft_token,
    get_nft_token_sale_history,
    get_nft_token_ownership_history,
    get_latest_aai_score,
    get_nft_floor_history,
)
from utils.ml_rows import as_utc, iso, with_stale_note

router = APIRouter(tags=["NFT"])


def _serialize_ts(doc: dict | None) -> dict | None:
    if not doc:
        return doc
    out = dict(doc)
    ts = out.get("timestamp")
    if hasattr(ts, "strftime"):
        out["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    since = out.get("since")
    if hasattr(since, "strftime"):
        out["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


# ── GET /nft/collections ─────────────────────────────────────────────────────

@router.get("/nft/collections", response_model=list[NFTCollectionListItem])
def list_nft_collections(
    sort: str = Query("floor_usd", pattern="^(floor_usd|change_24h|change_7d|volume_24h_eth|holders_count)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        collections = get_nft_collections()
        market_by_slug = {m["slug"]: m for m in get_nft_market_data_all_latest()}
    except Exception as exc:
        raise db_unavailable(exc)

    items = []
    for c in collections:
        m = market_by_slug.get(c["slug"], {})
        items.append({
            **c,
            "floor_eth": m.get("floor_eth"),
            "floor_usd": m.get("floor_usd"),
            "change_24h": m.get("change_24h"),
            "change_7d": m.get("change_7d"),
            "volume_24h_eth": m.get("volume_24h_eth"),
            "holders_count": m.get("holders_count"),
        })

    reverse = order == "desc"
    items.sort(key=lambda i: (i.get(sort) if i.get(sort) is not None else -1), reverse=reverse)
    return items


# ── GET /nft/collections/{slug} ──────────────────────────────────────────────

@router.get("/nft/collections/{slug}", response_model=NFTCollectionDetail)
def get_nft_collection_detail(slug: str):
    try:
        collection = get_nft_collection(slug)
    except Exception as exc:
        raise db_unavailable(exc)

    if not collection:
        raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")

    market = _serialize_ts(get_nft_market_data_latest(slug))
    holder_stats = _serialize_ts(get_nft_holder_stats(slug))
    liquidity = _serialize_ts(get_nft_liquidity(slug))
    risk_breakdown = _serialize_ts(get_nft_risk_breakdown(slug))
    traits = get_nft_traits(slug) or {}
    sales = [_serialize_ts(s) for s in get_nft_sales(slug, limit=10)]
    aai = get_latest_aai_score("nft", slug)
    history = [{"date": r["date"], "floor_eth": r.get("floor_eth"), "floor_usd": r.get("floor_usd"),
                "floor_age_hours": r.get("floor_age_hours")}
               for r in get_nft_floor_history(slug)]
    # ML risk (Phase 10, ml/docs/DECISIONS.md D59, D67): the stored row's note plus the backend's 36 h stale note.
    ml_risk = risk_breakdown if (risk_breakdown or {}).get("source") == "ml-service" else None
    raw_risk = get_nft_risk_breakdown(slug) if ml_risk else None

    return {
        **collection,
        "market": market,
        "holder_stats": holder_stats,
        "liquidity": liquidity,
        "risk_breakdown": risk_breakdown,
        "trait_categories": traits.get("categories", []),
        "recent_sales": sales,
        "aai_score": aai.get("aai_score") if aai else None,
        "floor_history": history,
        "volatility": ml_risk.get("floor_volatility_30d") if ml_risk else None,
        "risk_score": ml_risk.get("risk_score") if ml_risk else None,
        "risk_note": with_stale_note(ml_risk.get("note"), raw_risk.get("timestamp")) if ml_risk else None,
        "risk_model_version": ml_risk.get("model_version") if ml_risk else None,
        "risk_as_of": ml_risk.get("date") if ml_risk else None,
        "last_updated": iso(raw_risk.get("timestamp")) if ml_risk else None,
    }


# ── NFT sentiment ────────────────────────────────────────────────────────────
# Stored readings only (controllers/nft_sentiment_controller.py writes them every 30 min): a request never
# runs the pipeline, so it never costs an LLM call.

NFT_SENTIMENT_STALE_AFTER_HOURS = 3      # six missed 30-minute cycles


def sentiment_view(doc: dict, now=None) -> dict:
    """A stored nft_sentiment row as NFTSentimentOut fields (without history)."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone.utc)
    placeholder = bool((doc.get("data_quality") or {}).get("reason"))
    ts = as_utc(doc.get("timestamp"))
    out = {k: v for k, v in doc.items() if k in NFTSentimentOut.model_fields and k != "history"}
    out["status"] = "no_articles" if placeholder else "ok"
    if placeholder:
        out["sentiment_score"] = None          # a placeholder's 0.0 is not a reading
    out["last_updated"] = iso(ts) if ts else doc.get("last_updated")
    out["stale"] = ts is not None and now - ts > timedelta(hours=NFT_SENTIMENT_STALE_AFTER_HOURS)
    return out


@router.get("/nft/sentiment", response_model=list[NFTSentimentOut])
def list_nft_sentiment():
    """Latest reading for every collection plus the NFT market (slug "nft-market")."""
    try:
        docs = get_all_nft_sentiment()
    except Exception as exc:
        raise db_unavailable(exc)
    return sorted((sentiment_view(d) for d in docs), key=lambda d: (d["slug"] == "nft-market", d["slug"]))


@router.get("/nft/sentiment/mood-trend")
def nft_mood_trend(days: int = Query(30, ge=1, le=365)):
    """Average collection sentiment over time (-1..1), like GET /sentiment/mood-trend for crypto."""
    try:
        return get_nft_mood_trend(days)
    except Exception as exc:
        raise db_unavailable(exc)


@router.get("/nft/collections/{slug}/sentiment", response_model=NFTSentimentOut)
def get_nft_collection_sentiment(slug: str, days: int = Query(7, ge=1, le=90)):
    """A collection's latest reading and its history; slug "nft-market" for the NFT market as a whole."""
    try:
        doc = get_nft_sentiment(slug)
        history = get_nft_sentiment_history(slug, days) if doc else []
    except Exception as exc:
        raise db_unavailable(exc)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No sentiment computed for '{slug}' yet.")
    return {
        **sentiment_view(doc),
        "history": [{"timestamp": iso(h["timestamp"]), "sentiment_score": h["sentiment_score"],
                     "confidence": h["confidence"], "story_count": h.get("story_count")}
                    for h in history if h.get("sentiment_score") is not None],
    }


# ── GET /nft/collections/{slug}/tokens/{token_id} ───────────────────────────

@router.get("/nft/collections/{slug}/tokens/{token_id}", response_model=NFTTokenDetail)
def get_nft_token_detail(slug: str, token_id: str):
    try:
        collection = get_nft_collection(slug)
    except Exception as exc:
        raise db_unavailable(exc)

    if not collection:
        raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")

    token = get_nft_token(slug, token_id)
    if not token:
        raise HTTPException(
            status_code=404, detail=f"Token '{token_id}' not found in collection '{slug}'."
        )

    sale_history = [_serialize_ts(s) for s in get_nft_token_sale_history(slug, token_id)]
    ownership_history = [_serialize_ts(o) for o in get_nft_token_ownership_history(slug, token_id)]

    return {
        **token,
        "sale_history": sale_history,
        "ownership_history": ownership_history,
    }

# ── GET /nft/collections/{slug}/items/{token_id}/value ──────────────────────
# Phase 10 step 10.7 (ml/docs/DECISIONS.md D78): one live call to the ML service, stored on success; if the call
# fails, the last stored estimate is returned with stale = true.

@router.get("/nft/collections/{slug}/items/{token_id}/value", response_model=NFTItemValueOut)
def get_nft_item_value(slug: str, token_id: str):
    import httpx
    from controllers.ml_pull_controller import fetch
    from controllers.nft_items import live_item_value

    token_id = str(token_id).strip()
    if not token_id.isdigit() or len(token_id) > 12:
        raise HTTPException(status_code=422, detail="token_id must be a number.")
    with httpx.Client() as client:
        status, row = live_item_value(client, fetch, slug.lower(), token_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail=f"Token '{token_id}' not found in collection '{slug}'.")
    if row is None:
        raise HTTPException(status_code=503, detail="Item estimate unavailable; the ML service did not answer.")
    return {**{k: v for k, v in row.items() if k in NFTItemValueOut.model_fields}, "stale": status == "stale"}
