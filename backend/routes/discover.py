"""
routes/discover.py

Unified browse endpoint across crypto assets and NFT collections. Supports
category filtering, a few sort keys, and basic range filters on price/AAI.
"""
import path_setup  # noqa: F401

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import DiscoverItem
from db.queries import (
    get_asset_market_data_all_latest,
    get_nft_market_data_all_latest,
    get_all_latest_aai_scores,
    get_supported_assets,
    get_nft_collections,
)

router = APIRouter(tags=["Discover"])

_SORT_KEYS = {"price", "change_24h", "change_7d", "market_cap", "volume_24h", "aai_score"}


def _build_crypto_items() -> list[dict]:
    assets = {a["asset_id"]: a for a in get_supported_assets()}
    market = get_asset_market_data_all_latest()
    aai_scores = get_all_latest_aai_scores("crypto")

    items = []
    for m in market:
        asset_id = m["asset_id"]
        meta = assets.get(asset_id, {})
        aai = aai_scores.get(asset_id)
        items.append({
            "category": "crypto",
            "id": asset_id,
            "symbol": meta.get("symbol", asset_id),
            "name": meta.get("name", asset_id),
            "logo_color": meta.get("logo_color"),
            "price": m.get("price"),
            "change_24h": m.get("change_24h"),
            "change_7d": m.get("change_7d"),
            "market_cap": m.get("market_cap"),
            "volume_24h": m.get("volume_24h"),
            "aai_score": aai.get("aai_score") if aai else None,
            "verified": None,
        })
    return items


def _build_nft_items() -> list[dict]:
    collections = {c["slug"]: c for c in get_nft_collections()}
    market = get_nft_market_data_all_latest()
    aai_scores = get_all_latest_aai_scores("nft")

    items = []
    for m in market:
        slug = m["slug"]
        meta = collections.get(slug, {})
        aai = aai_scores.get(slug)
        items.append({
            "category": "nft",
            "id": slug,
            "symbol": meta.get("symbol"),
            "name": meta.get("name", slug),
            "logo_color": meta.get("banner_color"),
            "price": m.get("floor_usd"),
            "change_24h": m.get("change_24h"),
            "change_7d": m.get("change_7d"),
            "market_cap": None,
            "volume_24h": m.get("volume_24h_eth"),
            "aai_score": aai.get("aai_score") if aai else None,
            "verified": meta.get("verified"),
        })
    return items


# ── GET /discover ────────────────────────────────────────────────────────────

@router.get("/discover", response_model=list[DiscoverItem])
def discover(
    category: str = Query("all", pattern="^(all|crypto|nft)$"),
    sort: str = Query("market_cap"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_aai: Optional[float] = Query(None),
    verified_only: bool = Query(False),
):
    if sort not in _SORT_KEYS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(_SORT_KEYS)}.")

    try:
        items: list[dict] = []
        if category in ("all", "crypto"):
            items += _build_crypto_items()
        if category in ("all", "nft"):
            items += _build_nft_items()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if min_price is not None:
        items = [i for i in items if (i.get("price") or 0) >= min_price]
    if max_price is not None:
        items = [i for i in items if (i.get("price") or 0) <= max_price]
    if min_aai is not None:
        items = [i for i in items if (i.get("aai_score") or 0) >= min_aai]
    if verified_only:
        items = [i for i in items if i.get("verified") is True]

    reverse = order == "desc"
    items.sort(key=lambda i: (i.get(sort) if i.get(sort) is not None else -1), reverse=reverse)

    return items