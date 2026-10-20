"""
db/enrich_asset_profiles.py

Fills in the Asset Detail "About" fields an asset row is missing (description, website, all-time
high and its date) from CoinGecko's public API, which needs no key. Existing values are never
overwritten, and each filled row is marked profile_source: "coingecko".

The CoinGecko coin is the one whose symbol matches exactly and has the best market-cap rank
(so "ADA" is Cardano, not a token that borrowed the ticker). The free API allows only a few calls a
minute, so the script pauses between assets.

Run:  python db/enrich_asset_profiles.py            (writes to the database)
      python db/enrich_asset_profiles.py --dry-run  (prints what it would write)
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import re
import time
import html

import httpx

from db.mongo_connection import get_db

API = "https://api.coingecko.com/api/v3"
PAUSE_SECONDS = 7          # stays under the free tier's rate limit
MAX_SENTENCES = 3


def _short_description(raw: str) -> str | None:
    text = html.unescape(re.sub(r"<[^>]+>", "", raw or "")).strip()
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:MAX_SENTENCES]).strip()


def _coin_id(client: httpx.Client, symbol: str) -> str | None:
    coins = client.get(f"{API}/search", params={"query": symbol}).raise_for_status().json().get("coins", [])
    exact = [c for c in coins if (c.get("symbol") or "").upper() == symbol.upper() and c.get("market_cap_rank")]
    exact.sort(key=lambda c: c["market_cap_rank"])
    return exact[0]["id"] if exact else None


def fetch_profile(client: httpx.Client, symbol: str) -> dict | None:
    coin_id = _coin_id(client, symbol)
    if not coin_id:
        return None
    time.sleep(PAUSE_SECONDS)
    d = client.get(f"{API}/coins/{coin_id}", params={
        "localization": "false", "tickers": "false", "market_data": "true",
        "community_data": "false", "developer_data": "false", "sparkline": "false",
    }).raise_for_status().json()
    homepage = next((u for u in (d.get("links") or {}).get("homepage", []) if u), None)
    md = d.get("market_data") or {}
    ath = (md.get("ath") or {}).get("usd")
    ath_date = ((md.get("ath_date") or {}).get("usd") or "")[:10] or None
    return {
        "description": _short_description((d.get("description") or {}).get("en")),
        "website": homepage,
        "all_time_high": ath,
        "ath_date": ath_date,
        "coingecko_id": coin_id,
    }


def main(dry_run: bool = False):
    db = get_db()
    wanted = ("description", "website", "all_time_high", "ath_date")
    todo = [a for a in db.assets.find({}, {"_id": 0}) if any(not a.get(f) for f in wanted)]
    print(f"[profiles] {len(todo)} asset(s) missing About fields")
    with httpx.Client(timeout=20, headers={"accept": "application/json"}) as client:
        for n, a in enumerate(todo):
            if n:
                time.sleep(PAUSE_SECONDS)
            sym = a["asset_id"]
            try:
                profile = fetch_profile(client, sym)
            except Exception as exc:
                print(f"  {sym}: skipped ({type(exc).__name__}: {exc})")
                continue
            if not profile:
                print(f"  {sym}: no CoinGecko match")
                continue
            update = {f: profile[f] for f in wanted if not a.get(f) and profile.get(f) is not None}
            if not update:
                print(f"  {sym}: nothing new")
                continue
            update.update({"profile_source": "coingecko", "coingecko_id": profile["coingecko_id"]})
            print(f"  {sym}: {'would set' if dry_run else 'set'} {sorted(k for k in update if k in wanted)}")
            if dry_run:
                print(f"     {update}")
            else:
                db.assets.update_one({"asset_id": sym}, {"$set": update})


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
