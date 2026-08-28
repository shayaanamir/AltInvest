"""
db/seed_prices.py
Seeds: prices
Generates synthetic hourly OHLC-ish price/volume history via geometric
Brownian motion — no dependency on ml/data/raw/*.csv or the ML pipeline
having been run. Schema matches ml/features/feature_engineering.py's
required input exactly: asset, price, volume, timestamp.

Run: python db/seed_prices.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
import random
from datetime import datetime, timedelta, timezone

from db.mongo_connection import get_db

# ── Config ──────────────────────────────────────────────────────────────────

DAYS_OF_HISTORY = 400          # >30d window needed by feature_engineering's rolling windows
HOURS_PER_DAY = 24

# Per-asset starting price + annualised volatility/drift, tuned to land
# roughly near the values used elsewhere in the mock data (assets.json etc.)
ASSET_PARAMS = {
    "BTC":  {"start_price": 42000.0,  "annual_vol": 0.55, "annual_drift": 0.40, "base_volume": 25_000_000_000},
    "ETH":  {"start_price": 2400.0,   "annual_vol": 0.65, "annual_drift": 0.35, "base_volume": 14_000_000_000},
    "SOL":  {"start_price": 95.0,     "annual_vol": 0.90, "annual_drift": 0.30, "base_volume": 4_500_000_000},
    "LINK": {"start_price": 12.0,     "annual_vol": 0.70, "annual_drift": 0.25, "base_volume": 450_000_000},
    "DOGE": {"start_price": 0.09,     "annual_vol": 1.10, "annual_drift": 0.45, "base_volume": 1_500_000_000},
    "ARB":  {"start_price": 1.05,     "annual_vol": 0.85, "annual_drift": 0.10, "base_volume": 210_000_000},
    "DAI":  {"start_price": 1.00,     "annual_vol": 0.01, "annual_drift": 0.00, "base_volume": 2_800_000_000},
    "UNI":  {"start_price": 6.80,     "annual_vol": 0.75, "annual_drift": -0.10, "base_volume": 150_000_000},
    "BASE": {"start_price": 17.50,    "annual_vol": 0.70, "annual_drift": 0.20, "base_volume": 30_000_000},
}

HOURS_PER_YEAR = 365 * HOURS_PER_DAY


def generate_gbm_series(start_price: float, annual_vol: float, annual_drift: float,
                         n_hours: int, seed: int) -> list[float]:
    """
    Geometric Brownian Motion:  S(t+1) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
    dt = 1 hour expressed as a fraction of a year.
    Occasionally injects a small regime-shift jump so the series doesn't look
    perfectly log-normal (real crypto data has fat tails / momentum bursts).
    """
    rng = random.Random(seed)
    dt = 1.0 / HOURS_PER_YEAR

    prices = [start_price]
    for i in range(1, n_hours):
        z = rng.gauss(0, 1)
        drift_term = (annual_drift - 0.5 * annual_vol ** 2) * dt
        shock_term = annual_vol * math.sqrt(dt) * z
        next_price = prices[-1] * math.exp(drift_term + shock_term)

        # Rare regime-shift jump (~0.3% of hours): momentum burst up or down
        if rng.random() < 0.003:
            jump = rng.uniform(-0.08, 0.10)
            next_price *= (1 + jump)

        prices.append(max(next_price, 0.0001))  # floor to avoid negative/zero
    return prices


def generate_volume_series(base_volume: float, n_hours: int, seed: int,
                            price_returns: list[float]) -> list[float]:
    """
    Volume correlated loosely with |return| (bigger moves → higher volume),
    plus daily seasonality (lower volume overnight UTC) and random noise.
    """
    rng = random.Random(seed + 1)
    volumes = []
    for i in range(n_hours):
        hour_of_day = i % HOURS_PER_DAY
        # mild daily seasonality curve, peak around 14:00 UTC
        seasonality = 0.75 + 0.5 * math.exp(-((hour_of_day - 14) ** 2) / 30)
        move_factor = 1.0
        if i > 0 and i - 1 < len(price_returns):
            move_factor = 1.0 + min(abs(price_returns[i - 1]) * 8, 2.5)
        noise = rng.uniform(0.8, 1.25)
        volumes.append(base_volume * seasonality * move_factor * noise / HOURS_PER_DAY)
    return volumes


def build_asset_docs(asset: str, params: dict, n_hours: int, end_time: datetime) -> list[dict]:
    seed = abs(hash(asset)) % (2 ** 31)
    prices = generate_gbm_series(
        params["start_price"], params["annual_vol"], params["annual_drift"], n_hours, seed
    )
    returns = [
        (prices[i] - prices[i - 1]) / prices[i - 1] if i > 0 else 0.0
        for i in range(n_hours)
    ]
    volumes = generate_volume_series(params["base_volume"], n_hours, seed, returns)

    start_time = end_time - timedelta(hours=n_hours - 1)
    docs = []
    for i in range(n_hours):
        ts = start_time + timedelta(hours=i)
        docs.append({
            "asset": asset,
            "price": round(prices[i], 8 if prices[i] < 1 else 2),
            "volume": round(volumes[i], 2),
            "timestamp": ts,
        })
    return docs


def seed():
    db = get_db()
    db.prices.create_index([("asset", 1), ("timestamp", 1)])

    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    n_hours = DAYS_OF_HISTORY * HOURS_PER_DAY

    for asset, params in ASSET_PARAMS.items():
        docs = build_asset_docs(asset, params, n_hours, end_time)

        db.prices.delete_many({"asset": asset})
        db.prices.insert_many(docs)

        first, last = docs[0]["price"], docs[-1]["price"]
        pct_change = (last - first) / first * 100
        print(f"[prices] {asset}: inserted {len(docs)} hourly rows "
              f"({docs[0]['timestamp'].date()} → {docs[-1]['timestamp'].date()}), "
              f"${first:,.4f} → ${last:,.4f} ({pct_change:+.1f}%)")

    print(f"\nSeeded {len(ASSET_PARAMS)} assets, {n_hours} hourly points each "
          f"({DAYS_OF_HISTORY} days of history).")


if __name__ == "__main__":
    seed()