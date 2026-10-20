"""Download daily klines from the Binance public API (docs/DATA.md).

    python -m ml.data.fetch --asset btc

Writes {asset}_1d.csv and {asset}_1d.fetch.json (fetch time, source) to config.ML_RAW_DIR (D40; the evaluation
snapshot ml/data/raw unless the ML_RAW_DIR env var is set).
Only fully closed bars are kept. No forward-fill, no interpolation.
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
INTERVAL = "1d"
LIMIT = 1000
MAX_ATTEMPTS = 5
PAUSE_SEC = 0.5            # between pages; klines(limit=1000) costs 2 of 6000 request weight/min
BLOCKED_STATUSES = {403, 451}


class FetchBlocked(RuntimeError):
    """Region block or forbidden: stop, do not work around it."""


def _get_page(session: requests.Session, symbol: str, start_ms: int) -> list:
    params = {"symbol": symbol, "interval": INTERVAL, "startTime": start_ms, "limit": LIMIT}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(KLINES_URL, params=params, timeout=30)
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
    symbol = config.ASSET_SYMBOLS[asset]
    session = requests.Session()
    klines, start_ms, pages = [], 0, 0      # startTime=0 -> earliest available bar
    while True:
        page = _get_page(session, symbol, start_ms)
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
        "source": KLINES_URL,
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
