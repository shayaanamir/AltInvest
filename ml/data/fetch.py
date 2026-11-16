"""Download daily klines from the Binance public API (docs/DATA.md).

    python -m ml.data.fetch --asset btc

Writes {asset}_1d.csv and {asset}_1d.fetch.json (fetch time, source) to config.ML_RAW_DIR (D40; the evaluation
snapshot ml/data/raw unless the ML_RAW_DIR env var is set).
Only fully closed bars are kept. No forward-fill, no interpolation.

Hosts (D95): api.binance.com first, then data-api.binance.vision, Binance's official public market-data mirror
(same /api/v3/klines, same data). The mirror is used only when the main host gives a network error (timeout,
refused connection), which happens intermittently from Docker on the dev machine. An HTTP answer is never
retried on the mirror: a 403/451 still raises FetchBlocked (do not work around a block), and 418/429/5xx are
handled on the host that answered. The URL(s) actually used are recorded in the fetch metadata's `source`.
"""

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from ml import config
from ml.data.loader import COLUMNS, fetch_meta_path, raw_csv_path

KLINES_URL = "https://api.binance.com/api/v3/klines"
KLINES_MIRROR_URL = "https://data-api.binance.vision/api/v3/klines"     # D95: network-error fallback only
KLINES_URLS = (KLINES_URL, KLINES_MIRROR_URL)
INTERVAL = "1d"
LIMIT = 1000
MAX_ATTEMPTS = 5
PAUSE_SEC = 0.5            # between pages; klines(limit=1000) costs 2 of 6000 request weight/min
BLOCKED_STATUSES = {403, 451}


class FetchBlocked(RuntimeError):
    """Region block or forbidden: stop, do not work around it."""


def _request(session: requests.Session, params: dict, urls=KLINES_URLS) -> tuple[requests.Response, str]:
    """GET the first host in `urls` that answers at all; (response, url). A network error moves on to the next
    host; any HTTP answer (even an error status) is returned as is. Raises the last network error if none answer."""
    if not urls:
        raise ValueError("no klines URL given")
    for i, url in enumerate(urls):
        try:
            return session.get(url, params=params, timeout=30), url
        except requests.RequestException as exc:
            if i == len(urls) - 1:
                raise
            print(f"  network error on {url} ({type(exc).__name__}); trying {urls[i + 1]}")
    raise AssertionError("unreachable")


def _get_page(session: requests.Session, symbol: str, start_ms: int, used: set | None = None) -> list:
    """One page of klines. `used` collects the URL(s) that answered (for the metadata's `source`)."""
    params = {"symbol": symbol, "interval": INTERVAL, "startTime": start_ms, "limit": LIMIT}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp, url = _request(session, params)
        except requests.RequestException as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"  network error ({exc}); retry {attempt}/{MAX_ATTEMPTS - 1}")
            time.sleep(2 ** attempt)
            continue
        if resp.status_code in BLOCKED_STATUSES:
            raise FetchBlocked(f"HTTP {resp.status_code} from Binance: {resp.text[:200]}")
        if resp.status_code in (418, 429):          # rate limited: obey Retry-After
            wait = int(resp.headers.get("Retry-After", 2 ** attempt))
            print(f"  HTTP {resp.status_code} rate limit; sleeping {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code >= 500 and attempt < MAX_ATTEMPTS:
            print(f"  HTTP {resp.status_code}; retry {attempt}/{MAX_ATTEMPTS - 1}")
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        if used is not None:
            used.add(url)
        return resp.json()
    raise RuntimeError(f"gave up after {MAX_ATTEMPTS} attempts")


def closed_bars(klines: list, asset: str, now_ms: int) -> list[list]:
    """Convert raw klines to CSV rows, dropping bars whose close time has not passed yet.

    Binance kline: [open_time, open, high, low, close, volume, close_time, ...].
    Price/volume strings are written as received (no float rounding).
    """
    rows = []
    for k in klines:
        if int(k[6]) >= now_ms:
            continue
        ts = datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append([asset, ts, k[1], k[2], k[3], k[4], k[5]])
    return rows


def fetch(asset: str, raw_dir: Path | None = None) -> dict:
    """Download every closed daily bar into raw_dir (default config.ML_RAW_DIR). Returns the fetch metadata."""
    symbol = config.SERVED_ASSET_SYMBOLS[asset]     # D87: served assets (a superset of the evaluated ones)
    session = requests.Session()
    klines, start_ms, pages = [], 0, 0      # startTime=0 -> earliest available bar
    used: set[str] = set()                  # the host(s) that answered
    while True:
        page = _get_page(session, symbol, start_ms, used)
        pages += 1
        klines.extend(page)
        if len(page) < LIMIT:
            break
        start_ms = int(page[-1][0]) + 1
        time.sleep(PAUSE_SEC)

    now_ms = int(time.time() * 1000)
    rows = closed_bars(klines, asset, now_ms)
    raw_csv_path(asset, raw_dir).parent.mkdir(parents=True, exist_ok=True)
    with open(raw_csv_path(asset, raw_dir), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    meta = {
        "asset": asset,
        "symbol": symbol,
        "source": ", ".join(u for u in KLINES_URLS if u in used),     # main host, mirror, or both
        "interval": INTERVAL,
        "fetched_at": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages": pages,
        "bars_received": len(klines),
        "bars_written": len(rows),
        "dropped_unclosed": len(klines) - len(rows),
    }
    fetch_meta_path(asset, raw_dir).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Binance daily klines")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    args = parser.parse_args()
    meta = fetch(args.asset)
    print(json.dumps(meta, indent=2))
    print(f"wrote {raw_csv_path(args.asset)}")


if __name__ == "__main__":
    main()
