"""
backend/controllers/asset_profile_controller.py

Asset profiles from CoinGecko (/coins/{id}, keyless). Replaces the typed-in profile fields of the seed:

  description     the first sentences of CoinGecko's English description
  website         CoinGecko's first homepage link
  categories      CoinGecko's category tags, as published
  subcategory     one label derived from those tags by SUBCATEGORY_RULES (first match wins), e.g.
                  "Stablecoins" -> Stablecoin, "Layer 2 (L2)" -> Layer 2, "Layer 1 (L1)" -> Layer 1
  related_assets  the other covered assets sharing the most specific tags (related_basis says which tags);
                  investor portfolios, indices and tags most covered assets carry are not counted

(Price, market cap and all-time high come from market_data_controller.)

The free API allows only a few calls a minute, and market_data_controller already calls it every 2 minutes
from the same IP, so a run refreshes at most PROFILES_PER_RUN assets with PAUSE_SECONDS between calls and
stops at the first rate limit; the next run carries on. A profile is refreshed when missing or older than
PROFILE_MAX_AGE_DAYS: descriptions and tags change rarely.
"""
import path_setup  # noqa: F401

import html
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

from controllers.market_data_controller import SOURCES

COINGECKO_COIN_URL = "https://api.coingecko.com/api/v3/coins/{id}"
PROFILE_SOURCE = "coingecko"
PROFILE_MAX_AGE_DAYS = 7
PROFILES_PER_RUN = 4
PAUSE_SECONDS = 20
RUN_INTERVAL_SECONDS = 10 * 60
MAX_SENTENCES = 3
RELATED_MAX = 4

_sleep = time.sleep   # replaced in tests


class RateLimited(Exception):
    pass


# CoinGecko tag -> subcategory, first match wins (most specific first).
SUBCATEGORY_RULES = [
    (re.compile(r"stablecoin", re.I), "Stablecoin"),
    (re.compile(r"\bmeme", re.I), "Meme"),
    (re.compile(r"exchange-based tokens|centralized exchange \(cex\) token", re.I), "Exchange token"),
    (re.compile(r"^layer 2", re.I), "Layer 2"),
    (re.compile(r"^layer 0", re.I), "Layer 0"),
    (re.compile(r"^oracle", re.I), "Oracle"),
    (re.compile(r"decentralized exchange", re.I), "DEX"),
    (re.compile(r"decentralized finance|^defi$", re.I), "DeFi"),
    (re.compile(r"interoperability", re.I), "Interoperability"),
    (re.compile(r"^layer 1", re.I), "Layer 1"),
    (re.compile(r"smart contract platform", re.I), "Smart contract platform"),
]

# Tags that say nothing about what an asset is: who invested, which index lists it, where it is "made".
NOT_RELATEDNESS = re.compile(r"portfolio|index|holdings|made in|launchpad|alleged sec|proof of|top 100", re.I)


def subcategory_of(categories: list) -> str | None:
    for pattern, label in SUBCATEGORY_RULES:
        if any(pattern.search(c or "") for c in categories or []):
            return label
    return None


def short_description(raw: str) -> str | None:
    text = html.unescape(re.sub(r"<[^>]+>", "", raw or "")).strip()
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:MAX_SENTENCES]).strip()


def profile_fields(coin: dict) -> dict:
    """One /coins/{id} response -> the profile fields stored on the asset."""
    homepage = next((u for u in ((coin.get("links") or {}).get("homepage") or []) if u), None)
    categories = [c for c in (coin.get("categories") or []) if c]
    return {
        "description": short_description((coin.get("description") or {}).get("en")),
        "website": homepage,
        "categories": categories,
        "subcategory": subcategory_of(categories),
        "coingecko_id": coin.get("id"),
        "profile_source": PROFILE_SOURCE,
    }


