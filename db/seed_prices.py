"""
db/seed_prices.py
Seeds: prices, asset_market_data  (REAL data, not generated)

Fetches the live market snapshot (CoinGecko) and the hourly price history (Binance; DAI from CoinGecko)
through backend/controllers/market_data_controller.py, the same code the backend's scheduler runs every
few minutes. It used to generate a random-walk history instead; that, and any other row the live sources
did not write, is deleted.

Run: python db/seed_prices.py
"""
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))


def seed():
    from controllers.market_data_controller import refresh_market_snapshot, refresh_prices
    print(f"[asset_market_data] {refresh_market_snapshot()}")
    print(f"[prices] {refresh_prices()}")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
