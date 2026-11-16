"""
backend/controllers/bootstrap_controller.py

One command that makes a fresh database usable. Every machine running the project has its own MongoDB, and
it starts empty: the live jobs (prices, sentiment, insights, themes) would fill most of it by themselves, but
the coin names, colours and CoinGecko profiles only appear when something creates the `assets` rows, so a
new clone shows "BTC" instead of "Bitcoin", no descriptions, no trending list, no themes.

    docker exec -w /app/backend altinvest-backend python -m controllers.bootstrap_controller

Steps, in dependency order (the app is usable after the first few; the slow profile step is last):

  indexes        the database indexes the backend normally creates at startup (a fresh database without them
                 turned the first price backfill from under a minute into well over an hour)
  coins         the 17 coins' identity rows: id, symbol, name, category, display colour   (db/seed_assets.py)
  nft            the 7 NFT collections' static metadata (names, symbols, supply)           (db/seed_nft.py)
  market         live prices, market caps, all-time highs and 400 days of hourly price history
                 (CoinGecko + Binance)                                           -> trending, charts, AAI inputs
  sentiment      one news-sentiment run for all 15 coins                                    (needs a few minutes of CPU)
  nft_sentiment  one NFT news-sentiment run                                      (Groq if GROQ_API_KEY is set)
  insights       the market-insights feed from the headlines the sentiment runs read
  themes         recurring themes named by the Groq LLM                                    (needs GROQ_API_KEY)
  profiles       CoinGecko description, website, subcategory and related coins for every coin
                 (about 6 minutes: CoinGecko's free tier allows only a few calls a minute)

It writes no made-up numbers. It is safe to run again (every step is idempotent), and like the seed scripts it
refuses a non-local database unless --allow-remote is given. Not covered, because they come from elsewhere:
NFT floor prices and sales (the ML service's first download, which needs OPENSEA_API_KEY / ALCHEMY_API_KEY in
.env); predictions and risk scores (the ML pull, for the 16 coins the ML service serves, ml/docs/DECISIONS.md
D87; DAI has none); and AAI scores (the backend's AAI refresh, from those rows and the sentiment readings).

    --only coins,market      run just these steps        --skip profiles      leave these out
    --allow-remote           allow a non-local database (not recommended)
"""
import path_setup  # noqa: F401

import contextlib
import io
import sys
import time
from datetime import datetime

PROFILE_ROUNDS = 6              # profile fetches are retried this many times when CoinGecko throttles
PROFILE_WAIT_SECONDS = 90       # ...waiting this long between rounds

_sleep = time.sleep             # replaced in tests