def related_from_categories(cats_by_asset: dict, market_cap: dict | None = None) -> dict:
    """
    {asset: (related assets, {related asset: shared tags})}. Tags carried by more than half of the
    assets (e.g. "Smart Contract Platform") and NOT_RELATEDNESS tags are ignored. Ranked by shared tags,
    then market cap.
    """
    market_cap = market_cap or {}
    n = len(cats_by_asset)
    counts = {}
    for cats in cats_by_asset.values():
        for c in set(cats):
            counts[c] = counts.get(c, 0) + 1
    useful = {a: {c for c in cats if not NOT_RELATEDNESS.search(c) and counts[c] <= n / 2}
              for a, cats in cats_by_asset.items()}
    out = {}
    for a, mine in useful.items():
        scored = []
        for b, theirs in useful.items():
            shared = sorted(mine & theirs)
            if b != a and shared:
                scored.append((-len(shared), -(market_cap.get(b) or 0), b, shared))
        scored.sort()
        top = scored[:RELATED_MAX]
        out[a] = ([b for *_, b, _ in top], {b: shared for *_, b, shared in top})
    return out


def fetch_coin(client: httpx.Client, cg_id: str) -> dict:
    resp = client.get(COINGECKO_COIN_URL.format(id=cg_id), timeout=20, params={
        "localization": "false", "tickers": "false", "market_data": "false",
        "community_data": "false", "developer_data": "false", "sparkline": "false"})
    if resp.status_code == 429:
        raise RateLimited(resp.headers.get("retry-after") or "")
    resp.raise_for_status()
    return resp.json()


def _due(asset: dict, now: datetime) -> bool:
    ts = asset.get("profile_updated_at")
    if not isinstance(ts, datetime):
        return True
    ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return now - ts > timedelta(days=PROFILE_MAX_AGE_DAYS)


def refresh_profiles(client: httpx.Client | None = None, db=None, now: datetime | None = None,
                     limit: int = PROFILES_PER_RUN) -> dict:
    """
    Refreshes up to `limit` due profiles (missing ones first), then recomputes every covered asset's
    related assets from the stored tags. Stops at the first rate limit.
    """
    from db.mongo_connection import get_db
    db = db if db is not None else get_db()
    now = now or datetime.now(timezone.utc)
    assets = {a["asset_id"]: a for a in db.assets.find({"asset_id": {"$in": list(SOURCES)}}, {"_id": 0})}
    due = sorted((a for a in SOURCES if a in assets and _due(assets[a], now)),
                 key=lambda a: assets[a].get("profile_updated_at") is not None)[:limit]

    done, stopped = [], None
    with (client or httpx.Client()) as http:
        for i, asset in enumerate(due):
            if i:
                _sleep(PAUSE_SECONDS)
            try:
                fields = profile_fields(fetch_coin(http, SOURCES[asset][0]))
            except RateLimited:
                stopped = "rate limited"
                break
            except Exception as exc:
                stopped = f"{asset}: {type(exc).__name__}: {exc}"[:200]
                continue
            db.assets.update_one({"asset_id": asset}, {"$set": {**fields, "profile_updated_at": now}})
            assets[asset].update(fields)
            done.append(asset)

    cats = {a: assets[a].get("categories") for a in SOURCES if a in assets and assets[a].get("categories")}
    caps = {m["asset_id"]: m.get("market_cap") for m in db.asset_market_data.find({}, {"_id": 0, "asset_id": 1, "market_cap": 1})}
    for a, (related, basis) in related_from_categories(cats, caps).items():
        db.assets.update_one({"asset_id": a}, {"$set": {"related_assets": related, "related_basis": basis}})
    return {"refreshed": done, "due_left": max(0, len(due) - len(done)) if stopped else 0,
            "related_computed": len(cats), "stopped": stopped}


def run_profile_scheduler(initial_delay_seconds: int = 60) -> None:
    """Daemon-thread loop: a few due profiles every 10 minutes (the whole set fills in within the hour)."""
    from utils.scheduler_gate import claim_run

    time.sleep(initial_delay_seconds)
    while True:
        try:
            if claim_run("asset-profiles", RUN_INTERVAL_SECONDS - 30):
                result = refresh_profiles()
                if result["refreshed"] or result["stopped"]:
                    print(f"[asset-profiles] {result}")
        except Exception as exc:
            from utils.http_errors import redact
            print(f"[asset-profiles] failed: {type(exc).__name__}: {redact(exc)}")
        time.sleep(RUN_INTERVAL_SECONDS)


if __name__ == "__main__":
    print(refresh_profiles(limit=len(SOURCES)))
