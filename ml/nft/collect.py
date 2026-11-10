"""Collectors for the NFT data (D54-D56), written to config.ML_NFT_DIR (the live/serving directory).

    python -m ml.nft.collect                    (every stage)
    python -m ml.nft.collect --stage floor      (meta | floor | eth | sales | traits)

Stages are independent and safe to re-run:
  meta    collections.json: name, contract, supply and image per slug (OpenSea)
  floor   floor_points.csv: every all_time floor point, re-read in full (about one point per day)
  eth     eth_1d.csv: Binance ETHUSDT daily bars, by the existing ml.data.fetch (D2)
  sales   sales_raw.csv: sale events since NFT_SALES_START, continued from the last stored sale;
          sales_dropped.csv: events dropped by D56 (other payment token, quantity != 1)
  traits  traits/<slug>.csv and tokens/<slug>.csv from Alchemy, fetched once per collection (static)
Raw API responses are not stored; API keys are never printed.
"""

import argparse
import json
import time

import pandas as pd

from ml import config
from ml.data.fetch import fetch as fetch_bars
from ml.nft import alchemy, sales as sl, store, traits as tr
from ml.nft.opensea import Client

STAGES = ("meta", "floor", "eth", "sales", "traits")
WINDOW_DAYS = 30            # sale events are paged inside windows of this many days
OVERLAP_SECONDS = 3600      # a continued run re-reads the last hour; duplicates are removed
DROPPED_COLUMNS = ["slug", "tx", "token_id", "timestamp", "reason", "payment_symbol"]
INTRADAY_COLUMNS = ["slug", "date", "floor_intraday_median_eth", "n_points"]


def _log(msg: str) -> None:
    print(f"[nft-collect] {msg}", flush=True)


def collect_meta(client: Client) -> dict:
    out = {}
    for slug in config.NFT_SLUGS:
        c = client.collection(slug)
        contracts = [x["address"].lower() for x in c.get("contracts") or [] if x.get("chain") == "ethereum"]
        out[slug] = {"name": c.get("name") or slug, "contract": contracts[0] if contracts else None,
                     "total_supply": c.get("total_supply"), "image_url": c.get("image_url") or "",
                     "description": (c.get("description") or "").strip(),
                     "verified": c.get("safelist_status") == "verified", "created_date": c.get("created_date")}
        if out[slug]["contract"]:
            out[slug]["symbol"] = alchemy.contract_metadata(out[slug]["contract"]).get("symbol")
    path = config.ML_NFT_DIR / "collections.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def load_meta() -> dict:
    return json.loads((config.ML_NFT_DIR / "collections.json").read_text(encoding="utf-8"))


def collect_floor(client: Client) -> pd.DataFrame:
    parts = []
    for slug in config.NFT_SLUGS:
        pts = pd.DataFrame(client.floor_prices(slug, "all_time"))[["time", "token_unit", "usd_price"]]
        parts.append(pts.assign(slug=slug))
        _log(f"floor {slug}: {len(pts)} points")
    out = pd.concat(parts, ignore_index=True)[["slug", "time", "token_unit", "usd_price"]]
    store.write_csv(out, config.ML_NFT_DIR / "floor_points.csv")
    return out


def collect_eth() -> dict:
    return fetch_bars("eth", raw_dir=config.ML_NFT_DIR)


def _existing(name: str, columns: list[str]) -> pd.DataFrame:
    path = config.ML_NFT_DIR / f"{name}.csv"
    return store.read_csv(path) if path.exists() else pd.DataFrame(columns=columns)


def _append(table: pd.DataFrame, rows: list[dict], columns: list[str]) -> pd.DataFrame:
    parts = [p for p in (table, pd.DataFrame(rows, columns=columns)) if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns)


def collect_intraday(client: Client, day: str) -> pd.DataFrame:
    """Display only (D55): the median of yesterday's intraday floor points, kept per (slug, date)."""
    from ml.nft import floor as fl
    rows = []
    for slug in config.NFT_SLUGS:
        pts = pd.DataFrame(client.floor_prices(slug, "one_day"))
        med, n = fl.intraday_median(pts, day) if len(pts) else (None, 0)
        if med is not None:
            rows.append({"slug": slug, "date": day, "floor_intraday_median_eth": med, "n_points": n})
    out = _append(_existing("floor_intraday", INTRADAY_COLUMNS), rows, INTRADAY_COLUMNS)
    out = out.drop_duplicates(["slug", "date"], keep="last").sort_values(["slug", "date"])
    store.write_csv(out, config.ML_NFT_DIR / "floor_intraday.csv")
    return out


