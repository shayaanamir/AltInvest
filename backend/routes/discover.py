"""
routes/discover.py

Unified browse endpoint across crypto assets and NFT collections. Supports
category filtering, sorting and range filters. Public, but when a valid
Bearer token is sent the `held` / `watching` flags reflect that user.
"""
import path_setup  # noqa: F401

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_optional_user_id
from controllers.market_controller import build_crypto_items, build_nft_items
from models.schemas import DiscoverItem

router = APIRouter(tags=["Discover"])

_SORT_KEYS = {
    "price", "change_24h", "change_7d", "market_cap", "volume_24h",
    "aai_score", "volatility", "name",
}


# ── GET /discover ────────────────────────────────────────────────────────────

@router.get("/discover", response_model=list[DiscoverItem])
def discover(
    category: str = Query("all", pattern="^(all|crypto|nft)$"),
    sort: str = Query("market_cap"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    q: Optional[str] = Query(None, description="Name / symbol substring"),
    subcategory: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_aai: Optional[float] = Query(None),
    min_sentiment: Optional[float] = Query(None, description="-1..1"),
    max_volatility: Optional[float] = Query(None),
    min_market_cap: Optional[float] = Query(None),
    verified_only: bool = Query(False),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    if sort not in _SORT_KEYS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(_SORT_KEYS)}.")

    try:
        items: list[dict] = []
        if category in ("all", "crypto"):
            items += build_crypto_items(user_id, with_sparklines=True)
        if category in ("all", "nft"):
            items += build_nft_items(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    if q:
        needle = q.strip().lower()
        items = [i for i in items
                 if needle in (i.get("name") or "").lower() or needle in (i.get("symbol") or "").lower()]
    if subcategory:
        items = [i for i in items if i.get("subcategory") == subcategory]
    if min_price is not None:
        items = [i for i in items if (i.get("price") or 0) >= min_price]
    if max_price is not None:
        items = [i for i in items if (i.get("price") or 0) <= max_price]
    # The client only sends a range filter once it differs from its default, so an
    # active filter means "must have a value inside the range".
    if min_aai is not None:
        items = [i for i in items if i.get("aai_score") is not None and i["aai_score"] >= min_aai]
    if min_sentiment is not None:
        items = [i for i in items if i.get("sentiment_score") is not None and i["sentiment_score"] >= min_sentiment]
    if max_volatility is not None:
        items = [i for i in items if i.get("volatility") is not None and i["volatility"] <= max_volatility]
    if min_market_cap is not None:
        items = [i for i in items if i.get("market_cap") is not None and i["market_cap"] >= min_market_cap]
    if verified_only:
        items = [i for i in items if i.get("verified") is True]

    reverse = order == "desc"
    if sort == "name":
        items.sort(key=lambda i: (i.get("name") or "").lower(), reverse=reverse)
    else:
        # Missing values always sort last, whichever direction was asked for.
        present = [i for i in items if i.get(sort) is not None]
        missing = [i for i in items if i.get(sort) is None]
        present.sort(key=lambda i: i[sort], reverse=reverse)
        items = present + missing

    return items
