"""OpenSea API v2 client for Phase 10 (D54): floor history, sale events, collection info, best listing.

The key comes from the OPENSEA_API_KEY environment variable, or from the repo's .env (gitignored) when the
variable is unset. It is sent only in the x-api-key header and is never printed, logged or written.
"""

import os
import time
from collections.abc import Iterator

import requests

from ml.gitinfo import REPO_ROOT

BASE = "https://api.opensea.io/api/v2"
PAGE_LIMIT = 200            # the events endpoint's maximum
MAX_ATTEMPTS = 6
MIN_INTERVAL = 0.3          # seconds between calls (the key allows 120 per 30 s)


class OpenSeaError(RuntimeError):
    """A call that failed after retries, or a missing key."""


def env_value(name: str) -> str | None:
    """os.environ first, then KEY=value lines of the repo's .env. Never logged."""
    if os.environ.get(name):
        return os.environ[name]
    path = REPO_ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key == name and value:
                return value.strip().strip('"').strip("'")
    return None


class Client:
    def __init__(self, key: str | None = None, session: requests.Session | None = None, sleep=time.sleep):
        self.key = key or env_value("OPENSEA_API_KEY")
        if not self.key:
            raise OpenSeaError("OPENSEA_API_KEY is not set (environment or .env)")
        self.session, self.sleep, self.calls, self._last = session or requests.Session(), sleep, 0, 0.0

    def get(self, path: str, params: dict | None = None, allow_404: bool = False) -> dict | None:
        reason = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            wait = MIN_INTERVAL - (time.monotonic() - self._last)
            if wait > 0:
                self.sleep(wait)
            self._last = time.monotonic()
            self.calls += 1
            try:
                r = self.session.get(f"{BASE}{path}", params=params, timeout=30,
                                     headers={"x-api-key": self.key, "accept": "application/json"})
            except requests.RequestException as exc:
                reason = type(exc).__name__
                self.sleep(2 ** attempt)
                continue
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404 and allow_404:
                return None
            reason = f"HTTP {r.status_code}"
            if r.status_code == 429 or r.status_code >= 500:
                self.sleep(float(r.headers.get("retry-after") or 2 ** attempt))
                continue
            break
        raise OpenSeaError(f"GET {path} failed: {reason}")

    def collection(self, slug: str) -> dict:
        return self.get(f"/collections/{slug}")

    def floor_prices(self, slug: str, timeframe: str = "all_time") -> list[dict]:
        """Points {time (unix s), token_unit (ETH), usd_price}; about one per day for all_time (10.0 A1)."""
        return self.get(f"/collections/{slug}/floor_prices", {"timeframe": timeframe})["floor_prices"]

    def sale_events(self, slug: str, after: int, before: int) -> Iterator[list[dict]]:
        """Pages of sale events with after < event_timestamp < before (unix s), newest first."""
        params = {"event_type": "sale", "limit": PAGE_LIMIT, "after": after, "before": before}
        while True:
            body = self.get(f"/events/collection/{slug}", params)
            events = body.get("asset_events") or []
            if events:
                yield events
            if not body.get("next") or not events:
                return
            params = {**params, "next": body["next"]}

    def best_listing_eth(self, slug: str, token_id: str) -> float | None:
        """Price in ETH of the item's best active listing; None if it is not listed or not priced in ETH."""
        body = self.get(f"/listings/collection/{slug}/nfts/{token_id}/best", allow_404=True)
        cur = ((body or {}).get("price") or {}).get("current") or {}
        if cur.get("currency") not in ("ETH", "WETH") or not cur.get("value"):
            return None
        return int(cur["value"]) / 10 ** int(cur.get("decimals", 18))
