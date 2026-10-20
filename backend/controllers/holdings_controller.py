"""
backend/controllers/holdings_controller.py

Every change to a holding goes through here, so that:
  - targets are normalised (crypto symbols upper-case, NFT slugs lower-case) and must exist;
  - the cost basis is always computed by the server from quantity x price, never typed in;
  - adding an asset the user already holds merges into that holding (weighted average price)
    instead of creating a duplicate row;
  - each change is written to `portfolio_transactions` (buy, sell, adjust, remove), which is the
    holding's history and the record of realised profit/loss on sells.

Cost method: average cost. A sell keeps the average buy price and reduces the cost basis in
proportion to the quantity sold; realised P&L = (sell price - average buy price) x quantity.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from db.mongo_connection import get_db

_EPS = 1e-12


def _now():
    return datetime.now(timezone.utc)


def _round(v):
    return round(v, 2) if v is not None else None


def normalise_target(asset_type: str, symbol: str | None, slug: str | None) -> dict:
    """{"symbol": "BTC"} or {"nft_collection_slug": "punks"}, checked against the covered universe."""
    db = get_db()
    if asset_type == "crypto":
        sym = (symbol or "").strip().upper()
        if not sym:
            raise HTTPException(status_code=422, detail="symbol is required for crypto holdings.")
        if not db.assets.find_one({"asset_id": sym}, {"_id": 1}):
            raise HTTPException(status_code=404, detail=f"Asset '{sym}' isn't covered.")
        return {"symbol": sym}
    if asset_type == "nft":
        s = (slug or "").strip().lower()
        if not s:
            raise HTTPException(status_code=422, detail="nft_collection_slug is required for nft holdings.")
        if not db.nft_collections.find_one({"slug": s}, {"_id": 1}):
            raise HTTPException(status_code=404, detail=f"NFT collection '{s}' isn't covered.")
        return {"nft_collection_slug": s}
    raise HTTPException(status_code=422, detail="asset_type must be 'crypto' or 'nft'.")


def cost_basis(asset_type: str, quantity, avg_usd=None, avg_eth=None, eth_rate=None):
    """USD cost basis from the numbers, or None when it can't be worked out (an NFT with no ETH/USD rate)."""
    if quantity is None:
        return None
    if asset_type == "crypto":
        return _round(quantity * avg_usd) if avg_usd is not None else None
    if avg_eth is not None and eth_rate:
        return _round(quantity * avg_eth * eth_rate)
    return None


def _record(user_id, holding: dict, kind: str, **fields):
    get_db().portfolio_transactions.insert_one({
        "user_id": user_id,
        "holding_id": str(holding["_id"]),
        "asset_type": holding.get("asset_type"),
        "symbol": holding.get("symbol"),
        "nft_collection_slug": holding.get("nft_collection_slug"),
        "nft_token_id": holding.get("nft_token_id"),
        "type": kind,
        "timestamp": _now(),
        **fields,
    })


def _owned(user_id, holding_id: str) -> dict:
    h = get_db().portfolio_holdings.find_one({"_id": ObjectId(holding_id), "user_id": user_id})
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
    return h


# ── add (or merge) ───────────────────────────────────────────────────────────

def add_holding(user_id, payload: dict) -> dict:
    """Returns {"id", "merged"}. Crypto already held -> merged; the same NFT token twice -> 409."""
    db = get_db()
    asset_type = payload["asset_type"]
    target = normalise_target(asset_type, payload.get("symbol"), payload.get("nft_collection_slug"))
    qty = payload["quantity"]
    now = _now()

    if asset_type == "crypto":
        price = payload.get("avg_buy_price_usd")
        existing = db.portfolio_holdings.find_one({"user_id": user_id, "asset_type": "crypto", **target})
        if existing:
            old_qty = float(existing.get("quantity") or 0)
            old_avg = existing.get("avg_buy_price_usd")
            new_qty = old_qty + qty
            # Weighted average when both prices are known; otherwise keep whichever exists.
            if old_avg is not None and price is not None:
                new_avg = (old_qty * old_avg + qty * price) / new_qty
            else:
                new_avg = price if price is not None else old_avg
            update = {"quantity": new_qty, "avg_buy_price_usd": new_avg,
                      "cost_basis_usd": cost_basis("crypto", new_qty, new_avg), "updated_at": now}
            db.portfolio_holdings.update_one({"_id": existing["_id"]}, {"$set": update})
            _record(user_id, existing, "buy", quantity=qty, price_usd=price,
                    quantity_after=new_qty, avg_buy_price_usd_after=new_avg, note="merged into existing holding")
            return {"id": str(existing["_id"]), "merged": True}

        doc = {"asset_type": "crypto", **target, "quantity": qty, "avg_buy_price_usd": price,
               "cost_basis_usd": cost_basis("crypto", qty, price)}
    else:
        token = str(payload.get("nft_token_id") or "").strip()
        if not token:
            raise HTTPException(status_code=422, detail="nft_token_id is required for nft holdings.")
        if db.portfolio_holdings.find_one({"user_id": user_id, "asset_type": "nft", **target, "nft_token_id": token}):
            raise HTTPException(status_code=409, detail=f"Token #{token} is already in your portfolio.")
        avg_eth, rate = payload.get("avg_buy_price_eth"), payload.get("avg_buy_eth_usd_rate")
        doc = {"asset_type": "nft", **target, "nft_token_id": token, "quantity": qty,
               "avg_buy_price_eth": avg_eth, "avg_buy_eth_usd_rate": rate,
               "cost_basis_usd": cost_basis("nft", qty, avg_eth=avg_eth, eth_rate=rate)}

    doc = {k: v for k, v in doc.items() if v is not None}
    doc.update({"user_id": user_id, "date_added": now, "updated_at": now})
    result = db.portfolio_holdings.insert_one(doc)
    doc["_id"] = result.inserted_id
    _record(user_id, doc, "buy", quantity=qty, price_usd=doc.get("avg_buy_price_usd"),
            price_eth=doc.get("avg_buy_price_eth"), eth_usd_rate=doc.get("avg_buy_eth_usd_rate"),
            quantity_after=qty)
    return {"id": str(result.inserted_id), "merged": False}


