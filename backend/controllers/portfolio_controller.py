"""
backend/controllers/portfolio_controller.py

Shared logic for turning raw portfolio_holdings rows into USD-valued,
display-ready holdings. Used by both routes/dashboard.py and
routes/portfolio.py so the valuation logic lives in exactly one place.
"""
from db.queries import (
    get_portfolio_holdings,
    get_asset_market_data_all_latest,
    get_nft_market_data_latest,
    get_asset,
    get_nft_collection,
)


def get_valued_holdings(user_id) -> list[dict]:
    """
    Returns each holding enriched with current_price, current_value_usd,
    and unrealised_pnl_usd (crypto only — NFT cost basis is in ETH terms
    at buy time, so P&L needs the ETH/USD rate at buy time vs now, which
    isn't tracked live yet; NFT holdings get current_value_usd only).
    """
    holdings = get_portfolio_holdings(user_id)
    market_latest = get_asset_market_data_all_latest()
    price_by_asset = {m["asset_id"]: m.get("price", 0.0) for m in market_latest}

    valued = []
    for h in holdings:
        if h.get("asset_type") == "crypto":
            symbol = h.get("symbol", "")
            price = price_by_asset.get(symbol, 0.0)
            quantity = h.get("quantity", 0.0)
            current_value = round(price * quantity, 2)
            cost_basis = h.get("cost_basis_usd", 0.0) or 0.0
            asset_meta = get_asset(symbol) or {}
            valued.append({
                **h,
                "name": asset_meta.get("name", symbol),
                "current_price": price,
                "current_value_usd": current_value,
                "unrealised_pnl_usd": round(current_value - cost_basis, 2),
                "unrealised_pnl_pct": round(
                    ((current_value - cost_basis) / cost_basis) * 100, 2
                ) if cost_basis else None,
            })
        elif h.get("asset_type") == "nft":
            slug = h.get("nft_collection_slug", "")
            nft_market = get_nft_market_data_latest(slug) or {}
            floor_usd = nft_market.get("floor_usd", 0.0)
            quantity = h.get("quantity", 1)
            current_value = round(floor_usd * quantity, 2)
            cost_basis = h.get("cost_basis_usd", 0.0) or 0.0
            collection_meta = get_nft_collection(slug) or {}
            valued.append({
                **h,
                "name": collection_meta.get("name", slug),
                "current_price": floor_usd,
                "current_value_usd": current_value,
                "unrealised_pnl_usd": round(current_value - cost_basis, 2),
                "unrealised_pnl_pct": round(
                    ((current_value - cost_basis) / cost_basis) * 100, 2
                ) if cost_basis else None,
            })
        else:
            valued.append({**h, "current_price": None, "current_value_usd": 0.0,
                            "unrealised_pnl_usd": None, "unrealised_pnl_pct": None})

    return valued


def get_total_portfolio_value(user_id) -> float:
    return round(sum(h["current_value_usd"] for h in get_valued_holdings(user_id)), 2)