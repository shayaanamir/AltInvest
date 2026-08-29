"""
routes/portfolio.py

Portfolio summary, performance, allocation, and holdings CRUD.
All routes are user-scoped — see auth/dependencies.py::get_current_user_id.
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone
from collections import defaultdict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import (
    PortfolioHoldingIn,
    PortfolioHoldingOut,
    PortfolioSummary,
    AllocationSlice,
)
from controllers.portfolio_controller import get_valued_holdings
from db.queries import (
    insert_portfolio_holding,
    update_portfolio_holding,
    delete_portfolio_holding,
    get_portfolio_snapshots,
)

router = APIRouter(tags=["Portfolio"])

_FILTER_DAYS = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}


def _serialize(h: dict) -> dict:
    """Datetime fields → ISO strings for JSON response."""
    out = dict(h)
    for field in ("date_added", "updated_at"):
        v = out.get(field)
        if hasattr(v, "strftime"):
            out[field] = v.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


# ── GET /portfolio/summary ──────────────────────────────────────────────────

@router.get("/portfolio/summary", response_model=PortfolioSummary)
def get_portfolio_summary(user_id: ObjectId = Depends(get_current_user_id)):
    valued = get_valued_holdings(user_id)

    total_value = sum(h["current_value_usd"] or 0.0 for h in valued)
    total_cost = sum(h.get("cost_basis_usd") or 0.0 for h in valued)
    total_pnl = total_value - total_cost

    return PortfolioSummary(
        total_value_usd=round(total_value, 2),
        total_cost_basis_usd=round(total_cost, 2),
        total_unrealised_pnl_usd=round(total_pnl, 2),
        total_unrealised_pnl_pct=round((total_pnl / total_cost) * 100, 2) if total_cost else None,
        holding_count=len(valued),
    )


# ── GET /portfolio/performance ──────────────────────────────────────────────

@router.get("/portfolio/performance")
def get_portfolio_performance(
    filter: str = Query("1M", pattern="^(1D|1W|1M|3M|1Y)$"),
    user_id: ObjectId = Depends(get_current_user_id),
):
    """
    Same semantics as /dashboard/performance — kept as a separate route
    since the Portfolio page and Dashboard page are different frontend
    surfaces, but the underlying data source is identical. If these ever
    drift apart in what they show, split the implementations; for now
    this delegates to the dashboard version to avoid duplicated logic.
    """
    from routes.dashboard import get_dashboard_performance
    return get_dashboard_performance(filter=filter, user_id=user_id)


# ── GET /portfolio/allocation ────────────────────────────────────────────────

@router.get("/portfolio/allocation")
def get_portfolio_allocation(
    by: str = Query("category", pattern="^(category|asset)$"),
    user_id: ObjectId = Depends(get_current_user_id),
):
    """
    by=category → crypto vs nft split.
    by=asset    → per-symbol/per-collection split (top-level, no sub-grouping).
    """
    valued = get_valued_holdings(user_id)
    total_value = sum(h["current_value_usd"] or 0.0 for h in valued) or 1.0  # avoid /0

    buckets: dict[str, float] = defaultdict(float)
    for h in valued:
        if by == "category":
            key = h.get("asset_type", "unknown")
        else:
            key = h.get("symbol") or h.get("nft_collection_slug") or "unknown"
        buckets[key] += h["current_value_usd"] or 0.0

    slices = [
        AllocationSlice(
            label=label,
            value_usd=round(value, 2),
            pct_of_portfolio=round((value / total_value) * 100, 2),
        )
        for label, value in buckets.items()
    ]
    slices.sort(key=lambda s: s.value_usd, reverse=True)
    return slices


# ── GET /portfolio/holdings ─────────────────────────────────────────────────

@router.get("/portfolio/holdings", response_model=list[PortfolioHoldingOut])
def list_portfolio_holdings(user_id: ObjectId = Depends(get_current_user_id)):
    valued = get_valued_holdings(user_id)
    return [_serialize(h) for h in valued]


# ── POST /portfolio/holdings ────────────────────────────────────────────────

@router.post("/portfolio/holdings", status_code=201)
def create_portfolio_holding(
    payload: PortfolioHoldingIn, user_id: ObjectId = Depends(get_current_user_id)
):
    if payload.asset_type not in ("crypto", "nft"):
        raise HTTPException(status_code=422, detail="asset_type must be 'crypto' or 'nft'.")
    if payload.asset_type == "crypto" and not payload.symbol:
        raise HTTPException(status_code=422, detail="symbol is required for crypto holdings.")
    if payload.asset_type == "nft" and not (payload.nft_collection_slug and payload.nft_token_id):
        raise HTTPException(
            status_code=422,
            detail="nft_collection_slug and nft_token_id are required for nft holdings.",
        )

    holding_id = insert_portfolio_holding(user_id, payload.model_dump(exclude_none=True))
    return {"id": holding_id}


# ── PATCH /portfolio/holdings/{id} ──────────────────────────────────────────

@router.patch("/portfolio/holdings/{holding_id}")
def patch_portfolio_holding(
    holding_id: str, payload: dict, user_id: ObjectId = Depends(get_current_user_id)
):
    allowed_fields = {
        "quantity", "avg_buy_price_usd", "avg_buy_price_eth",
        "avg_buy_eth_usd_rate", "cost_basis_usd",
    }
    update = {k: v for k, v in payload.items() if k in allowed_fields}
    if not update:
        raise HTTPException(status_code=422, detail="No updatable fields provided.")

    try:
        updated = update_portfolio_holding(user_id, holding_id, update)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid holding id.")

    if not updated:
        raise HTTPException(status_code=404, detail="Holding not found.")
    return {"status": "updated"}


# ── DELETE /portfolio/holdings/{id} ─────────────────────────────────────────

@router.delete("/portfolio/holdings/{holding_id}", status_code=204)
def remove_portfolio_holding(
    holding_id: str, user_id: ObjectId = Depends(get_current_user_id)
):
    try:
        deleted = delete_portfolio_holding(user_id, holding_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid holding id.")

    if not deleted:
        raise HTTPException(status_code=404, detail="Holding not found.")
    return None