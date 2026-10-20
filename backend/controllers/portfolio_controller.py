"""
backend/controllers/portfolio_controller.py

Shared logic for turning raw portfolio_holdings rows into USD-valued,
display-ready holdings. Used by both routes/dashboard.py and
routes/portfolio.py so the valuation logic lives in exactly one place.
"""
import math

from db.queries import (
    get_portfolio_holdings,
    get_asset_market_data_latest_by_id,
    get_nft_market_data_latest_by_slug,
    get_assets_by_id,
    get_nft_collections_by_slug,
)

_NUMERIC_FIELDS = ("quantity", "cost_basis_usd", "avg_buy_price_usd", "avg_buy_price_eth", "avg_buy_eth_usd_rate")


def _num(value):
    """A finite float, or None for anything else (missing, null, text, NaN/inf, a bool)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _valued(h: dict, price, quantity, name: str) -> dict:
    """
    One holding with its valuation. If it can't be valued (no price, or an unreadable quantity)
    the value and P&L are None and valuation_status says why. They are never 0: a holding with
    no price is not worth nothing, and "worth 0" would read as a total loss.
    """
    cost_basis = _num(h.get("cost_basis_usd")) or 0.0
    if quantity is None or quantity < 0:
        status = "invalid_quantity"
    elif price is None:
        status = "no_price"
    else:
        status = "ok"

    if status != "ok":
        return {**h, "name": name, "current_price": price, "current_value_usd": None,
                "unrealised_pnl_usd": None, "unrealised_pnl_pct": None, "valuation_status": status}

    value = round(price * quantity, 2)
    return {
        **h,
        "name": name,
        "current_price": price,
        "current_value_usd": value,
        "unrealised_pnl_usd": round(value - cost_basis, 2),
        "unrealised_pnl_pct": round(((value - cost_basis) / cost_basis) * 100, 2) if cost_basis else None,
        "valuation_status": "ok",
    }


def get_valued_holdings(user_id) -> list[dict]:
    """
    Returns each holding enriched with current_price, current_value_usd,
    and unrealised_pnl_usd (crypto only — NFT cost basis is in ETH terms
    at buy time, so P&L needs the ETH/USD rate at buy time vs now, which
    isn't tracked live yet; NFT holdings get current_value_usd only).

    Every holding carries valuation_status: "ok", or why it couldn't be valued ("no_price" —
    no market row or a null price; "invalid_quantity"; "unsupported_type"). Stored numbers are
    cleaned first, so a bad value in the database (say a quantity saved as text) can't raise.
    """
    holdings = get_portfolio_holdings(user_id)

    # Everything the holdings need, fetched once for all of them (not per holding).
    symbols = [h.get("symbol", "") for h in holdings if h.get("asset_type") == "crypto"]
    slugs = [h.get("nft_collection_slug", "") for h in holdings if h.get("asset_type") == "nft"]
    price_by_asset = {k: _num(m.get("price")) for k, m in get_asset_market_data_latest_by_id(symbols).items()}
    assets_meta = get_assets_by_id(symbols)
    nft_markets = get_nft_market_data_latest_by_slug(slugs)
    collections_meta = get_nft_collections_by_slug(slugs)

    valued = []
    for raw in holdings:
        h = {**raw, **{f: _num(raw.get(f)) for f in _NUMERIC_FIELDS if f in raw}}

        if h.get("asset_type") == "crypto":
            symbol = (h.get("symbol") or "").upper()   # older rows may have stored "btc"
            asset_meta = assets_meta.get(symbol, {})
            valued.append(_valued(h, price_by_asset.get(symbol), h.get("quantity"), asset_meta.get("name", symbol)))
        elif h.get("asset_type") == "nft":
            slug = h.get("nft_collection_slug", "")
            nft_market = nft_markets.get(slug, {})
            collection_meta = collections_meta.get(slug, {})
            quantity = h["quantity"] if "quantity" in h else 1.0
            valued.append(_valued(h, _num(nft_market.get("floor_usd")), quantity, collection_meta.get("name", slug)))
        else:
            valued.append({**h, "current_price": None, "current_value_usd": None,
                           "unrealised_pnl_usd": None, "unrealised_pnl_pct": None,
                           "valuation_status": "unsupported_type"})

    return valued


def get_total_portfolio_value(user_id):
    """
    Total USD value of the user's holdings, or None if any holding couldn't be valued. A total
    that silently leaves a holding out would look like a drop, so callers that store it (the
    daily snapshots) must skip None rather than record it.
    """
    valued = get_valued_holdings(user_id)
    if any(h["valuation_status"] != "ok" for h in valued):
        return None
    return round(sum(h["current_value_usd"] for h in valued), 2)