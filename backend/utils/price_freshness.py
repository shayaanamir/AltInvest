"""
utils/price_freshness.py

How old a crypto price is (audit N-05). Every price the app shows comes from an `asset_market_data` row that the
market snapshot job (controllers/market_data_controller.py) refreshes every 2 minutes from CoinGecko. Each row
carries the price's own time (`timestamp`, CoinGecko's last_updated) and when we fetched it (`fetched_at`).

price_as_of     the price's time, ISO UTC (`timestamp`, else `fetched_at`); None without a price
price_delayed   True when that time is more than PRICE_DELAYED_AFTER ago: the job has stalled or CoinGecko is
                not answering, and the price on screen is old. None without a price.
"""
from datetime import datetime, timedelta, timezone

from utils.ml_rows import as_utc

# The snapshot runs every 2 minutes and CoinGecko updates within a few minutes, so 15 minutes means it stalled.
PRICE_DELAYED_AFTER = timedelta(minutes=15)


def price_freshness(row: dict | None, now: datetime | None = None) -> dict:
    row = row or {}
    ts = as_utc(row.get("timestamp")) or as_utc(row.get("fetched_at"))
    if row.get("price") is None or ts is None:
        return {"price_as_of": None, "price_delayed": None}
    now = now or datetime.now(timezone.utc)
    return {"price_as_of": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "price_delayed": now - ts > PRICE_DELAYED_AFTER}
