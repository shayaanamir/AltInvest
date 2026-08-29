"""
routes/nft.py

NFT collection list, collection detail (joins across nft_market_data,
nft_holder_stats, nft_liquidity, nft_risk_breakdown, nft_traits,
nft_sales, aai_scores), and individual token detail.

Public routes — no auth required, same as routes/assets.py.
"""
import path_setup  # noqa: F401

from fastapi import APIRouter, HTTPException, Query

from models.schemas import NFTCollectionListItem, NFTCollectionDetail, NFTTokenDetail
from db.queries import (
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
)

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if not collection:
        raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")

    market = _serialize_ts(get_nft_market_data_latest(slug))
    holder_stats = _serialize_ts(get_nft_holder_stats(slug))
    liquidity = _serialize_ts(get_nft_liquidity(slug))
    risk_breakdown = _serialize_ts(get_nft_risk_breakdown(slug))
    traits = get_nft_traits(slug) or {}
    sales = [_serialize_ts(s) for s in get_nft_sales(slug, limit=10)]
    aai = get_latest_aai_score("nft", slug)

    return {
        **collection,
        "market": market,
        "holder_stats": holder_stats,
        "liquidity": liquidity,
        "risk_breakdown": risk_breakdown,
        "trait_categories": traits.get("categories", []),
        "recent_sales": sales,
        "aai_score": aai.get("aai_score") if aai else None,
    }


# ── GET /nft/collections/{slug}/tokens/{token_id} ───────────────────────────

@router.get("/nft/collections/{slug}/tokens/{token_id}", response_model=NFTTokenDetail)
def get_nft_token_detail(slug: str, token_id: str):
    try:
        collection = get_nft_collection(slug)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

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