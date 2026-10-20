"""
routes/watchlists.py

Watchlist CRUD + item add/remove. Items are enriched at read time with
live price/AAI data rather than stored denormalised, per the schema doc's
note: "resolve live price/AAI at read time by joining assets/nft_collections."
"""
import path_setup  # noqa: F401

from bson import ObjectId
from utils.http_errors import require_object_id
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
    get_nft_collection,
    get_assets_by_id,
    get_asset_market_data_latest_by_id,
    get_nft_collections_by_slug,
    get_nft_market_data_latest_by_slug,
    get_latest_aai_scores_for,
)

router = APIRouter(tags=["Watchlists"])


def _enrich_watchlists(watchlists: list) -> list:
    """
    Adds name / price / 24h change / AAI to every item of every list, with one batched
    lookup per collection for all items together (not several queries per item).
    """
    items = [i for w in watchlists for i in w.get("items", [])]
    symbols = [i["symbol_or_slug"] for i in items if i.get("type") == "crypto"]
    slugs = [i["symbol_or_slug"] for i in items if i.get("type") == "nft"]
    assets = get_assets_by_id(symbols)
    markets = get_asset_market_data_latest_by_id(symbols)
    collections = get_nft_collections_by_slug(slugs)
    nft_markets = get_nft_market_data_latest_by_slug(slugs)
    crypto_aai = get_latest_aai_scores_for("crypto", [x.upper() for x in symbols])
    nft_aai = get_latest_aai_scores_for("nft", slugs)

    def enrich(item: dict) -> dict:
        item = serialize_dates(item)
        key = item["symbol_or_slug"]
        if item["type"] == "crypto":
            sym = key.upper()
            market = markets.get(sym, {})
            item["name"] = assets.get(sym, {}).get("name", key)
            item["price"] = market.get("price")
            item["change_24h"] = market.get("change_24h")
            item["aai_score"] = (crypto_aai.get(sym) or {}).get("aai_score")
        elif item["type"] == "nft":
            market = nft_markets.get(key, {})
            item["name"] = collections.get(key, {}).get("name", key)
            item["price"] = market.get("floor_usd")
            item["change_24h"] = market.get("change_24h")
            item["aai_score"] = (nft_aai.get(key) or {}).get("aai_score")
        return item

    out = []
    for w in watchlists:
        w = serialize_dates(w)
        w["items"] = [enrich(i) for i in w.get("items", [])]
        out.append(w)
    return out


# ── GET /watchlists ──────────────────────────────────────────────────────────

@router.get("/watchlists", response_model=list[WatchlistOut])
def list_watchlists(user_id: ObjectId = Depends(get_current_user_id)):
    watchlists = get_watchlists(user_id)
    return _enrich_watchlists(watchlists)


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
    require_object_id(watchlist_id, "watchlist")
    deleted = delete_watchlist(user_id, watchlist_id)

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

    require_object_id(watchlist_id, "watchlist")
    added = add_watchlist_item(user_id, watchlist_id, payload.type, payload.symbol_or_slug)

    if not added:
        raise HTTPException(status_code=404, detail="Watchlist not found.")
    return {"status": "added"}


# ── DELETE /watchlists/{id}/items/{symbol_or_slug} ──────────────────────────

@router.delete("/watchlists/{watchlist_id}/items/{symbol_or_slug}", status_code=204)
def remove_item_from_watchlist(
    watchlist_id: str, symbol_or_slug: str,
    user_id: ObjectId = Depends(get_current_user_id),
):
    require_object_id(watchlist_id, "watchlist")
    removed = remove_watchlist_item(user_id, watchlist_id, symbol_or_slug)

    if not removed:
        raise HTTPException(status_code=404, detail="Watchlist or item not found.")
    return None