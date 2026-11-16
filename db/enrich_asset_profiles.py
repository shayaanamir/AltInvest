"""
db/enrich_asset_profiles.py
Fills every covered asset's profile from CoinGecko: description, website, category tags, the subcategory
derived from them, and related assets (shared tags). Runs backend/controllers/asset_profile_controller.py,
the same code the backend's scheduler runs weekly; this just does all assets now.

The free API allows only a few calls a minute, so this pauses between assets (about 6 minutes for all 17)
and stops at a rate limit; run it again, or let the backend carry on.

Run: python db/enrich_asset_profiles.py
"""
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))


def seed():
    from controllers.asset_profile_controller import refresh_profiles
    from controllers.market_data_controller import SOURCES
    print(f"[asset profiles] {refresh_profiles(limit=len(SOURCES))}")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
