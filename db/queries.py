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

def _latest_per_key(collection: str, key: str) -> dict:
    """{key_value: latest_doc} for collections keyed by a field + timestamp."""
    db = get_db()
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": f"${key}", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return {d[key]: d for d in db[collection].aggregate(pipeline, allowDiskUse=True)}


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
    out = {}
    step = max(1, hours // points)
    for a in assets:
        rows = list(db.prices.find(
            {"asset": a.upper()}, sort=[("timestamp", -1)], limit=hours,
            projection={"_id": 0, "price": 1},
        ))
        series = [r["price"] for r in reversed(rows)]
        out[a.upper()] = series[::step] if len(series) > points else series
    return out


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


def get_asset_market_data_latest(asset_id: str) -> dict | None:
    db = get_db()
    return db.asset_market_data.find_one(
        {"asset_id": asset_id.upper()},
        sort=[("timestamp", -1)],
        projection={"_id": 0},
    )


def get_asset_market_data_all_latest() -> list:
    """One latest snapshot per asset — used by dashboard/discover/trending."""
    db = get_db()
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$asset_id", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return list(db.asset_market_data.aggregate(pipeline))


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


def insert_portfolio_holding(user_id: ObjectId, payload: dict) -> str:
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {**payload, "user_id": user_id, "date_added": now, "updated_at": now}
    result = db.portfolio_holdings.insert_one(doc)
    return str(result.inserted_id)


def update_portfolio_holding(user_id: ObjectId, holding_id: str, payload: dict) -> bool:
    db = get_db()
    result = db.portfolio_holdings.update_one(
        {"_id": ObjectId(holding_id), "user_id": user_id},
        {"$set": {**payload, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.matched_count > 0


def delete_portfolio_holding(user_id: ObjectId, holding_id: str) -> bool:
    db = get_db()
    result = db.portfolio_holdings.delete_one({"_id": ObjectId(holding_id), "user_id": user_id})
    return result.deleted_count > 0


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


def create_watchlist(user_id: ObjectId, name: str) -> str:
    db = get_db()
    doc = {"user_id": user_id, "name": name, "created_at": datetime.now(timezone.utc), "items": []}
    result = db.watchlists.insert_one(doc)
    return str(result.inserted_id)


def delete_watchlist(user_id: ObjectId, watchlist_id: str) -> bool:
    db = get_db()
    result = db.watchlists.delete_one({"_id": ObjectId(watchlist_id), "user_id": user_id})
    return result.deleted_count > 0


def add_watchlist_item(user_id: ObjectId, watchlist_id: str, item_type: str, symbol_or_slug: str) -> bool:
    db = get_db()
    item = {"type": item_type, "symbol_or_slug": symbol_or_slug, "added_at": datetime.now(timezone.utc)}
    result = db.watchlists.update_one(
        {"_id": ObjectId(watchlist_id), "user_id": user_id},
        {"$push": {"items": item}},
    )
    return result.matched_count > 0


def remove_watchlist_item(user_id: ObjectId, watchlist_id: str, symbol_or_slug: str) -> bool:
    db = get_db()
    result = db.watchlists.update_one(
        {"_id": ObjectId(watchlist_id), "user_id": user_id},
        {"$pull": {"items": {"symbol_or_slug": symbol_or_slug}}},
    )
    return result.matched_count > 0


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


def get_nft_market_data_latest(slug: str) -> dict | None:
    db = get_db()
    return db.nft_market_data.find_one(
        {"slug": slug}, sort=[("timestamp", -1)], projection={"_id": 0}
    )


def get_nft_market_data_all_latest() -> list:
    db = get_db()
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$slug", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return list(db.nft_market_data.aggregate(pipeline))


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
    regex = {"$regex": q, "$options": "i"}
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


def log_search(user_id: ObjectId, query: str) -> None:
    db = get_db()
    db.user_search_history.insert_one(
        {"user_id": user_id, "query": query, "searched_at": datetime.now(timezone.utc)}
    )


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
    db = get_db()
    pipeline = [
        {"$match": {"target_type": target_type}},
        {"$sort": {"timestamp": -1}},
        {"$group": {"_id": "$target_id", "doc": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$project": {"_id": 0}},
    ]
    return {d["target_id"]: d for d in db.aai_scores.aggregate(pipeline)}

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

# ── Login sessions (one row per issued access token; deleting the row revokes the token) ──

_session_indexes_ready = False


def _sessions():
    global _session_indexes_ready
    db = get_db()
    if not _session_indexes_ready:
        db.user_sessions.create_index([("user_id", 1), ("last_active", -1)])
        # Mongo drops each row once its token has expired.
        db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        _session_indexes_ready = True
    return db.user_sessions


def create_user_session(user_id: ObjectId, expires_at: datetime, user_agent: str, ip: str | None) -> str:
    now = datetime.now(timezone.utc)
    result = _sessions().insert_one({
        "user_id": user_id, "created_at": now, "last_active": now, "expires_at": expires_at,
        "user_agent": user_agent, "ip": ip,
    })
    return str(result.inserted_id)


def get_user_session(session_id: str) -> dict | None:
    try:
        oid = ObjectId(session_id)
    except Exception:
        return None
    return _sessions().find_one({"_id": oid})


def touch_user_session(session_id: ObjectId, when: datetime) -> None:
    _sessions().update_one({"_id": session_id}, {"$set": {"last_active": when}})


def list_user_sessions(user_id: ObjectId) -> list:
    now = datetime.now(timezone.utc)
    return list(_sessions().find(
        {"user_id": user_id, "expires_at": {"$gt": now}}, sort=[("last_active", -1)]
    ))


def delete_user_session(user_id: ObjectId, session_id: ObjectId) -> bool:
    return _sessions().delete_one({"_id": session_id, "user_id": user_id}).deleted_count > 0


def delete_other_user_sessions(user_id: ObjectId, keep_session_id: ObjectId) -> int:
    return _sessions().delete_many({"user_id": user_id, "_id": {"$ne": keep_session_id}}).deleted_count
