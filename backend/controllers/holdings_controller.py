"""
backend/controllers/holdings_controller.py

Every change to a holding goes through here, so that:
  - targets are normalised (crypto symbols upper-case, NFT slugs lower-case) and must exist;
  - the cost basis is always computed by the server from quantity x price, never typed in;
  - adding an asset the user already holds merges into that holding (weighted average price)
    instead of creating a duplicate row;
  - each change is written to `portfolio_transactions` (buy, sell, adjust, remove), which is the
    holding's history and the record of realised profit/loss on sells.

Concurrency (audit G-35): every change to a holding is ONE atomic MongoDB update (a pipeline
`find_one_and_update` or a `find_one_and_delete`), so two requests racing on the same holding can't
lose an update or oversell. The compose database is a standalone mongod with no transactions, so
the history row in `portfolio_transactions` is written after the holding changes. Duplicate rows
are prevented by partial unique indexes (db/indexes.py); run `python -m db.normalize_holdings`
once before those indexes are first built on an existing database.

Cost method: average cost. A sell keeps the average buy price and reduces the cost basis in
proportion to the quantity sold; realised P&L = (sell price - average buy price) x quantity.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

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


# ── atomic update pipelines ──────────────────────────────────────────────────
# Each is an aggregation-pipeline update: MongoDB evaluates it against the stored document inside
# the same atomic write, so the arithmetic always starts from the quantity that is really stored.

def _is_null(field: str) -> dict:
    """True when the field is missing or null."""
    return {"$eq": [{"$ifNull": [field, None]}, None]}


def _cost_basis_stage(now) -> dict:
    """Recomputes cost_basis_usd from the stored quantity and prices; same rules as cost_basis()."""
    crypto = {"$cond": [_is_null("$avg_buy_price_usd"), None,
                        {"$round": [{"$multiply": ["$quantity", "$avg_buy_price_usd"]}, 2]}]}
    nft = {"$cond": [
        {"$and": [{"$not": [_is_null("$avg_buy_price_eth")]},
                  {"$gt": [{"$ifNull": ["$avg_buy_eth_usd_rate", 0]}, 0]}]},
        {"$round": [{"$multiply": ["$quantity", "$avg_buy_price_eth", "$avg_buy_eth_usd_rate"]}, 2]},
        None,
    ]}
    return {"$set": {"cost_basis_usd": {"$cond": [{"$eq": ["$asset_type", "crypto"]}, crypto, nft]},
                     "updated_at": now}}


def _buy_pipeline(quantity: float, price, now) -> list:
    """Adds `quantity` at `price` (weighted average). No known price keeps the stored average; a
    holding with no stored average takes the buy price."""
    old_qty = {"$ifNull": ["$quantity", 0]}
    if price is None:
        new_avg = {"$ifNull": ["$avg_buy_price_usd", None]}
    else:
        new_avg = {"$cond": [
            _is_null("$avg_buy_price_usd"), price,
            {"$divide": [{"$add": [{"$multiply": [old_qty, "$avg_buy_price_usd"]}, quantity * price]},
                         {"$add": [old_qty, quantity]}]},
        ]}
    return [{"$set": {"quantity": {"$add": [old_qty, quantity]}, "avg_buy_price_usd": new_avg}},
            _cost_basis_stage(now)]


def _sell_pipeline(quantity: float, now) -> list:
    return [{"$set": {"quantity": {"$max": [0, {"$subtract": ["$quantity", quantity]}]}}},
            _cost_basis_stage(now)]


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
        flt = {"user_id": user_id, "asset_type": "crypto", **target}
        doc = {"asset_type": "crypto", **target, "quantity": qty, "avg_buy_price_usd": price,
               "cost_basis_usd": cost_basis("crypto", qty, price)}
        doc = {k: v for k, v in doc.items() if v is not None}
        doc.update({"user_id": user_id, "date_added": now, "updated_at": now})
        # Merge into the row if there is one, else insert. If a concurrent request inserts the row
        # between the two (the partial unique index rejects the second insert), merge on the next pass.
        for _ in range(3):
            merged = db.portfolio_holdings.find_one_and_update(
                flt, _buy_pipeline(qty, price, now), return_document=ReturnDocument.AFTER)
            if merged:
                _record(user_id, merged, "buy", quantity=qty, price_usd=price,
                        quantity_after=merged.get("quantity"),
                        avg_buy_price_usd_after=merged.get("avg_buy_price_usd"),
                        note="merged into existing holding")
                return {"id": str(merged["_id"]), "merged": True}
            try:
                result = db.portfolio_holdings.insert_one(dict(doc))
            except DuplicateKeyError:
                continue
            doc["_id"] = result.inserted_id
            _record(user_id, doc, "buy", quantity=qty, price_usd=price,
                    price_eth=None, eth_usd_rate=None, quantity_after=qty)
            return {"id": str(result.inserted_id), "merged": False}
        raise HTTPException(status_code=409, detail="That holding changed while you were adding to it. Try again.")

    token = str(payload.get("nft_token_id") or "").strip()
    if not token:
        raise HTTPException(status_code=422, detail="nft_token_id is required for nft holdings.")
    already = HTTPException(status_code=409, detail=f"Token #{token} is already in your portfolio.")
    if db.portfolio_holdings.find_one({"user_id": user_id, "asset_type": "nft", **target, "nft_token_id": token}):
        raise already
    avg_eth, rate = payload.get("avg_buy_price_eth"), payload.get("avg_buy_eth_usd_rate")
    doc = {"asset_type": "nft", **target, "nft_token_id": token, "quantity": qty,
           "avg_buy_price_eth": avg_eth, "avg_buy_eth_usd_rate": rate,
           "cost_basis_usd": cost_basis("nft", qty, avg_eth=avg_eth, eth_rate=rate)}
    doc = {k: v for k, v in doc.items() if v is not None}
    doc.update({"user_id": user_id, "date_added": now, "updated_at": now})
    try:
        result = db.portfolio_holdings.insert_one(doc)
    except DuplicateKeyError:
        raise already          # a concurrent add of the same token won the race
    doc["_id"] = result.inserted_id
    _record(user_id, doc, "buy", quantity=qty, price_usd=None,
            price_eth=doc.get("avg_buy_price_eth"), eth_usd_rate=doc.get("avg_buy_eth_usd_rate"),
            quantity_after=qty)
    return {"id": str(result.inserted_id), "merged": False}


# ── correct (PATCH) ──────────────────────────────────────────────────────────

def correct_holding(user_id, holding_id: str, patch: dict) -> None:
    """A correction to what was recorded. Cost basis is recomputed in the same atomic update;
    before/after go in the history."""
    h = get_db().portfolio_holdings.find_one_and_update(
        {"_id": ObjectId(holding_id), "user_id": user_id},
        [{"$set": {k: {"$literal": v} for k, v in patch.items()}}, _cost_basis_stage(_now())],
        return_document=ReturnDocument.BEFORE)
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
    merged = {**h, **patch}
    new_cost = cost_basis(h["asset_type"], merged.get("quantity"), merged.get("avg_buy_price_usd"),
                          merged.get("avg_buy_price_eth"), merged.get("avg_buy_eth_usd_rate"))
    fields = list(patch)
    _record(user_id, h, "adjust",
            before={f: h.get(f) for f in fields + ["cost_basis_usd"]},
            after={**{f: merged.get(f) for f in fields}, "cost_basis_usd": new_cost})


# ── trade (buy / sell more of a crypto holding) ──────────────────────────────

def _trade_refused(user_id, oid, kind: str, quantity: float):
    """The atomic update matched nothing; work out why (not yours, not crypto, or not enough)."""
    h = get_db().portfolio_holdings.find_one({"_id": oid, "user_id": user_id})
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
    if h.get("asset_type") != "crypto":
        raise HTTPException(status_code=422, detail="Buys and sells can be recorded for crypto holdings only.")
    if kind == "sell":
        raise HTTPException(status_code=422,
                            detail=f"You hold {float(h.get('quantity') or 0):g}; you can't sell {quantity:g}.")
    raise HTTPException(status_code=409, detail="That holding changed while you were updating it. Try again.")


def trade(user_id, holding_id: str, kind: str, quantity: float, price_usd: float) -> dict:
    db = get_db()
    oid = ObjectId(holding_id)
    now = _now()
    mine = {"_id": oid, "user_id": user_id, "asset_type": "crypto"}

    if kind == "buy":
        h = db.portfolio_holdings.find_one_and_update(
            mine, _buy_pipeline(quantity, price_usd, now), return_document=ReturnDocument.AFTER)
        if not h:
            _trade_refused(user_id, oid, kind, quantity)
        new_qty, new_avg = float(h["quantity"]), h.get("avg_buy_price_usd")
        _record(user_id, h, "buy", quantity=quantity, price_usd=price_usd,
                quantity_after=new_qty, avg_buy_price_usd_after=new_avg)
        return {"status": "bought", "quantity": new_qty, "closed": False}

    # sell: only matches while the stored quantity still covers it, so two sells can't both pass
    h = db.portfolio_holdings.find_one_and_update(
        {**mine, "quantity": {"$gte": quantity - _EPS}}, _sell_pipeline(quantity, now),
        return_document=ReturnDocument.AFTER)
    if not h:
        _trade_refused(user_id, oid, kind, quantity)
    avg = h.get("avg_buy_price_usd")     # a sell never changes the average
    new_qty = float(h["quantity"])
    realised = _round((price_usd - avg) * quantity) if avg is not None else None
    closed = False
    if new_qty <= _EPS:
        # Fully sold: drop the row (the history stays). The quantity filter means a buy that landed
        # since the update keeps the holding alive instead of deleting it.
        closed = db.portfolio_holdings.delete_one(
            {"_id": oid, "user_id": user_id, "quantity": {"$lte": _EPS}}).deleted_count == 1
        if not closed:
            again = db.portfolio_holdings.find_one({"_id": oid, "user_id": user_id})
            new_qty = float(again["quantity"]) if again else 0.0
            closed = again is None
    if closed:
        new_qty = 0.0
    _record(user_id, h, "sell", quantity=quantity, price_usd=price_usd, realised_pnl_usd=realised,
            avg_buy_price_usd=avg, quantity_after=new_qty)
    return {"status": "sold", "quantity": new_qty, "closed": closed, "realised_pnl_usd": realised}


# ── remove ───────────────────────────────────────────────────────────────────

def remove_holding(user_id, holding_id: str) -> None:
    h = get_db().portfolio_holdings.find_one_and_delete({"_id": ObjectId(holding_id), "user_id": user_id})
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found.")
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
