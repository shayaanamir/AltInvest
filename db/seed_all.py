"""
db/seed_all.py
Runs every seed script in dependency order.
Run: python db/seed_all.py

No seed writes predictions, risk_scores, risk_breakdown or aai_scores (ml/docs/DECISIONS.md D87): predictions and
risk scores come only from the ML pull (backend/controllers/ml_pull_controller.py), AAI scores only from the AAI
refresh (backend/controllers/aai_controller.py). db/cleanup_seeded_ml_rows.py removes rows an older seed wrote.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import (
    seed as seed_legacy,            # existing db/seed.py (BTC/ETH assets shortlist — superseded by seed_assets)
    seed_assets,
    seed_prices,
    enrich_asset_profiles,
    seed_nft,
    seed_insights,
    seed_users,                     # existing db/seed_users.py (demo user login credentials)
    seed_user_data,
    seed_portfolio_snapshots,
)

STEPS = [
    ("assets (metadata only)", seed_assets.seed),
    ("live prices + market data (CoinGecko, Binance)", seed_prices.seed),
    ("asset profiles (CoinGecko description, website, tags)", enrich_asset_profiles.seed),
    ("nft_*", seed_nft.seed),
    ("market insights + themes (real headlines, LLM themes)", seed_insights.seed),
    ("users (demo login)", seed_users.seed),
    ("user_settings + portfolio_holdings + watchlists + alerts + notifications", seed_user_data.seed),
    ("portfolio_snapshots (history backfill)", seed_portfolio_snapshots.seed),
]


def run():
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    for label, fn in STEPS:
        print(f"\n=== Seeding: {label} ===")
        try:
            fn()
        except Exception as exc:
            print(f"  !! FAILED ({label}): {exc}")
    print("\nAll seed steps attempted.")


if __name__ == "__main__":
    run()