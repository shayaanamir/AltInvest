import re
from db.mongo_connection import get_db
from datetime import datetime, timezone
from bson import ObjectId

def get_latest_price(asset: str) -> dict | None:
    db = get_db()
    return db.prices.find_one(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0}
    )

def get_price_history(asset: str, days: int = 365) -> list:
    db = get_db()
    cursor = db.prices.find(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        limit=days,
        projection={"_id": 0}
    )
    return list(cursor)

def get_latest_sentiment(asset: str) -> dict | None:
    db = get_db()
    return db.sentiment.find_one(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        projection={"_id": 0}
    )

def get_latest_prediction(asset: str) -> dict | None:
    db = get_db()
    return db.predictions.find_one(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0}
    )

def get_latest_risk(asset: str) -> dict | None:
    db = get_db()
    return db.risk_scores.find_one(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0}
    )

def get_supported_assets() -> list:
    db = get_db()
    return list(db.assets.find({}, projection={"_id": 0}))

def upsert_aai_score(asset: str, payload: dict) -> None:
    db = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    db.aai_scores.update_one(
        {"asset": asset.upper(), "date": today},
        {"$set": payload},
        upsert=True
    )

def _latest_rows(collection: str, key: str, match: dict | None = None) -> list:
    """
    The newest row per `key` value. Sorting on (key, timestamp desc) matches the
    (key, timestamp) index in db/indexes.py, so MongoDB reads the first index entry per key
    instead of sorting the whole collection in memory. allowDiskUse is a safety net only.
    """
    db = get_db()
    pipeline = ([{"$match": match}] if match else []) + [
        {"$sort": {key: 1, "timestamp": -1}},
        {"$group": {"_id": f"${key}", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return list(db[collection].aggregate(pipeline, allowDiskUse=True))


def _latest_per_key(collection: str, key: str) -> dict:
    """{key_value: latest_doc} for collections keyed by a field + timestamp."""
    return {d[key]: d for d in _latest_rows(collection, key)}


def get_all_latest_predictions() -> dict:
    return _latest_per_key("predictions", "asset")


def get_all_latest_risk_scores() -> dict:
    return _latest_per_key("risk_scores", "asset")


def get_all_latest_risk_breakdowns() -> dict:
    return _latest_per_key("risk_breakdown", "asset")


def get_all_latest_nft_liquidity() -> dict:
    return _latest_per_key("nft_liquidity", "slug")


def get_daily_price_series(asset: str, days: int) -> list:
    """
    Oldest-first [{date: 'YYYY-MM-DD', price}] — last hourly price of each UTC day
    over the last `days` days. `prices` is hourly, so this caps the scan.
    """
    db = get_db()
    rows = db.prices.find(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        limit=(days + 1) * 24,
        projection={"_id": 0, "timestamp": 1, "price": 1},
    )
    by_day: dict[str, float] = {}
    for r in rows:  # newest first, so the first hit per day is that day's close
        ts = r["timestamp"]
        day = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        by_day.setdefault(day, r["price"])
    return [{"date": d, "price": by_day[d]} for d in sorted(by_day)][-(days + 1):]


def get_price_sparklines(assets: list[str], hours: int = 168, points: int = 28) -> dict:
    """{ASSET: [price, ...]} — the last `hours` of hourly prices, thinned to ~`points`."""
    db = get_db()
    symbols = sorted({a.upper() for a in assets})
    by_asset: dict[str, list] = {s: [] for s in symbols}
    if symbols:
        # The last `hours` rows of every asset in one aggregation (was one query per asset),
        # walking the (asset, timestamp) index newest-first; reversed to oldest-first below.
        for g in db.prices.aggregate([
            {"$match": {"asset": {"$in": symbols}}},
            {"$sort": {"asset": 1, "timestamp": -1}},
            {"$group": {"_id": "$asset", "prices": {"$firstN": {"input": "$price", "n": hours}}}},
        ]):
            by_asset[g["_id"]] = list(reversed(g["prices"]))
    step = max(1, hours // points)
    return {s: (series[::step] if len(series) > points else series) for s, series in by_asset.items()}


def get_user_flags(user_id) -> dict:
    """
    {"held": {...}, "watching": {...}} keyed by crypto symbol / nft slug, from
    the user's portfolio_holdings and watchlists. Empty sets for anonymous callers.
    """
    held: set[str] = set()
    watching: set[str] = set()
    if user_id is None:
        return {"held": held, "watching": watching}
    db = get_db()
    for h in db.portfolio_holdings.find({"user_id": user_id}, projection={"symbol": 1, "nft_collection_slug": 1}):
        key = h.get("symbol") or h.get("nft_collection_slug")
        if key:
            held.add(key)
    for w in db.watchlists.find({"user_id": user_id}, projection={"items": 1}):
        for it in w.get("items", []):
            if it.get("symbol_or_slug"):
                watching.add(it["symbol_or_slug"])
    return {"held": held, "watching": watching}


def get_user_by_email(email: str) -> dict | None:
    db = get_db()
    return db.users.find_one({"email": email.lower().strip()})


# ── Assets / market data ─────────────────────────────────────────────────────

def get_asset(asset_id: str) -> dict | None:
    db = get_db()
    return db.assets.find_one({"asset_id": asset_id.upper()}, projection={"_id": 0})


def get_assets_by_id(asset_ids) -> dict:
    """{ASSET_ID: asset_doc} for many assets in one query."""
    ids = sorted({a.upper() for a in asset_ids if a})
    if not ids:
        return {}
    return {d["asset_id"]: d for d in get_db().assets.find({"asset_id": {"$in": ids}}, projection={"_id": 0})}


def get_asset_market_data_latest_by_id(asset_ids) -> dict:
    """{ASSET_ID: latest asset_market_data row} for many assets in one aggregation."""
    ids = sorted({a.upper() for a in asset_ids if a})
    if not ids:
        return {}
    return {d["asset_id"]: d for d in _latest_rows("asset_market_data", "asset_id", {"asset_id": {"$in": ids}})}


def get_asset_market_data_latest(asset_id: str) -> dict | None:
    db = get_db()
    return db.asset_market_data.find_one(
        {"asset_id": asset_id.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0},
    )


def get_asset_market_data_all_latest() -> list:
    """One latest snapshot per asset — used by dashboard/discover/trending."""
    return _latest_rows("asset_market_data", "asset_id")


def get_prediction_history(asset: str, days: int = 30) -> list:
    db = get_db()
    cursor = db.predictions.find(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        limit=days,
        projection={"_id": 0},
    )
    return list(cursor)


def get_latest_risk_breakdown(asset: str) -> dict | None:
    db = get_db()
    return db.risk_breakdown.find_one(
        {"asset": asset.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0},
    )


def get_latest_aai_score(target_type: str, target_id: str) -> dict | None:
    db = get_db()
    return db.aai_scores.find_one(
        {"target_type": target_type, "target_id": target_id},
        sort=[("timestamp", -1)],
        projection={"_id": 0},
    )


# ── Market insights / themes ─────────────────────────────────────────────────

def get_market_insights(limit: int = 6, asset_symbol: str | None = None,
                         nft_slug: str | None = None) -> list:
    db = get_db()
    query = {}
    if asset_symbol:
        query["related_asset_symbol"] = asset_symbol.upper()
    if nft_slug:
        query["related_nft_slug"] = nft_slug
    cursor = db.market_insights.find(
        query, sort=[("published_at", -1)], limit=limit, projection={"_id": 0}
    )
    return list(cursor)


def get_sentiment_themes() -> list:
    db = get_db()
    return list(db.sentiment_themes.find({}, projection={"_id": 0}))


# ── Portfolio ─────────────────────────────────────────────────────────────────

def get_portfolio_holdings(user_id: ObjectId) -> list:
    db = get_db()
    cursor = db.portfolio_holdings.find({"user_id": user_id})
    out = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc["user_id"] = str(doc["user_id"])
        out.append(doc)
    return out


def get_portfolio_snapshots(user_id: ObjectId, days: int = 365) -> list:
    db = get_db()
    cursor = db.portfolio_snapshots.find(
        {"user_id": user_id}, sort=[("snapshot_date", -1)], limit=days,
        projection={"_id": 0},
    )
    return list(cursor)


# ── Watchlists ────────────────────────────────────────────────────────────────

def get_watchlists(user_id: ObjectId) -> list:
    db = get_db()
    out = []
    for doc in db.watchlists.find({"user_id": user_id}):
        doc["id"] = str(doc.pop("_id"))
        doc["user_id"] = str(doc["user_id"])
        out.append(doc)
    return out


def create_watchlist(user_id: ObjectId, name: str, items: list | None = None) -> str:
    """Creates the list with its starter items in one write, so it can't half-succeed."""
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id, "name": name, "created_at": now,
        "items": [{"type": t, "symbol_or_slug": k, "added_at": now} for t, k in (items or [])],
    }
    result = db.watchlists.insert_one(doc)
    return str(result.inserted_id)


def rename_watchlist(user_id: ObjectId, watchlist_id: str, name: str) -> bool:
    db = get_db()
    result = db.watchlists.update_one({"_id": ObjectId(watchlist_id), "user_id": user_id}, {"$set": {"name": name}})
    return result.matched_count > 0


def watchlist_name_taken(user_id: ObjectId, name: str, except_id: str | None = None) -> bool:
    db = get_db()
    query = {"user_id": user_id, "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
    if except_id:
        query["_id"] = {"$ne": ObjectId(except_id)}
    return db.watchlists.find_one(query, {"_id": 1}) is not None


def delete_watchlist(user_id: ObjectId, watchlist_id: str) -> bool:
    db = get_db()
    result = db.watchlists.delete_one({"_id": ObjectId(watchlist_id), "user_id": user_id})
    return result.deleted_count > 0


def add_watchlist_item(user_id: ObjectId, watchlist_id: str, item_type: str, symbol_or_slug: str) -> str:
    """
    Adds an item unless it's already on the list. Returns "added", "duplicate" or "no_list".
    The duplicate check is part of the update's filter, so two quick clicks can't add it twice.
    """
    db = get_db()
    oid = ObjectId(watchlist_id)
    item = {"type": item_type, "symbol_or_slug": symbol_or_slug, "added_at": datetime.now(timezone.utc)}
    result = db.watchlists.update_one(
        {"_id": oid, "user_id": user_id, "items.symbol_or_slug": {"$ne": symbol_or_slug}},
        {"$push": {"items": item}},
    )
    if result.matched_count:
        return "added"
    return "duplicate" if db.watchlists.find_one({"_id": oid, "user_id": user_id}, {"_id": 1}) else "no_list"


def remove_watchlist_item(user_id: ObjectId, watchlist_id: str, symbol_or_slug: str) -> str:
    """Returns "removed", "no_item" or "no_list". Matches the item whatever case it was stored in."""
    db = get_db()
    oid = ObjectId(watchlist_id)
    variants = sorted({symbol_or_slug, symbol_or_slug.upper(), symbol_or_slug.lower()})
    result = db.watchlists.update_one(
        {"_id": oid, "user_id": user_id},
        {"$pull": {"items": {"symbol_or_slug": {"$in": variants}}}},
    )
    if not result.matched_count:
        return "no_list"
    return "removed" if result.modified_count else "no_item"


# ── Alerts ────────────────────────────────────────────────────────────────────

def get_alerts(user_id: ObjectId, status: str | None = None) -> list:
    db = get_db()
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    out = []
    for doc in db.alerts.find(query, sort=[("created_at", -1)]):
        doc["id"] = str(doc.pop("_id"))
        doc["user_id"] = str(doc["user_id"])
        out.append(doc)
    return out


def create_alert(user_id: ObjectId, payload: dict) -> str:
    db = get_db()
    doc = {
        **payload, "user_id": user_id, "status": "active",
        "created_at": datetime.now(timezone.utc),
        "last_triggered_at": None, "last_observed_value": None,
    }
    result = db.alerts.insert_one(doc)
    return str(result.inserted_id)


def update_alert(user_id: ObjectId, alert_id: str, payload: dict) -> bool:
    db = get_db()
    result = db.alerts.update_one(
        {"_id": ObjectId(alert_id), "user_id": user_id}, {"$set": payload}
    )
    return result.matched_count > 0


def delete_alert(user_id: ObjectId, alert_id: str) -> bool:
    db = get_db()
    result = db.alerts.delete_one({"_id": ObjectId(alert_id), "user_id": user_id})
    return result.deleted_count > 0


# ── Notifications ─────────────────────────────────────────────────────────────

def get_notifications(user_id: ObjectId, unread_only: bool = False, limit: int = 50) -> list:
    db = get_db()
    query = {"user_id": user_id}
    if unread_only:
        query["read"] = False
    out = []
    for doc in db.notifications.find(query, sort=[("timestamp", -1)], limit=limit):
        doc["id"] = str(doc.pop("_id"))
        doc["user_id"] = str(doc["user_id"])
        out.append(doc)
    return out


def mark_notification_read(user_id: ObjectId, notification_id: str) -> bool:
    db = get_db()
    result = db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user_id}, {"$set": {"read": True}}
    )
    return result.matched_count > 0


# ── NFT ───────────────────────────────────────────────────────────────────────

def get_nft_collections() -> list:
    db = get_db()
    return list(db.nft_collections.find({}, projection={"_id": 0}))


def get_nft_collection(slug: str) -> dict | None:
    db = get_db()
    return db.nft_collections.find_one({"slug": slug}, projection={"_id": 0})


def get_nft_collections_by_slug(slugs) -> dict:
    """{slug: collection_doc} for many collections in one query."""
    wanted = sorted({x for x in slugs if x})
    if not wanted:
        return {}
    return {d["slug"]: d for d in get_db().nft_collections.find({"slug": {"$in": wanted}}, projection={"_id": 0})}


def get_nft_market_data_latest_by_slug(slugs) -> dict:
    """{slug: latest nft_market_data row} for many collections in one aggregation."""
    wanted = sorted({x for x in slugs if x})
    if not wanted:
        return {}
    return {d["slug"]: d for d in _latest_rows("nft_market_data", "slug", {"slug": {"$in": wanted}})}


def get_nft_market_data_latest(slug: str) -> dict | None:
    db = get_db()
    return db.nft_market_data.find_one(
        {"slug": slug}, sort=[("timestamp", -1)], projection={"_id": 0}
    )


def get_nft_market_data_all_latest() -> list:
    return _latest_rows("nft_market_data", "slug")


def get_nft_sales(slug: str, limit: int = 20) -> list:
    db = get_db()
    cursor = db.nft_sales.find(
        {"slug": slug}, sort=[("timestamp", -1)], limit=limit, projection={"_id": 0}
    )
    return list(cursor)


def get_nft_holder_stats(slug: str) -> dict | None:
    db = get_db()
    return db.nft_holder_stats.find_one(
        {"slug": slug}, sort=[("timestamp", -1)], projection={"_id": 0}
    )


def get_nft_liquidity(slug: str) -> dict | None:
    db = get_db()
    return db.nft_liquidity.find_one(
        {"slug": slug}, sort=[("timestamp", -1)], projection={"_id": 0}
    )


def get_nft_risk_breakdown(slug: str) -> dict | None:
    db = get_db()
    return db.nft_risk_breakdown.find_one(
        {"slug": slug}, sort=[("timestamp", -1)], projection={"_id": 0}
    )


def get_nft_traits(slug: str) -> dict | None:
    db = get_db()
    return db.nft_traits.find_one({"slug": slug}, projection={"_id": 0})


def get_nft_token(slug: str, token_id: str) -> dict | None:
    db = get_db()
    return db.nft_tokens.find_one({"slug": slug, "token_id": token_id}, projection={"_id": 0})


def get_nft_token_sale_history(slug: str, token_id: str) -> list:
    db = get_db()
    cursor = db.nft_token_sale_history.find(
        {"slug": slug, "token_id": token_id}, sort=[("timestamp", -1)], projection={"_id": 0}
    )
    return list(cursor)


def get_nft_token_ownership_history(slug: str, token_id: str) -> list:
    db = get_db()
    cursor = db.nft_token_ownership_history.find(
        {"slug": slug, "token_id": token_id}, sort=[("since", -1)], projection={"_id": 0}
    )
    return list(cursor)


# ── Search / profile / settings ────────────────────────────────────────────────

def search_all(q: str, limit: int = 10) -> dict:
    db = get_db()
    # Matched as literal text: escaping stops the query being run as a regular expression.
    regex = {"$regex": re.escape(q), "$options": "i"}
    assets = list(db.assets.find(
        {"$or": [{"name": regex}, {"symbol": regex}]}, limit=limit, projection={"_id": 0}
    ))
    nfts = list(db.nft_collections.find(
        {"$or": [{"name": regex}, {"symbol": regex}]}, limit=limit, projection={"_id": 0}
    ))
    insights = list(db.market_insights.find(
        {"title": regex}, limit=limit, projection={"_id": 0}
    ))
    return {"assets": assets, "nft_collections": nfts, "insights": insights}


SEARCH_HISTORY_LIMIT = 20   # recent searches kept per user (rows also expire after 90 days, db/indexes.py)


def log_search(user_id: ObjectId, query: str) -> None:
    """Records a search: one row per distinct query (case-insensitive), capped per user."""
    db = get_db()
    query = query.strip()[:200]
    if not query:
        return
    db.user_search_history.update_one(
        {"user_id": user_id, "query_key": query.lower()},
        {"$set": {"query": query, "searched_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    stale = [d["_id"] for d in db.user_search_history.find(
        {"user_id": user_id}, sort=[("searched_at", -1)], skip=SEARCH_HISTORY_LIMIT, projection={"_id": 1},
    )]
    if stale:
        db.user_search_history.delete_many({"_id": {"$in": stale}})


def get_search_history(user_id: ObjectId, limit: int = 10) -> list:
    """The user's most recent distinct searches, newest first."""
    return list(get_db().user_search_history.find(
        {"user_id": user_id}, sort=[("searched_at", -1)], limit=limit,
        projection={"_id": 0, "query": 1, "searched_at": 1},
    ))


def clear_search_history(user_id: ObjectId) -> int:
    return get_db().user_search_history.delete_many({"user_id": user_id}).deleted_count


def get_user_settings(user_id: ObjectId) -> dict | None:
    db = get_db()
    return db.user_settings.find_one({"user_id": user_id}, projection={"_id": 0})



def update_user_settings(user_id: ObjectId, section: str, payload: dict) -> bool:
    """
    Shallow merge: sets each top-level key within `section` individually via
    dot-path, rather than replacing the whole section. E.g. section=
    "notifications", payload={"channels": {"push": False}} only touches
    notifications.channels, leaving notifications.alert_types and
    notifications.quiet_hours untouched.
    """
    db = get_db()
    dot_updates = {f"{section}.{k}": v for k, v in payload.items()}
    result = db.user_settings.update_one(
        {"user_id": user_id}, {"$set": dot_updates}, upsert=True
    )
    return result.matched_count > 0 or result.upserted_id is not None


def create_default_user_settings(user_id: ObjectId) -> None:
    """Seeds a default user_settings doc at signup, mirroring db/seed_user_data.py."""
    db = get_db()
    db.user_settings.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id": user_id,
            "preferences": {
                "display_currency": "USD", "date_format": "MM/DD/YYYY",
                "default_landing_page": "Dashboard", "default_dashboard_layout": "ai-first",
            },
            "appearance": {"theme": "dark", "density": "comfortable"},
            "notifications": {
                "channels": {"inApp": True, "push": True, "email": False},
                "alert_types": {
                    "aaiThresholdOnly": True, "priceAlerts": True, "sentimentShifts": False,
                    "minorPriceWiggles": False, "marketNews": True, "systemMessages": True,
                },
                "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00",
                                 "timezone": "UTC"},
            },
            "security": {"two_factor_enabled": False},
            "connected_accounts": {"google": False, "github": False, "wallet": False},
        }},
        upsert=True,
    )


