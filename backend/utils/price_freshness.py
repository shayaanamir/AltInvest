"""
utils/price_freshness.py

How old a price is (audit N-05).

Crypto: every price the app shows comes from an `asset_market_data` row that the market snapshot job
(controllers/market_data_controller.py) refreshes every 2 minutes from CoinGecko. Each row carries the price's own
time (`timestamp`, CoinGecko's last_updated) and when we fetched it (`fetched_at`).

NFT floors: one `nft_market_data` row per collection per day from the ML service, whose `timestamp` is the floor's
as-of time (00:00 UTC of its day). The ML service calls a floor stale after 48 hours (ml/config.py
STALE_DATA_HOURS, D55), so that is the limit here.

price_as_of     the price's (or floor's) time, ISO UTC; None without a price
price_delayed   True when that time is older than the limit: the job stalled or the source is not answering, and
                the number on screen is old. None without a price.
"""
from datetime import datetime, timedelta, timezone

from utils.ml_rows import as_utc

# The snapshot runs every 2 minutes and CoinGecko updates within a few minutes, so 15 minutes means it stalled.
PRICE_DELAYED_AFTER = timedelta(minutes=15)
# NFT floors are daily (as of 00:00 UTC); the ML service marks a floor older than 48 h as stale.
FLOOR_DELAYED_AFTER = timedelta(hours=48)


def price_freshness(row: dict | None, now: datetime | None = None, *, price_key: str = "price",
                    delayed_after: timedelta = PRICE_DELAYED_AFTER) -> dict:
    row = row or {}
    ts = as_utc(row.get("timestamp")) or as_utc(row.get("fetched_at"))
    if row.get(price_key) is None or ts is None:
        return {"price_as_of": None, "price_delayed": None}
    now = now or datetime.now(timezone.utc)
    return {"price_as_of": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "price_delayed": now - ts > delayed_after}


def floor_freshness(row: dict | None, now: datetime | None = None) -> dict:
    """price_as_of / price_delayed for an NFT floor (an `nft_market_data` row)."""
    return price_freshness(row, now, price_key="floor_usd", delayed_after=FLOOR_DELAYED_AFTER)
