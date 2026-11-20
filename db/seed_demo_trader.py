"""
db/seed_demo_trader.py

Seeds a second demo account that looks like someone who signed up two weeks ago and has used the
platform since: a completed onboarding, a portfolio built up over several trades (with the history
in portfolio_transactions, including a partial sell with realised P&L), daily portfolio snapshots,
watchlists, alerts (one of which fired), and notifications.

Every trade is priced from the database itself, so the numbers line up with the charts:
  - crypto buys/sells use the stored hourly price nearest the trade time (`prices`);
  - the NFT is a real token bought at the price, time and ETH/USD rate of a real sale (`nft_sales`);
  - snapshots replay the trades day by day at that day's close and that day's NFT floor.
Dates are relative to the day the script runs (signup = 14 days ago), so it can be re-run later.
Re-running deletes and rebuilds this account's data (the account keeps its _id).

Development only, like db/seed_users.py: the password is in this file, so the account must never
exist on a shared or deployed database.

Usage (the local docker-compose database the running app uses):
    MONGO_URI=mongodb://localhost:27017 MONGO_DB_NAME=aaip_db APP_ENV=dev python db/seed_demo_trader.py

Demo credentials (development only):
    email:    alex.rivera@altinvest.com
    password: AlexDemo2026!
"""
import os
import sys
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from db.mongo_connection import get_db
from shared.app_env import app_env, is_dev

EMAIL = "alex.rivera@altinvest.com"
PASSWORD = "AlexDemo2026!"
NAME = "Alex Rivera"
DAYS_ON_PLATFORM = 14

NOW = datetime.now(timezone.utc)
SIGNUP = (NOW - timedelta(days=DAYS_ON_PLATFORM)).replace(hour=18, minute=12, second=0, microsecond=0)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    """`day` days after signup, at hour:minute UTC."""
    return (SIGNUP + timedelta(days=day)).replace(hour=hour, minute=minute)


# (when, kind, symbol, quantity). Prices come from `prices`.
CRYPTO_TRADES = [
    (at(0, 18, 40), "buy", "BTC", 0.085),
    (at(0, 18, 46), "buy", "ETH", 2.4),
    (at(0, 18, 51), "buy", "SOL", 35),
    (at(2, 9, 15), "buy", "LINK", 140),
    (at(5, 14, 5), "buy", "ETH", 1.1),       # topped up -> merged, new average
    (at(7, 20, 30), "sell", "SOL", 12),      # took some profit / cut risk
    (at(9, 11, 45), "buy", "AVAX", 55),
    (at(11, 16, 20), "buy", "BTC", 0.02),
]
# A real sale: this token, at this sale's price and time.
NFT_BUY = {"slug": "milady", "token_id": "6254", "near": at(2, 4, 44)}


def price_at(db, symbol: str, when: datetime) -> float:
    row = db.prices.find_one({"asset": symbol, "timestamp": {"$lte": when}}, sort=[("timestamp", -1)])
    if not row:
        raise SystemExit(f"no stored price for {symbol} at {when}; run the price seed first.")
    return round(float(row["price"]), 6 if row["price"] < 1 else 2)


def daily_closes(db, symbol: str, start: datetime) -> dict:
    out = {}
    for r in db.prices.find({"asset": symbol, "timestamp": {"$gte": start}}, {"timestamp": 1, "price": 1},
                            sort=[("timestamp", 1)]):
        out[r["timestamp"].strftime("%Y-%m-%d")] = float(r["price"])   # last of the day wins
    return out


