"""
backend/controllers/fx_controller.py

USD exchange rates for the "Display currency" setting. Every price and value in the database is
stored in USD; the frontend converts for display using the latest row written here.

Source: Frankfurter (https://frankfurter.dev), free and keyless, serving the European Central
Bank's reference rates. The ECB publishes once per working day (around 16:00 CET), so the rate
date can be a day or two behind on weekends and holidays; `as_of` carries that date.
"""
import time
import logging
from datetime import datetime, timezone

import httpx

from db.mongo_connection import get_db

log = logging.getLogger("fx_rates")

BASE_CURRENCY = "USD"
# Must match CURRENCY_OPTIONS in frontend/src/content/uiOptions.js.
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "INR", "JPY"]

_SOURCE_URL = "https://api.frankfurter.dev/v1/latest"
_TIMEOUT_SECONDS = 15
_INTERVAL_SECONDS = 6 * 60 * 60   # every 6 hours; one stored row per rate date
_RETRY_SECONDS = 15 * 60          # after a failed fetch


def fetch_rates() -> dict:
    """Pulls the latest USD-based rates from Frankfurter. Raises on any network or shape problem."""
    symbols = [c for c in SUPPORTED_CURRENCIES if c != BASE_CURRENCY]
    resp = httpx.get(
        _SOURCE_URL,
        params={"base": BASE_CURRENCY, "symbols": ",".join(symbols)},
        timeout=_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    body = resp.json()

    rates = body.get("rates") or {}
    missing = [c for c in symbols if not isinstance(rates.get(c), (int, float)) or rates[c] <= 0]
    if body.get("base") != BASE_CURRENCY or missing or not body.get("date"):
        raise ValueError(f"unexpected Frankfurter response (missing: {missing or 'base/date'})")

    return {
        "base": BASE_CURRENCY,
        "rates": {BASE_CURRENCY: 1.0, **{c: float(rates[c]) for c in symbols}},
        "as_of": body["date"],          # the ECB publication date, YYYY-MM-DD
        "source": "frankfurter (ECB reference rates)",
    }


def refresh_rates() -> dict:
    """Fetches and upserts one row per rate date. Returns the stored document."""
    doc = fetch_rates()
    db = get_db()
    db.fx_rates.create_index([("base", 1), ("as_of", -1)], unique=True)
    db.fx_rates.update_one(
        {"base": doc["base"], "as_of": doc["as_of"]},
        {"$set": {**doc, "fetched_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return doc


def get_latest_rates() -> dict | None:
    """The most recent stored rates, or None if none have been fetched yet."""
    return get_db().fx_rates.find_one({"base": BASE_CURRENCY}, {"_id": 0}, sort=[("as_of", -1)])


def run_fx_scheduler() -> None:
    """Daemon-thread loop: fetch at startup, then every 6 hours (retry sooner after a failure). Never raises."""
    while True:
        try:
            doc = refresh_rates()
            log.info("[fx] stored %s rates as of %s", doc["base"], doc["as_of"])
            delay = _INTERVAL_SECONDS
        except Exception as exc:
            log.error("[fx] refresh failed: %s: %s", type(exc).__name__, exc)
            delay = _RETRY_SECONDS
        time.sleep(delay)
