"""
routes/watchlists.py

Watchlist CRUD + item add/remove. Items are enriched at read time with
live price/AAI data rather than stored denormalised, per the schema doc's
note: "resolve live price/AAI at read time by joining assets/nft_collections."
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user_id
from models.schemas import WatchlistOut, WatchlistCreate, WatchlistItemIn
from utils.serialization import serialize_dates
from db.queries import (
    get_watchlists,
    create_watchlist,
    delete_watchlist,
    add_watchlist_item,
    remove_watchlist_item,
    get_asset,
    get_asset_market_data_latest,
    get_nft_collection,
    get_nft_market_data_latest,
    get_latest_aai_score,
)

router = APIRouter(tags=["Watchlists"])


def _enrich_item(item: dict) -> dict:
    item = serialize_dates(item)
    symbol_or_slug = item["symbol_or_slug"]

    if item["type"] == "crypto":
        asset = get_asset(symbol_or_slug) or {}
        market = get_asset_market_data_latest(symbol_or_slug) or {}
        aai = get_latest_aai_score("crypto", symbol_or_slug)
        item["name"] = asset.get("name", symbol_or_slug)
        item["price"] = market.get("price")
        item["change_24h"] = market.get("change_24h")
        item["aai_score"] = aai.get("aai_score") if aai else None
    elif item["type"] == "nft":
        collection = get_nft_collection(symbol_or_slug) or {}
        market = get_nft_market_data_latest(symbol_or_slug) or {}
        aai = get_latest_aai_score("nft", symbol_or_slug)
        item["name"] = collection.get("name", symbol_or_slug)
        item["price"] = market.get("floor_usd")
        item["change_24h"] = market.get("change_24h")
        item["aai_score"] = aai.get("aai_score") if aai else None

    return item


def _enrich_watchlist(w: dict) -> dict:
    w = serialize_dates(w)
    w["items"] = [_enrich_item(i) for i in w.get("items", [])]
    return w


# ── GET /watchlists ──────────────────────────────────────────────────────────

@router.get("/watchlists", response_model=list[WatchlistOut])
def list_watchlists(user_id: ObjectId = Depends(get_current_user_id)):
    watchlists = get_watchlists(user_id)
    return [_enrich_watchlist(w) for w in watchlists]


# ── POST /watchlists ─────────────────────────────────────────────────────────

@router.post("/watchlists", status_code=201)
def create_new_watchlist(
    payload: WatchlistCreate, user_id: ObjectId = Depends(get_current_user_id)
):
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Watchlist name cannot be empty.")
    watchlist_id = create_watchlist(user_id, payload.name.strip())
    return {"id": watchlist_id}


# ── DELETE /watchlists/{id} ──────────────────────────────────────────────────

@router.delete("/watchlists/{watchlist_id}", status_code=204)
def remove_watchlist(watchlist_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    try:
        deleted = delete_watchlist(user_id, watchlist_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid watchlist id.")

    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist not found.")
    return None


# ── POST /watchlists/{id}/items ──────────────────────────────────────────────

@router.post("/watchlists/{watchlist_id}/items", status_code=201)
def add_item_to_watchlist(
    watchlist_id: str, payload: WatchlistItemIn,
    user_id: ObjectId = Depends(get_current_user_id),
):
    if payload.type not in ("crypto", "nft"):
        raise HTTPException(status_code=422, detail="type must be 'crypto' or 'nft'.")

    # Validate the target actually exists before adding it
    if payload.type == "crypto" and not get_asset(payload.symbol_or_slug):
        raise HTTPException(status_code=404, detail=f"Asset '{payload.symbol_or_slug}' not found.")
    if payload.type == "nft" and not get_nft_collection(payload.symbol_or_slug):
        raise HTTPException(status_code=404, detail=f"NFT collection '{payload.symbol_or_slug}' not found.")

    try:
        added = add_watchlist_item(user_id, watchlist_id, payload.type, payload.symbol_or_slug)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid watchlist id.")

    if not added:
        raise HTTPException(status_code=404, detail="Watchlist not found.")
    return {"status": "added"}


# ── DELETE /watchlists/{id}/items/{symbol_or_slug} ──────────────────────────

@router.delete("/watchlists/{watchlist_id}/items/{symbol_or_slug}", status_code=204)
def remove_item_from_watchlist(
    watchlist_id: str, symbol_or_slug: str,
    user_id: ObjectId = Depends(get_current_user_id),
):
    try:
        removed = remove_watchlist_item(user_id, watchlist_id, symbol_or_slug)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid watchlist id.")

    if not removed:
        raise HTTPException(status_code=404, detail="Watchlist or item not found.")
    return None