def get_user_by_id(user_id: str) -> dict | None:
    db = get_db()
    return db.users.find_one({"_id": ObjectId(user_id)})


def create_user(email: str, name: str, password_hash: str) -> str:
    db = get_db()
    doc = {
        "email": email.lower().strip(), "name": name, "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc), "email_verified": False,
        "risk_profile": "balanced", "layout_preference": "ai-first",
        "display_currency": "USD",
        "onboarding": {"completed": False, "completed_at": None, "skipped": False, "answers": {}},
        "bio": None,
    }
    result = db.users.insert_one(doc)
    return str(result.inserted_id)


def upsert_aai_score_generalized(target_type: str, target_id: str, payload: dict) -> None:
    """
    Generalized version of upsert_aai_score() that supports both crypto
    assets and NFT collections via target_type/target_id, per the updated
    aai_scores schema. Keeps a daily-bucketed doc, same upsert pattern as
    the original.
    """
    db = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    db.aai_scores.update_one(
        {"target_type": target_type, "target_id": target_id, "date": today},
        {"$set": payload},
        upsert=True,
    )

def get_all_latest_aai_scores(target_type: str) -> dict:
    """Returns {target_id: aai_score_doc} for the latest score per target."""
    return _latest_aai(target_type)


def _latest_aai(target_type: str, target_ids=None) -> dict:
    """Newest aai_scores row per target, sorted on the (target_type, target_id, timestamp) index."""
    match: dict = {"target_type": target_type}
    if target_ids is not None:
        match["target_id"] = {"$in": sorted(set(target_ids))}
    pipeline = [
        {"$match": match},
        {"$sort": {"target_type": 1, "target_id": 1, "timestamp": -1}},
        {"$group": {"_id": "$target_id", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return {d["target_id"]: d for d in get_db().aai_scores.aggregate(pipeline, allowDiskUse=True)}


def get_latest_aai_scores_for(target_type: str, target_ids) -> dict:
    """{target_id: latest aai_scores row} for the given targets, in one aggregation."""
    ids = [t for t in target_ids if t]
    return _latest_aai(target_type, ids) if ids else {}

def update_user(user_id: ObjectId, payload: dict) -> bool:
    db = get_db()
    result = db.users.update_one({"_id": user_id}, {"$set": payload})
    return result.matched_count > 0


def get_activity_counts(user_id: ObjectId) -> dict:
    db = get_db()
    return {
        "holdings_count": db.portfolio_holdings.count_documents({"user_id": user_id}),
        "watchlists_count": db.watchlists.count_documents({"user_id": user_id}),
        "alerts_count": db.alerts.count_documents({"user_id": user_id}),
        "active_alerts_count": db.alerts.count_documents({"user_id": user_id, "status": "active"}),
    }


def email_exists(email: str) -> bool:
    db = get_db()
    return db.users.find_one({"email": email.lower().strip()}, projection={"_id": 1}) is not None