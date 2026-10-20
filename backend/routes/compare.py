"""
routes/compare.py

Side-by-side comparison across crypto assets and/or NFT collections.
Generates a lightweight rule-based verdict — not stored, computed fresh
per request, per the schema doc ("[COMPUTED], ... rule-based comparator").

GET /compare/candidates is the picker's search: small rows (no sparklines), searched and ranked on
the server, with the items already chosen marked so the picker can show them as selected.
"""
import path_setup  # noqa: F401

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.http_errors import db_unavailable

from auth.dependencies import get_optional_user_id
from controllers.market_controller import build_crypto_items, build_nft_items
from models.schemas import CompareResponse

router = APIRouter(tags=["Compare"])

_MAX_ITEMS = 4


def _build_verdict(items: list[dict]) -> str:
    scored = [i for i in items if i.get("aai_score") is not None]
    if len(scored) < 2:
        return "Not enough AAI data across these items yet to generate a comparison."

    best = max(scored, key=lambda i: i["aai_score"])
    worst = min(scored, key=lambda i: i["aai_score"])
    if best["id"] == worst["id"]:
        return f"{best['name']} is the only item with a computed AAI score."

    gap = round(best["aai_score"] - worst["aai_score"], 1)
    lower_risk = min(
        (i for i in items if i.get("volatility") is not None),
        key=lambda i: i["volatility"],
        default=None,
    )

    verdict = f"{best['name']} currently has the strongest AAI score ({best['aai_score']}), {gap} points ahead of {worst['name']} ({worst['aai_score']})."
    if lower_risk and lower_risk["id"] != best["id"]:
        verdict += f" {lower_risk['name']} has the lowest measured volatility of the group."
    return verdict


# ── GET /compare ─────────────────────────────────────────────────────────────

_CANDIDATE_FIELDS = ("id", "category", "symbol", "name", "subcategory", "logo_color", "price",
                     "floor_eth", "change_24h", "aai_score", "signal", "held", "watching")


def _rank(item: dict, needle: str) -> tuple:
    """Exact symbol/id first, then names or symbols that start with the text, then anything containing it."""
    name, sym, ident = (item.get("name") or "").lower(), (item.get("symbol") or "").lower(), str(item["id"]).lower()
    if needle in (sym, ident):
        tier = 0
    elif name.startswith(needle) or sym.startswith(needle):
        tier = 1
    else:
        tier = 2
    return (tier, -(item.get("market_cap") or 0))


@router.get("/compare/candidates")
def compare_candidates(
    q: str = Query("", max_length=64, description="Name / symbol / slug text; empty lists the biggest first"),
    category: str = Query("all", pattern="^(all|crypto|nft)$"),
    selected: str = Query("", description="Comma-separated ids already picked (marked selected=true)"),
    limit: int = Query(30, ge=1, le=100),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    """What the compare picker can add: light rows, best match first, at most `limit`."""
    picked = {x.strip().lower() for x in selected.split(",") if x.strip()}
    try:
        items = []
        if category in ("all", "crypto"):
            items += build_crypto_items(user_id, with_sparklines=False)
        if category in ("all", "nft"):
            items += build_nft_items(user_id)
    except Exception as exc:
        raise db_unavailable(exc)

    needle = q.strip().lower()
    if needle:
        items = [i for i in items
                 if needle in (i.get("name") or "").lower()
                 or needle in (i.get("symbol") or "").lower()
                 or needle in str(i["id"]).lower()]
        items.sort(key=lambda i: _rank(i, needle))
    else:
        items.sort(key=lambda i: -(i.get("market_cap") or 0))

    total = len(items)
    rows = [{**{k: i.get(k) for k in _CANDIDATE_FIELDS}, "selected": str(i["id"]).lower() in picked}
            for i in items[:limit]]
    return {"items": rows, "total": total, "max_selectable": _MAX_ITEMS}


@router.get("/compare", response_model=CompareResponse)
def compare(
    assets: str = Query("", description="Comma-separated crypto symbols, e.g. 'btc,eth'"),
    nft: str = Query("", description="Comma-separated NFT collection slugs"),
    ids: str = Query("", description="Comma-separated mix of symbols and slugs; the server works out which is which"),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    asset_symbols = [s.strip().upper() for s in assets.split(",") if s.strip()]
    nft_slugs = [s.strip().lower() for s in nft.split(",") if s.strip()]
    mixed = [s.strip() for s in ids.split(",") if s.strip()]

    if mixed:
        from db.queries import get_assets_by_id
        try:
            known_crypto = set(get_assets_by_id(mixed))
        except Exception as exc:
            raise db_unavailable(exc)
        for x in mixed:
            if x.upper() in known_crypto:
                asset_symbols.append(x.upper())
            else:
                nft_slugs.append(x.lower())
    # The same item twice isn't a comparison.
    asset_symbols = list(dict.fromkeys(asset_symbols))
    nft_slugs = list(dict.fromkeys(nft_slugs))

    total = len(asset_symbols) + len(nft_slugs)
    if total < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 items to compare (via assets and/or nft).")
    if total > _MAX_ITEMS:
        raise HTTPException(status_code=422, detail=f"Compare supports at most {_MAX_ITEMS} items at once.")

    try:
        crypto = {i["id"]: i for i in build_crypto_items(user_id, with_sparklines=False)} if asset_symbols else {}
        nfts = {i["id"]: i for i in build_nft_items(user_id)} if nft_slugs else {}
    except Exception as exc:
        raise db_unavailable(exc)

    items = []
    for sym in asset_symbols:
        if sym not in crypto:
            raise HTTPException(status_code=404, detail=f"Asset '{sym}' isn't covered.")
        items.append(crypto[sym])
    for slug in nft_slugs:
        if slug not in nfts:
            raise HTTPException(status_code=404, detail=f"'{slug}' isn't a covered asset or NFT collection.")
        items.append(nfts[slug])

    return {"items": items, "verdict": _build_verdict(items)}