# ── correct (PATCH) ──────────────────────────────────────────────────────────

def correct_holding(user_id, holding_id: str, patch: dict) -> None:
    """A correction to what was recorded. Cost basis is recomputed; before/after go in the history."""
    db = get_db()
    h = _owned(user_id, holding_id)
    merged = {**h, **patch}
    new_cost = cost_basis(h["asset_type"], merged.get("quantity"), merged.get("avg_buy_price_usd"),
                          merged.get("avg_buy_price_eth"), merged.get("avg_buy_eth_usd_rate"))
    update = {**patch, "cost_basis_usd": new_cost, "updated_at": _now()}
    db.portfolio_holdings.update_one({"_id": h["_id"]}, {"$set": update})
    fields = list(patch)
    _record(user_id, h, "adjust",
            before={f: h.get(f) for f in fields + ["cost_basis_usd"]},
            after={**{f: merged.get(f) for f in fields}, "cost_basis_usd": new_cost})


# ── trade (buy / sell more of a crypto holding) ──────────────────────────────

def trade(user_id, holding_id: str, kind: str, quantity: float, price_usd: float) -> dict:
    db = get_db()
    h = _owned(user_id, holding_id)
    if h.get("asset_type") != "crypto":
        raise HTTPException(status_code=422, detail="Buys and sells can be recorded for crypto holdings only.")
    qty = float(h.get("quantity") or 0)
    avg = h.get("avg_buy_price_usd")

    if kind == "buy":
        new_qty = qty + quantity
        new_avg = (qty * avg + quantity * price_usd) / new_qty if avg is not None else price_usd
        db.portfolio_holdings.update_one({"_id": h["_id"]}, {"$set": {
            "quantity": new_qty, "avg_buy_price_usd": new_avg,
            "cost_basis_usd": cost_basis("crypto", new_qty, new_avg), "updated_at": _now()}})
        _record(user_id, h, "buy", quantity=quantity, price_usd=price_usd,
                quantity_after=new_qty, avg_buy_price_usd_after=new_avg)
        return {"status": "bought", "quantity": new_qty, "closed": False}

    # sell
    if quantity > qty + _EPS:
        raise HTTPException(status_code=422, detail=f"You hold {qty:g}; you can't sell {quantity:g}.")
    new_qty = max(qty - quantity, 0.0)
    realised = _round((price_usd - avg) * quantity) if avg is not None else None
    _record(user_id, h, "sell", quantity=quantity, price_usd=price_usd, realised_pnl_usd=realised,
            avg_buy_price_usd=avg, quantity_after=new_qty)
    if new_qty <= _EPS:
        db.portfolio_holdings.delete_one({"_id": h["_id"]})   # fully sold: the history stays
        return {"status": "sold", "quantity": 0.0, "closed": True, "realised_pnl_usd": realised}
    db.portfolio_holdings.update_one({"_id": h["_id"]}, {"$set": {
        "quantity": new_qty, "cost_basis_usd": cost_basis("crypto", new_qty, avg), "updated_at": _now()}})
    return {"status": "sold", "quantity": new_qty, "closed": False, "realised_pnl_usd": realised}


# ── remove ───────────────────────────────────────────────────────────────────

def remove_holding(user_id, holding_id: str) -> None:
    db = get_db()
    h = _owned(user_id, holding_id)
    db.portfolio_holdings.delete_one({"_id": h["_id"]})
    _record(user_id, h, "remove", quantity=h.get("quantity"), cost_basis_usd=h.get("cost_basis_usd"))


# ── history ──────────────────────────────────────────────────────────────────

def list_transactions(user_id, holding_id: str | None = None, limit: int = 100) -> list:
    query = {"user_id": user_id}
    if holding_id:
        query["holding_id"] = holding_id
    rows = get_db().portfolio_transactions.find(query, sort=[("timestamp", -1)], limit=limit)
    out = []
    for r in rows:
        r["id"] = str(r.pop("_id"))
        r.pop("user_id", None)
        ts = r.get("timestamp")
        if hasattr(ts, "strftime"):
            r["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(r)
    return out
