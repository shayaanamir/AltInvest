"""
routes/discover.py

Unified browse endpoint across crypto assets and NFT collections. Supports
category filtering, sorting, range and facet filters, a text query and paging. Public, but when a
valid Bearer token is sent the `held` / `watching` flags (and the held/watching filters) reflect
that user.

GET /discover/options publishes the sort keys and the filter values that exist in the data
(subcategories, signals, ranges), so the frontend never keeps its own copy that can drift.
"""
import path_setup  # noqa: F401

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from utils.http_errors import db_unavailable

from auth.dependencies import get_optional_user_id
from controllers.market_controller import build_crypto_items, build_nft_items
from models.schemas import DiscoverItem

router = APIRouter(tags=["Discover"])

# key -> label; every key is a field on a DiscoverItem
SORTS = {
    "aai_score": "AAI score",
    "change_24h": "24h change",
    "change_7d": "7d change",
    "market_cap": "Market cap",
    "volume_24h": "24h volume",
    "price": "Price",
    "sentiment_score": "Sentiment",
    "risk_score": "Risk score",
    "expected_return": "Expected 30d return",
    "volatility": "Volatility",
    "name": "Name",
}
_SIGNALS = ("BUY", "HOLD", "SELL")


def _universe(category: str, user_id) -> list[dict]:
    items: list[dict] = []
    if category in ("all", "crypto"):
        items += build_crypto_items(user_id, with_sparklines=True)
    if category in ("all", "nft"):
        items += build_nft_items(user_id)
    return items


# ── GET /discover ────────────────────────────────────────────────────────────

@router.get("/discover", response_model=list[DiscoverItem])
def discover(
    response: Response,
    category: str = Query("all", pattern="^(all|crypto|nft)$"),
    sort: str = Query("market_cap"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    q: Optional[str] = Query(None, max_length=64, description="Name / symbol substring"),
    subcategory: Optional[list[str]] = Query(None, description="Any of these (repeatable)"),
    signal: Optional[list[str]] = Query(None, description="BUY / HOLD / SELL (repeatable)"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_aai: Optional[float] = Query(None),
    min_sentiment: Optional[float] = Query(None, description="-1..1"),
    max_volatility: Optional[float] = Query(None),
    max_risk: Optional[float] = Query(None),
    min_market_cap: Optional[float] = Query(None),
    verified_only: bool = Query(False),
    held_only: bool = Query(False),
    watching_only: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Page size; omit for everything"),
    offset: int = Query(0, ge=0),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    """
    The matching rows, sorted. With `limit`, one page of them; the full match count is in the
    X-Total-Count response header either way.
    """
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(SORTS)}.")
    if signal and any(s.upper() not in _SIGNALS for s in signal):
        raise HTTPException(status_code=422, detail=f"signal must be one of {list(_SIGNALS)}.")

    try:
        items = _universe(category, user_id)
    except Exception as exc:
        raise db_unavailable(exc)

    if q and q.strip():
        needle = q.strip().lower()
        items = [i for i in items
                 if needle in (i.get("name") or "").lower()
                 or needle in (i.get("symbol") or "").lower()
                 or needle in str(i.get("id") or "").lower()]
    if subcategory:
        wanted = set(subcategory)
        items = [i for i in items if i.get("subcategory") in wanted]
    if signal:
        wanted = {s.upper() for s in signal}
        items = [i for i in items if i.get("signal") in wanted]
    # A range filter means "must have a value inside the range": unscored rows drop out.
    if min_price is not None:
        items = [i for i in items if i.get("price") is not None and i["price"] >= min_price]
    if max_price is not None:
        items = [i for i in items if i.get("price") is not None and i["price"] <= max_price]
    if min_aai is not None:
        items = [i for i in items if i.get("aai_score") is not None and i["aai_score"] >= min_aai]
    if min_sentiment is not None:
        items = [i for i in items if i.get("sentiment_score") is not None and i["sentiment_score"] >= min_sentiment]
    if max_volatility is not None:
        items = [i for i in items if i.get("volatility") is not None and i["volatility"] <= max_volatility]
    if max_risk is not None:
        items = [i for i in items if i.get("risk_score") is not None and i["risk_score"] <= max_risk]
    if min_market_cap is not None:
        items = [i for i in items if i.get("market_cap") is not None and i["market_cap"] >= min_market_cap]
    if verified_only:
        items = [i for i in items if i.get("verified") is True]
    if held_only:
        items = [i for i in items if i.get("held")]
    if watching_only:
        items = [i for i in items if i.get("watching")]

    reverse = order == "desc"
    if sort == "name":
        items.sort(key=lambda i: (i.get("name") or "").lower(), reverse=reverse)
    else:
        # Missing values always sort last, whichever direction was asked for.
        present = [i for i in items if i.get(sort) is not None]
        missing = [i for i in items if i.get(sort) is None]
        present.sort(key=lambda i: i[sort], reverse=reverse)
        items = present + missing

    response.headers["X-Total-Count"] = str(len(items))
    if limit is not None:
        items = items[offset:offset + limit]
    return items


# ── GET /discover/options ────────────────────────────────────────────────────

@router.get("/discover/options")
def discover_options(category: str = Query("all", pattern="^(all|crypto|nft)$")):
    """Sort keys, and the filter values that actually occur in the data for this category."""
    try:
        items = _universe(category, None)
    except Exception as exc:
        raise db_unavailable(exc)

    def count_by(field):
        counts: dict[str, int] = {}
        for i in items:
            v = i.get(field)
            if v:
                counts[v] = counts.get(v, 0) + 1
        return [{"value": k, "count": n} for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    def span(field):
        vals = [i[field] for i in items if isinstance(i.get(field), (int, float))]
        return {"min": min(vals), "max": max(vals)} if vals else None

    return {
        "sorts": [{"key": k, "label": v} for k, v in SORTS.items()],
        "subcategories": count_by("subcategory"),
        "signals": [s for s in count_by("signal") if s["value"] in _SIGNALS],
        "ranges": {f: span(f) for f in ("price", "market_cap", "aai_score", "sentiment_score", "volatility", "risk_score")},
        "has_verified": any(i.get("verified") is not None for i in items),
        "total": len(items),
    }
