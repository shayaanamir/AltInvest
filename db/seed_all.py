"""
db/seed_all.py
Runs every seed script in dependency order.
Run: python db/seed_all.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import (
    seed as seed_legacy,            # existing db/seed.py (BTC/ETH assets shortlist — superseded by seed_assets)
    seed_assets,
    seed_prices,
    seed_nft,
    seed_insights,
    seed_predictions_risk,
    seed_users,                     # existing db/seed_users.py (demo user login credentials)
    seed_user_data,
)

STEPS = [
    ("assets + asset_market_data", seed_assets.seed),
    ("prices (from ml/data/raw CSVs)", seed_prices.seed),
    ("nft_*", seed_nft.seed),
    ("market_insights + sentiment_themes", seed_insights.seed),
    ("predictions + risk_scores + risk_breakdown", seed_predictions_risk.seed),
    ("users (demo login)", seed_users.seed),
    ("user_settings + portfolio_holdings + watchlists + alerts + notifications", seed_user_data.seed),
]


def run():
    for label, fn in STEPS:
        print(f"\n=== Seeding: {label} ===")
        try:
            fn()
        except Exception as exc:
            print(f"  !! FAILED ({label}): {exc}")
    print("\nAll seed steps attempted.")


if __name__ == "__main__":
    run()