def _quiet(fn, *args, **kwargs):
    """Calls `fn` with its prints swallowed (the seeds print one line per coin)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


# Each step returns (status, detail): status is "ok", "partial" or "skipped"; an exception becomes "failed".

def step_indexes():
    from db.indexes import ensure_indexes
    r = ensure_indexes()
    if r["failed"]:
        return "partial", f"{r['created_or_present']} ok; failed: {', '.join(r['failed'])}"
    return "ok", f"{r['created_or_present']} indexes"


def step_coins():
    from db import seed_assets
    _quiet(seed_assets.seed)
    return "ok", f"{len(seed_assets.ASSETS)} coins"


def step_nft():
    from db import seed_nft
    _quiet(seed_nft.seed)
    return "ok", "7 collections"


def step_market():
    from controllers.market_data_controller import refresh_market_snapshot, refresh_prices
    snap = refresh_market_snapshot()
    prices = refresh_prices()
    failed = [a for a, v in prices.items() if isinstance(v, str) and v.startswith("failed")]
    rows = sum(v for v in prices.values() if isinstance(v, int))
    detail = f"{snap['updated']} coins priced, {rows} hourly prices"
    if snap["missing"] or failed:
        return "partial", f"{detail}; missing: {', '.join(sorted(set(snap['missing']) | set(failed)))}"
    return "ok", detail


def step_sentiment():
    from routes.sentiment import _refresh_all_assets
    results = _refresh_all_assets()
    counts = {}
    for outcome in results.values():
        counts[outcome] = counts.get(outcome, 0) + 1
    detail = ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
    return ("ok" if counts.get("failed", 0) == 0 else "partial"), detail


def step_nft_sentiment():
    from controllers.nft_sentiment_controller import refresh_all
    results = refresh_all()
    if "skipped" in results:
        return "skipped", results["skipped"]
    saved = sum(1 for v in results.values() if v == "saved")
    bad = [k for k, v in results.items() if v.startswith("failed") or v == "scoring_unavailable"]
    return ("partial" if bad else "ok"), f"{saved} readings saved, {len(results) - saved} without relevant news"


def step_insights():
    from controllers.insights_controller import refresh_insights
    r = refresh_insights()
    return ("ok" if r["upserted"] else "partial"), f"{r['upserted']} headlines" + ("" if r["upserted"] else " (run `sentiment` first)")


def step_themes():
    from controllers.insights_controller import refresh_themes
    r = refresh_themes()
    if r.get("themes") is None:
        return "skipped", r.get("reason", "no themes")
    return ("ok" if r["themes"] else "partial"), f"{r['themes']} themes from {r.get('from_headlines')} headlines"


def step_profiles():
    from controllers.asset_profile_controller import refresh_profiles
    from controllers.market_data_controller import SOURCES
    filled, last = set(), {}
    for round_no in range(PROFILE_ROUNDS):
        last = refresh_profiles(limit=len(SOURCES))
        filled |= set(last["refreshed"])
        if not last["stopped"]:
            break
        if round_no < PROFILE_ROUNDS - 1:
            _sleep(PROFILE_WAIT_SECONDS)       # CoinGecko throttled us: give it time, then carry on
    if last.get("stopped"):
        return "partial", f"{len(filled)} filled this run; stopped: {last['stopped']} (run it again later)"
    return "ok", f"{len(filled)} filled this run" if filled else "all already filled"


STEPS = [
    ("indexes", "Database indexes (speed)", step_indexes),
    ("coins", "Coin names and colours", step_coins),
    ("nft", "NFT collection details", step_nft),
    ("market", "Live prices and price history", step_market),
    ("sentiment", "News sentiment (15 coins)", step_sentiment),
    ("nft_sentiment", "NFT news sentiment", step_nft_sentiment),
    ("insights", "Market insights", step_insights),
    ("themes", "Themes", step_themes),
    ("profiles", "CoinGecko descriptions and profiles", step_profiles),
]


def run(only=None, skip=(), out=print) -> dict:
    """Runs the chosen steps in order; one failing step never stops the others. Returns {key: (status, detail)}."""
    unknown = (set(only or ()) | set(skip)) - {k for k, _, _ in STEPS}
    if unknown:
        raise ValueError(f"unknown step(s): {', '.join(sorted(unknown))}; choose from {', '.join(k for k, _, _ in STEPS)}")
    results = {}
    chosen = [s for s in STEPS if (not only or s[0] in only) and s[0] not in skip]
    for n, (key, label, fn) in enumerate(chosen, 1):
        out(f"[{datetime.now():%H:%M:%S}] ({n}/{len(chosen)}) {label} ...")
        started = time.monotonic()
        try:
            status, detail = fn()
        except Exception as exc:
            from utils.http_errors import redact
            status, detail = "failed", f"{type(exc).__name__}: {redact(exc)}"
        results[key] = (status, detail)
        out(f"            {status.upper():8} {detail}  ({time.monotonic() - started:.0f}s)")
    return results


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def option(name):
        if name in argv:
            i = argv.index(name)
            return [x for x in argv[i + 1].split(",") if x] if i + 1 < len(argv) else []
        return None

    from db.seed_guard import require_local_target          # same safety rule as every seed script
    require_local_target(["bootstrap", *argv])

    results = run(only=option("--only"), skip=option("--skip") or ())
    print("\nSummary")
    for key, label, _ in STEPS:
        if key in results:
            status, detail = results[key]
            print(f"  {status.upper():8} {label}: {detail}")
    if any(s == "failed" for s, _ in results.values()):
        print("\nSome steps failed; the app still works for what succeeded. Run the command again to retry.")
        return 1
    print("\nDone. Hard-refresh the browser (Ctrl+Shift+R).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
