"""
routes/portfolio.py

Portfolio summary, performance, allocation, and holdings CRUD.
All routes are user-scoped — see auth/dependencies.py::get_current_user_id.
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone
from collections import defaultdict

from bson import ObjectId
from utils.http_errors import require_object_id
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import get_current_user_id
from models.schemas import (
    PortfolioHoldingIn,
    PortfolioHoldingPatch,
    PortfolioTradeIn,
    PortfolioHoldingOut,
    PortfolioSummary,
    AllocationSlice,
)
from controllers.portfolio_controller import get_valued_holdings
from controllers import holdings_controller as holdings
from controllers.portfolio_intelligence import build_intelligence

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

    # Only holdings that could be valued count toward value, cost and P&L. Including the cost of
    # a holding with no price but not its value would show a loss that hasn't happened.
    priced = [h for h in valued if h["valuation_status"] == "ok"]
    total_value = sum(h["current_value_usd"] for h in priced)
    total_cost = sum(h.get("cost_basis_usd") or 0.0 for h in priced)
    total_pnl = total_value - total_cost

    return PortfolioSummary(
        total_value_usd=round(total_value, 2),
        total_cost_basis_usd=round(total_cost, 2),
        total_unrealised_pnl_usd=round(total_pnl, 2),
        total_unrealised_pnl_pct=round((total_pnl / total_cost) * 100, 2) if total_cost else None,
        holding_count=len(valued),
        unpriced_holding_count=len(valued) - len(priced),
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


# ── GET /portfolio/intelligence ─────────────────────────────────────────────

@router.get("/portfolio/intelligence")
def get_portfolio_intelligence(user_id: ObjectId = Depends(get_current_user_id)):
    return build_intelligence(user_id)


# ── POST /portfolio/holdings ────────────────────────────────────────────────

@router.post("/portfolio/holdings", status_code=201)
def create_portfolio_holding(
    payload: PortfolioHoldingIn, user_id: ObjectId = Depends(get_current_user_id)
):
    """Adds a holding. Crypto the user already holds is merged into that holding ({"merged": true})."""
    return holdings.add_holding(user_id, payload.model_dump(exclude_none=True))


# ── PATCH /portfolio/holdings/{id} ──────────────────────────────────────────

@router.patch("/portfolio/holdings/{holding_id}")
def patch_portfolio_holding(
    holding_id: str, payload: PortfolioHoldingPatch, user_id: ObjectId = Depends(get_current_user_id)
):
    """A correction to what was recorded. Typed by PortfolioHoldingPatch (finite numbers, quantity > 0)."""
    update = payload.model_dump(exclude_none=True)
    if not update:
        raise HTTPException(status_code=422, detail="No updatable fields provided.")
    require_object_id(holding_id, "holding")
    holdings.correct_holding(user_id, holding_id, update)
    return {"status": "updated"}


# ── DELETE /portfolio/holdings/{id} ─────────────────────────────────────────

@router.delete("/portfolio/holdings/{holding_id}", status_code=204)
def remove_portfolio_holding(
    holding_id: str, user_id: ObjectId = Depends(get_current_user_id)
):
    require_object_id(holding_id, "holding")
    holdings.remove_holding(user_id, holding_id)
    return None


# ── Transactions ────────────────────────────────────────────────────────────

@router.post("/portfolio/holdings/{holding_id}/transactions", status_code=201)
def record_trade(
    holding_id: str, payload: PortfolioTradeIn, user_id: ObjectId = Depends(get_current_user_id)
):
    """Record a buy or sell against a crypto holding. Selling everything closes the holding."""
    require_object_id(holding_id, "holding")
    return holdings.trade(user_id, holding_id, payload.type, payload.quantity, payload.price_usd)


@router.get("/portfolio/holdings/{holding_id}/transactions")
def holding_transactions(holding_id: str, user_id: ObjectId = Depends(get_current_user_id)):
    require_object_id(holding_id, "holding")
    return holdings.list_transactions(user_id, holding_id)


@router.get("/portfolio/transactions")
def all_transactions(
    limit: int = Query(100, ge=1, le=500), user_id: ObjectId = Depends(get_current_user_id)
):
    return holdings.list_transactions(user_id, limit=limit)
