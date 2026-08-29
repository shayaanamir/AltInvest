"""
routes/compare.py

Side-by-side comparison across crypto assets and/or NFT collections.
Generates a lightweight rule-based verdict — not stored, computed fresh
per request, per the schema doc ("[COMPUTED], ... rule-based comparator").
"""
import path_setup  # noqa: F401

from fastapi import APIRouter, HTTPException, Query

from models.schemas import CompareResponse
from db.queries import (
    get_asset,
    get_asset_market_data_latest,
    get_latest_aai_score,
    get_latest_risk,
    get_nft_collection,
    get_nft_market_data_latest,
    get_nft_risk_breakdown,
)

router = APIRouter(tags=["Compare"])

_MAX_ITEMS = 4


def _crypto_item(symbol: str) -> dict:
    asset = get_asset(symbol)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found.")

    market = get_asset_market_data_latest(symbol) or {}
    aai = get_latest_aai_score("crypto", symbol)
    risk = get_latest_risk(symbol)

    return {
        "category": "crypto",
        "id": symbol,
        "name": asset.get("name", symbol),
        "price": market.get("price"),
        "change_24h": market.get("change_24h"),
        "change_7d": market.get("change_7d"),
        "aai_score": aai.get("aai_score") if aai else None,
        "risk_score": risk.get("risk_score") if risk else None,
        "sentiment_score": aai.get("sentiment_score") if aai else None,
    }


def _nft_item(slug: str) -> dict:
    collection = get_nft_collection(slug)
    if not collection:
        raise HTTPException(status_code=404, detail=f"NFT collection '{slug}' not found.")

    market = get_nft_market_data_latest(slug) or {}
    aai = get_latest_aai_score("nft", slug)
    risk_breakdown = get_nft_risk_breakdown(slug) or {}

    # No single normalised risk_score exists for NFTs yet (only the
    # 3-part breakdown) — approximate with a simple average for comparison
    # purposes only. Not used anywhere else, so this stays local to compare.py.
    risk_parts = [
        risk_breakdown.get("floor_volatility_30d"),
        risk_breakdown.get("holder_concentration"),
    ]
    risk_parts = [p for p in risk_parts if p is not None]
    approx_risk = round(sum(risk_parts) / len(risk_parts), 2) if risk_parts else None

    return {
        "category": "nft",
        "id": slug,
        "name": collection.get("name", slug),
        "price": market.get("floor_usd"),
        "change_24h": market.get("change_24h"),
        "change_7d": market.get("change_7d"),
        "aai_score": aai.get("aai_score") if aai else None,
        "risk_score": approx_risk,
        "sentiment_score": None,
    }


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
        (i for i in items if i.get("risk_score") is not None),
        key=lambda i: i["risk_score"],
        default=None,
    )

    verdict = f"{best['name']} currently has the strongest AAI score ({best['aai_score']}), {gap} points ahead of {worst['name']} ({worst['aai_score']})."
    if lower_risk and lower_risk["id"] != best["id"]:
        verdict += f" {lower_risk['name']} carries the lowest measured risk of the group."
    return verdict


# ── GET /compare ─────────────────────────────────────────────────────────────

@router.get("/compare", response_model=CompareResponse)
def compare(
    assets: str = Query("", description="Comma-separated crypto symbols, e.g. 'btc,eth'"),
    nft: str = Query("", description="Comma-separated NFT collection slugs"),
):
    asset_symbols = [s.strip().upper() for s in assets.split(",") if s.strip()]
    nft_slugs = [s.strip() for s in nft.split(",") if s.strip()]

    total = len(asset_symbols) + len(nft_slugs)
    if total < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 items to compare (via assets and/or nft).")
    if total > _MAX_ITEMS:
        raise HTTPException(status_code=422, detail=f"Compare supports at most {_MAX_ITEMS} items at once.")

    try:
        items = [_crypto_item(s) for s in asset_symbols] + [_nft_item(s) for s in nft_slugs]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    return {"items": items, "verdict": _build_verdict(items)}