def collect_sales(client: Client, now: int | None = None) -> dict:
    """Appends new sale events per collection. Returns {slug: new rows}."""
    now = int(now or time.time())
    have, dropped = _existing("sales_raw", sl.SALE_COLUMNS), _existing("sales_dropped", DROPPED_COLUMNS)
    start0 = int(pd.Timestamp(config.NFT_SALES_START, tz="UTC").timestamp())
    added = {}
    for slug in config.NFT_SLUGS:
        last = have.loc[have["slug"] == slug, "timestamp"]
        after = int(last.max()) - OVERLAP_SECONDS if len(last) else start0 - 1
        rows, drops = [], []
        lo = after
        while lo < now:
            hi = min(lo + WINDOW_DAYS * 86400, now)
            for page in client.sale_events(slug, lo, hi + 1):
                for e in page:
                    row, reason = sl.parse_event(e, slug)
                    if row is not None and row["timestamp"] >= start0:
                        rows.append(row)
                    elif reason:
                        drops.append({"slug": slug, "tx": (e.get("transaction") or "").lower(),
                                      "token_id": str((e.get("nft") or {}).get("identifier") or ""),
                                      "timestamp": int(e.get("event_timestamp") or 0), "reason": reason,
                                      "payment_symbol": (e.get("payment") or {}).get("symbol") or ""})
            lo = hi
        before = len(have)
        have = sl.dedupe(_append(have, rows, sl.SALE_COLUMNS))
        dropped = _append(dropped, drops, DROPPED_COLUMNS).drop_duplicates(["slug", "tx", "token_id", "timestamp"])
        added[slug] = len(have) - before
        store.write_csv(have, config.ML_NFT_DIR / "sales_raw.csv")          # after every collection: resumable
        store.write_csv(dropped, config.ML_NFT_DIR / "sales_dropped.csv")
        _log(f"sales {slug}: +{added[slug]} (dropped events seen: {len(drops)}; calls so far {client.calls})")
    return added


def collect_traits(meta: dict, force: bool = False) -> dict:
    """Traits and tokens per collection; a collection already on disk is skipped (traits are static)."""
    done = {}
    for slug in config.NFT_SLUGS:
        t_path = config.ML_NFT_DIR / "traits" / f"{slug}.csv"
        k_path = config.ML_NFT_DIR / "tokens" / f"{slug}.csv"
        if t_path.exists() and k_path.exists() and not force:
            done[slug] = "kept"
            continue
        tokens, rows = [], []
        for page, _ in alchemy.contract_nfts(meta[slug]["contract"]):
            for nft in page:
                token, trait_rows = tr.parse_token(nft, slug)
                tokens.append(token)
                rows.extend(trait_rows)
        tk = pd.DataFrame(tokens, columns=tr.TOKEN_COLUMNS).drop_duplicates("token_id")
        store.write_csv(pd.DataFrame(rows, columns=tr.TRAIT_COLUMNS), t_path)
        store.write_csv(tk, k_path)
        done[slug] = f"{len(tk)} tokens, {int((tk['n_traits'] == 0).sum())} without traits"
        _log(f"traits {slug}: {done[slug]}")
    return done


def run(stages=STAGES) -> dict:
    out, client = {}, None
    if {"meta", "floor", "sales"} & set(stages):
        client = Client()
    if "meta" in stages:
        out["meta"] = sorted(collect_meta(client))
    if "floor" in stages:
        out["floor_points"] = len(collect_floor(client))
    if "eth" in stages:
        out["eth_bars"] = collect_eth()["bars_written"]
    if "sales" in stages:
        out["sales_added"] = collect_sales(client)
    if "traits" in stages:
        out["traits"] = collect_traits(load_meta())
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect NFT data into ML_NFT_DIR")
    parser.add_argument("--stage", choices=STAGES, action="append")
    print(json.dumps(run(tuple(parser.parse_args().stage or STAGES)), indent=1))


if __name__ == "__main__":
    main()
