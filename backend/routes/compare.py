"""
routes/compare.py

Side-by-side comparison across crypto assets and/or NFT collections.
Generates a lightweight rule-based verdict — not stored, computed fresh
per request, per the schema doc ("[COMPUTED], ... rule-based comparator").
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

@router.get("/compare", response_model=CompareResponse)
def compare(
    assets: str = Query("", description="Comma-separated crypto symbols, e.g. 'btc,eth'"),
    nft: str = Query("", description="Comma-separated NFT collection slugs"),
    user_id: Optional[ObjectId] = Depends(get_optional_user_id),
):
    asset_symbols = [s.strip().upper() for s in assets.split(",") if s.strip()]
    nft_slugs = [s.strip() for s in nft.split(",") if s.strip()]

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
            raise HTTPException(status_code=404, detail=f"Asset '{sym}' not found.")
        items.append(crypto[sym])
    for slug in nft_slugs:
        if slug not in nfts:
            raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")
        items.append(nfts[slug])

    return {"items": items, "verdict": _build_verdict(items)}
