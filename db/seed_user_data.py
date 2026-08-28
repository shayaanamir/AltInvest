"""
db/seed_user_data.py
Seeds: users (extends db/seed_users.py demo user with full profile),
       user_settings, portfolio_holdings, watchlists, alerts, notifications
Run AFTER db/seed_users.py and only once auth/protected routes are wired.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
BACKEND_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "backend")
sys.path.insert(0, BACKEND_DIR)

from datetime import datetime, timezone
from db.mongo_connection import get_db
from auth.security import hash_password

NOW = datetime.now(timezone.utc)
DEMO_EMAIL = "demo@altinvest.com"


def seed():
    db = get_db()

    # 1. Extend the demo user (created by db/seed_users.py) with full profile fields
    db.users.update_one(
        {"email": DEMO_EMAIL},
        {"$set": {
            "name": "Demo User",
            "avatar_initials": "DU",
            "avatar_color": "#5b6ef5",
            "created_at": NOW,
            "email_verified": True,
            "risk_profile": "balanced",
            "layout_preference": "ai-first",
            "display_currency": "USD",
            "onboarding": {
                "completed": True,
                "completed_at": NOW,
                "skipped": False,
                "answers": {
                    "markets": ["crypto", "nfts"],
                    "risk": 55,
                    "goals": ["research", "discovery", "portfolio"],
                    "assets": ["BTC", "ETH", "SOL"],
                    "layout": "ai-first",
                },
            },
            "bio": "Long-term crypto holder exploring alternative assets.",
        }},
        upsert=True,
    )
    user = db.users.find_one({"email": DEMO_EMAIL})
    user_id = user["_id"]
    print(f"[users] extended demo user {user_id}")

    # 2. user_settings
    db.user_settings.update_one(
        {"user_id": user_id},
        {"$set": {
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
                "quiet_hours": {"enabled": True, "start": "22:00", "end": "07:00",
                                 "timezone": "America/New_York"},
            },
            "security": {"two_factor_enabled": False},
            "connected_accounts": {"google": False, "github": False, "wallet": False},
        }},
        upsert=True,
    )
    print("[user_settings] upserted")

    # 3. portfolio_holdings
    db.portfolio_holdings.delete_many({"user_id": user_id})
    holdings = [
        {"user_id": user_id, "asset_type": "crypto", "symbol": "BTC",
         "quantity": 0.4218, "avg_buy_price_usd": 52300.00, "cost_basis_usd": 22060.07,
         "date_added": datetime(2026, 5, 18, 11, 2, tzinfo=timezone.utc), "updated_at": NOW},
        {"user_id": user_id, "asset_type": "crypto", "symbol": "ETH",
         "quantity": 6.8420, "avg_buy_price_usd": 2890.00, "cost_basis_usd": 19773.38,
         "date_added": datetime(2026, 5, 19, 9, 40, tzinfo=timezone.utc), "updated_at": NOW},
        {"user_id": user_id, "asset_type": "nft", "nft_collection_slug": "boredapeyachtclub",
         "nft_token_id": "4271", "quantity": 1, "avg_buy_price_eth": 11.5,
         "avg_buy_eth_usd_rate": 2100.00, "cost_basis_usd": 24150.00,
         "date_added": datetime(2026, 6, 2, 14, 15, tzinfo=timezone.utc), "updated_at": NOW},
    ]
    db.portfolio_holdings.insert_many(holdings)
    print(f"[portfolio_holdings] inserted {len(holdings)}")

    # 4. watchlists
    db.watchlists.delete_many({"user_id": user_id})
    watchlists = [
        {"user_id": user_id, "name": "Considering", "created_at": datetime(2026, 8, 14, 10, 5, tzinfo=timezone.utc),
         "items": [
             {"type": "crypto", "symbol_or_slug": "SOL", "added_at": NOW},
             {"type": "crypto", "symbol_or_slug": "DOGE", "added_at": NOW},
             {"type": "nft", "symbol_or_slug": "genesispunks", "added_at": NOW},
         ]},
        {"user_id": user_id, "name": "Core Watch", "created_at": datetime(2026, 6, 20, 8, 30, tzinfo=timezone.utc),
         "items": [
             {"type": "crypto", "symbol_or_slug": "LINK", "added_at": NOW},
             {"type": "nft", "symbol_or_slug": "astralcats", "added_at": NOW},
         ]},
    ]
    db.watchlists.insert_many(watchlists)
    print(f"[watchlists] inserted {len(watchlists)}")

    # 5. alerts
    db.alerts.delete_many({"user_id": user_id})
    alerts = [
        {"user_id": user_id, "target_type": "crypto", "target_symbol": "SOL", "target_name": "Solana",
         "metric_type": "aai_score", "condition": "below", "threshold_value": 55,
         "status": "triggered", "delivery_channel": "push",
         "created_at": datetime(2026, 8, 15, 16, 40, tzinfo=timezone.utc),
         "last_triggered_at": datetime(2026, 8, 26, 9, 14, tzinfo=timezone.utc),
         "last_observed_value": 53.1},
        {"user_id": user_id, "target_type": "crypto", "target_symbol": "BTC", "target_name": "Bitcoin",
         "metric_type": "price", "condition": "above", "threshold_value": 100000,
         "status": "active", "delivery_channel": "push",
         "created_at": datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
         "last_triggered_at": None, "last_observed_value": 71450.30},
        {"user_id": user_id, "target_type": "crypto", "target_symbol": "ETH", "target_name": "Ethereum",
         "metric_type": "sentiment", "condition": "shifts_bearish", "threshold_value": None,
         "status": "active", "delivery_channel": "in-app",
         "created_at": datetime(2026, 6, 25, 19, 20, tzinfo=timezone.utc),
         "last_triggered_at": None, "last_observed_value": 0.14},
    ]
    db.alerts.insert_many(alerts)
    print(f"[alerts] inserted {len(alerts)}")

    # 6. notifications
    db.notifications.delete_many({"user_id": user_id})
    notifications = [
        {"user_id": user_id, "type": "alert_triggered",
         "title": "SOL AAI dropped below your 55 threshold",
         "message": "Solana's AAI Score fell to 53.1, driven by cooling sentiment and rising short-term volatility.",
         "read": True, "timestamp": datetime(2026, 8, 26, 9, 14, tzinfo=timezone.utc),
         "deep_link": {"page": "AssetDetail", "symbol": "SOL", "slug": None}},
        {"user_id": user_id, "type": "market_event",
         "title": "BAYC floor price fell 4.5% in 24h",
         "message": "Liquidity across blue-chip NFT collections thinned this week, pressuring BAYC's floor toward 14.2 ETH.",
         "read": False, "timestamp": datetime(2026, 8, 28, 2, 50, tzinfo=timezone.utc),
         "deep_link": {"page": "NFTCollectionDetail", "symbol": None, "slug": "boredapeyachtclub"}},
        {"user_id": user_id, "type": "system",
         "title": "Weekly portfolio summary is ready",
         "message": "Your portfolio is up 68.3% overall since you started tracking it on AltInvest.",
         "read": False, "timestamp": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
         "deep_link": {"page": "Portfolio", "symbol": None, "slug": None}},
    ]
    db.notifications.insert_many(notifications)
    print(f"[notifications] inserted {len(notifications)}")

    # indexes
    db.user_settings.create_index("user_id", unique=True)
    db.portfolio_holdings.create_index([("user_id", 1), ("asset_type", 1)])
    db.watchlists.create_index("user_id")
    db.alerts.create_index([("user_id", 1), ("status", 1)])
    db.notifications.create_index([("user_id", 1), ("timestamp", -1)])
    print("Indexes ensured.")


if __name__ == "__main__":
    seed()