def seed():
    if not is_dev():
        print(f"Skipped demo trader: APP_ENV={app_env()!r}; it is only created when APP_ENV=dev.")
        return
    from auth.security import hash_password
    db = get_db()

    # ── 1. user ──────────────────────────────────────────────────────────────
    db.users.update_one(
        {"email": EMAIL},
        {"$set": {
            "email": EMAIL, "name": NAME, "password_hash": hash_password(PASSWORD),
            "created_at": SIGNUP, "email_verified": True, "email_verified_at": SIGNUP + timedelta(minutes=3),
            "risk_profile": "growth", "layout_preference": "everything", "display_currency": "USD",
            "avatar_initials": "AR", "avatar_color": "#14b8a6",
            "onboarding": {
                "completed": True, "completed_at": SIGNUP + timedelta(minutes=9), "skipped": False,
                "answers": {
                    "markets": ["crypto", "nfts"], "risk": 68,
                    "goals": ["portfolio", "research", "alerts"],
                    "assets": ["BTC", "ETH", "SOL", "LINK"], "focus": "everything",
                },
            },
            "bio": "Software engineer, mostly large caps plus a couple of higher-beta L1s. Dabbling in NFTs.",
        },
         "$unset": {"email_verification_required": ""}},
        upsert=True,
    )
    uid = db.users.find_one({"email": EMAIL})["_id"]
    print(f"[users] {EMAIL} -> {uid}")

    for coll in ("portfolio_holdings", "portfolio_transactions", "portfolio_snapshots", "watchlists",
                 "alerts", "alert_triggers", "notifications", "user_sessions"):
        db[coll].delete_many({"user_id": uid})

    # ── 2. settings ──────────────────────────────────────────────────────────
    db.user_settings.update_one({"user_id": uid}, {"$set": {
        "user_id": uid,
        "preferences": {"display_currency": "USD", "date_format": "MM/DD/YYYY",
                        "default_landing_page": "Dashboard", "default_dashboard_layout": "everything"},
        "appearance": {"theme": "dark", "density": "compact"},
        "notifications": {
            "channels": {"inApp": True, "email": False},
            "alert_types": {"aaiThresholdOnly": True, "priceAlerts": True, "sentimentShifts": True,
                            "minorPriceWiggles": False, "marketNews": True, "systemMessages": True},
            "quiet_hours": {"enabled": True, "start": "23:00", "end": "07:00", "timezone": "America/Los_Angeles"},
        },
        "security": {"two_factor_enabled": False},
        "connected_accounts": {"google": False, "wallet": False},
    }}, upsert=True)

    # ── 3. trades -> holdings + transactions (same rules as holdings_controller) ──
    holdings: dict[str, dict] = {}
    txns = []
    events = []        # (when, symbol_or_slug, quantity delta) for the snapshot replay
    trades = [(w, k, s, q, price_at(db, s, w)) for w, k, s, q in CRYPTO_TRADES]

    sale = db.nft_sales.find_one({"slug": NFT_BUY["slug"], "token_id": NFT_BUY["token_id"],
                                  "timestamp": {"$gte": NFT_BUY["near"] - timedelta(hours=1),
                                                "$lte": NFT_BUY["near"] + timedelta(hours=1)}})
    if not sale:
        raise SystemExit("the NFT sale this account copies isn't in nft_sales; pick another one.")

    for when, kind, sym, qty, price in sorted(trades, key=lambda t: t[0]):
        h = holdings.get(sym)
        if kind == "buy":
            if h is None:
                h = holdings[sym] = {"_id": None, "user_id": uid, "asset_type": "crypto", "symbol": sym,
                                     "quantity": 0.0, "avg_buy_price_usd": None, "date_added": when}
                note = {}
            else:
                note = {"note": "merged into existing holding"}
            old_q, old_avg = h["quantity"], h["avg_buy_price_usd"]
            h["quantity"] = round(old_q + qty, 8)
            h["avg_buy_price_usd"] = price if old_avg is None else (old_q * old_avg + qty * price) / h["quantity"]
            txn = {"type": "buy", "quantity": qty, "price_usd": price, "quantity_after": h["quantity"],
                   "avg_buy_price_usd_after": round(h["avg_buy_price_usd"], 2), **note}
        else:
            h["quantity"] = round(h["quantity"] - qty, 8)
            txn = {"type": "sell", "quantity": qty, "price_usd": price,
                   "realised_pnl_usd": round((price - h["avg_buy_price_usd"]) * qty, 2),
                   "avg_buy_price_usd": round(h["avg_buy_price_usd"], 2), "quantity_after": h["quantity"]}
        h["updated_at"] = when
        txns.append((sym, when, txn))
        events.append((when, sym, qty if kind == "buy" else -qty))

    for sym, h in holdings.items():
        h["avg_buy_price_usd"] = round(h["avg_buy_price_usd"], 2)
        h["quantity"] = round(h["quantity"], 8)
        h["cost_basis_usd"] = round(h["quantity"] * h["avg_buy_price_usd"], 2)
        doc = {k: v for k, v in h.items() if k != "_id"}
        h["_id"] = db.portfolio_holdings.insert_one(doc).inserted_id

    eth_rate = round(sale["price_usd"] / sale["price_eth"], 2)
    nft_doc = {"user_id": uid, "asset_type": "nft", "nft_collection_slug": sale["slug"],
               "nft_token_id": sale["token_id"], "quantity": 1, "avg_buy_price_eth": sale["price_eth"],
               "avg_buy_eth_usd_rate": eth_rate, "cost_basis_usd": round(sale["price_eth"] * eth_rate, 2),
               "date_added": sale["timestamp"], "updated_at": sale["timestamp"]}
    nft_id = db.portfolio_holdings.insert_one(nft_doc).inserted_id
    events.append((sale["timestamp"], "nft:" + sale["slug"], 1))

    rows = [{"user_id": uid, "holding_id": str(holdings[sym]["_id"]), "asset_type": "crypto", "symbol": sym,
             "nft_collection_slug": None, "nft_token_id": None, "timestamp": when, **t}
            for sym, when, t in txns]
    rows.append({"user_id": uid, "holding_id": str(nft_id), "asset_type": "nft", "symbol": None,
                 "nft_collection_slug": sale["slug"], "nft_token_id": sale["token_id"], "type": "buy",
                 "timestamp": sale["timestamp"], "quantity": 1, "price_usd": None,
                 "price_eth": sale["price_eth"], "eth_usd_rate": eth_rate, "quantity_after": 1})
    db.portfolio_transactions.insert_many(rows)
    print(f"[portfolio_holdings] {len(holdings) + 1} holdings, [portfolio_transactions] {len(rows)} rows")

    # ── 4. daily snapshots: replay the trades at each day's close / floor ─────
    closes = {s: daily_closes(db, s, SIGNUP - timedelta(days=1)) for s in holdings}
    floors = {r["date"]: r["floor_usd"] for r in db.nft_market_data.find(
        {"slug": sale["slug"], "date": {"$gte": SIGNUP.strftime("%Y-%m-%d")}}, {"date": 1, "floor_usd": 1})}
    held: dict[str, float] = {}
    last_close, last_floor = {}, None
    snaps = []
    day = SIGNUP.date()
    while day <= NOW.date():
        end = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1)
        held = {}
        for when, key, delta in events:
            if when < end:
                held[key] = held.get(key, 0) + delta
        key = day.isoformat()
        total = 0.0
        for k, q in held.items():
            if k.startswith("nft:"):
                last_floor = floors.get(key, last_floor)
                total += (last_floor or nft_doc["cost_basis_usd"]) * q
            else:
                last_close[k] = closes[k].get(key, last_close.get(k))
                total += (last_close[k] or 0) * q
        snaps.append({"user_id": uid, "snapshot_date": day.strftime("%Y-%m-%dT00:00:00Z"),
                      "total_value_usd": round(total, 2), "source": "backfill", "nft_at_current_floor": False})
        day += timedelta(days=1)
    db.portfolio_snapshots.insert_many(snaps)
    print(f"[portfolio_snapshots] {len(snaps)} days, {snaps[0]['total_value_usd']} -> {snaps[-1]['total_value_usd']}")

    # ── 5. watchlists ────────────────────────────────────────────────────────
    db.watchlists.insert_many([
        {"user_id": uid, "name": "Next buys", "created_at": at(1, 8, 30), "items": [
            {"type": "crypto", "symbol_or_slug": "NEAR", "added_at": at(1, 8, 31)},
            {"type": "crypto", "symbol_or_slug": "ARB", "added_at": at(3, 21, 2)},
            {"type": "crypto", "symbol_or_slug": "AVAX", "added_at": at(4, 12, 10)},
            {"type": "crypto", "symbol_or_slug": "DOT", "added_at": at(10, 19, 44)},
        ]},
        {"user_id": uid, "name": "NFT floors", "created_at": at(0, 19, 5), "items": [
            {"type": "nft", "symbol_or_slug": "milady", "added_at": at(0, 19, 5)},
            {"type": "nft", "symbol_or_slug": "pudgypenguins", "added_at": at(0, 19, 6)},
            {"type": "nft", "symbol_or_slug": "azuki", "added_at": at(6, 22, 15)},
        ]},
    ])

    # ── 6. alerts (+ the one that fired) and notifications ───────────────────
    sol_drop = at(8, 7, 25)
    sol_value = price_at(db, "SOL", sol_drop)
    btc_now = price_at(db, "BTC", NOW)
    alerts = [
        {"user_id": uid, "target_type": "crypto", "target_symbol": "SOL", "target_name": "Solana",
         "metric_type": "price", "condition": "below", "threshold_value": round(sol_value * 1.01, 0),
         "status": "triggered", "delivery_channel": "in-app", "created_at": at(7, 20, 35),
         "last_triggered_at": sol_drop, "last_observed_value": sol_value},
        {"user_id": uid, "target_type": "crypto", "target_symbol": "BTC", "target_name": "Bitcoin",
         "metric_type": "price", "condition": "above", "threshold_value": round(btc_now * 1.1, -3),
         "status": "active", "delivery_channel": "in-app", "created_at": at(0, 19, 0),
         "last_triggered_at": None, "last_observed_value": btc_now},
        {"user_id": uid, "target_type": "crypto", "target_symbol": "LINK", "target_name": "Chainlink",
         "metric_type": "aai_score", "condition": "below", "threshold_value": 45,
         "status": "active", "delivery_channel": "in-app", "created_at": at(2, 9, 20),
         "last_triggered_at": None, "last_observed_value": None},
        {"user_id": uid, "target_type": "crypto", "target_symbol": "ETH", "target_name": "Ethereum",
         "metric_type": "sentiment", "condition": "shifts_bearish", "threshold_value": None,
         "status": "active", "delivery_channel": "in-app", "created_at": at(5, 14, 10),
         "last_triggered_at": None, "last_observed_value": None},
    ]
    sol_alert_id = db.alerts.insert_many(alerts).inserted_ids[0]
    sol_title = f"SOL fell below ${alerts[0]['threshold_value']:,.0f}"
    db.alert_triggers.insert_one({
        "alert_id": str(sol_alert_id), "user_id": uid, "triggered_at": sol_drop, "value": sol_value,
        "previous_value": None, "condition": "below", "threshold_value": alerts[0]["threshold_value"],
        "metric_type": "price", "message": sol_title})

    def note(when, kind, title, message, read, page, symbol=None, slug=None, **extra):
        return {"user_id": uid, "type": kind, "title": title, "message": message, "read": read,
                "timestamp": when, "deep_link": {"page": page, "symbol": symbol, "slug": slug}, **extra}

    gain = snaps[-1]["total_value_usd"] - snaps[-8]["total_value_usd"] if len(snaps) >= 8 else 0
    db.notifications.insert_many([
        note(SIGNUP + timedelta(minutes=10), "system", "Welcome to AltInvest",
             "Your dashboard shows the full overview. Add holdings to start tracking your portfolio.",
             True, "Dashboard"),
        note(sol_drop, "alert_triggered", sol_title,
             f"Solana traded at ${sol_value:,.2f}, below your alert threshold.", True, "AssetDetail",
             symbol="SOL", alert_id=str(sol_alert_id)),
        note(at(7, 8, 0), "system", "Your first weekly portfolio summary is ready",
             "See how your holdings moved this week, with realised and unrealised P&L.", True, "Portfolio"),
        note(at(12, 15, 30), "market_event", "Milady floor moved this week",
             "The collection you hold has a new 7-day floor and liquidity reading.", False,
             "NFTCollectionDetail", slug="milady"),
        note(at(14, 8, 0) if at(14, 8, 0) < NOW else NOW - timedelta(hours=1), "system",
             "Weekly portfolio summary is ready",
             f"Your portfolio {'gained' if gain >= 0 else 'lost'} ${abs(gain):,.0f} over the last 7 days.",
             False, "Portfolio"),
    ])
    print("[watchlists] 2, [alerts] 4 (1 triggered), [notifications] 5")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
