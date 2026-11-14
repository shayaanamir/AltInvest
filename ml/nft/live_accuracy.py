"""Live accuracy log of the item value estimates (Phase 10 step 10.9, D85). Monitoring only: nothing here changes
serving.

    python -m ml.nft.live_accuracy --record            log today's served estimates (every token with traits)
    python -m ml.nft.live_accuracy --summarize 2026-11 the monthly summary (only once the month's sales are settled)

RECORD (daily, after the NFT refresh): at time e, the served estimate of every token with known traits, computed by
the same code as the API (ml.serving.nft_items.estimates), with the floor point it used (= B0's prediction at e),
the method, the model version and the rarity decile as of e. One gzip CSV per UTC day under
ML_NFT_DIR/live_accuracy/estimates/ (the serving data volume; never tracked).

MATCH (monthly): each sale of month M that is clean under the training rules (C1-C3 by the request-time code,
W1 and W2 by fv_features.clean_mask) is matched to the latest logged estimate of its token made before the sale and
at most MATCH_HOURS earlier; sales without one are counted as unmatched. W2 looks 30 days ahead, so month M is
summarised only when its last sale is at least SETTLE_DAYS old (on the 1st of month M+2 by the job).
APE = |estimate / price - 1| for the served estimate and for B0 (the logged floor point).

SUMMARY: MdAPE of served vs B0, pooled, by collection and by rarity decile, with counts, written to
config.NFT_LIVE_ACCURACY_DIR/<M>.json and .md (ml/docs/phase10/live_accuracy/). A collection whose served MdAPE is
above B0's in two consecutive summarised months is marked ALERT; nothing switches automatically.
"""

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml import config
from ml.nft import fv_features as fv
from ml.nft import fv_serving

MATCH_HOURS = 48
SETTLE_DAYS = 30
EST_DIR = "live_accuracy/estimates"


def est_dir(directory: Path | None = None) -> Path:
    return Path(directory or config.ML_NFT_DIR) / EST_DIR


def record(now: datetime | None = None, directory: Path | None = None) -> dict:
    """Log the served estimate of every token with traits at `now`."""
    from ml.serving import nft_items
    now = now or datetime.now(timezone.utc)
    t = nft_items.tables(now)
    st = t["items"]["static"]
    pairs = list(zip(st["slug"].astype(str), st["token_id"].astype(str)))
    df = nft_items.estimates(t, pairs, int(now.timestamp()))
    df.insert(0, "logged_at", int(now.timestamp()))
    out = est_dir(directory)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{now.strftime('%Y-%m-%d')}.csv.gz"
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False)
    tmp.replace(path)
    return {"file": str(path), "rows": len(df), "with_estimate": int(df["estimated_value_eth"].notna().sum())}


def load_estimates(first: pd.Timestamp, last: pd.Timestamp, directory: Path | None = None) -> pd.DataFrame:
    frames = []
    for p in sorted(est_dir(directory).glob("*.csv.gz")):
        day = pd.Timestamp(p.name.split(".")[0], tz="UTC")
        if first <= day <= last:
            frames.append(pd.read_csv(p, dtype={"token_id": str, "slug": str}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def month_bounds(month: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(f"{month}-01", tz="UTC")
    return start, start + pd.offsets.MonthBegin(1)


def settled(month: str, now: datetime) -> bool:
    return pd.Timestamp(now) >= month_bounds(month)[1] + pd.Timedelta(days=SETTLE_DAYS)


def match(sales: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    """Each sale with the latest estimate of its token logged strictly before it, within MATCH_HOURS."""
    s = sales.sort_values("timestamp").reset_index(drop=True)
    e = est.dropna(subset=["estimated_value_eth"]).sort_values("logged_at")
    m = pd.merge_asof(s, e, left_on="timestamp", right_on="logged_at", by=["slug", "token_id"],
                      allow_exact_matches=False, direction="backward", tolerance=MATCH_HOURS * 3600)
    m["matched"] = m["logged_at"].notna()
    m["ape_served"] = np.abs(m["estimated_value_eth"] / m["price_eth"] - 1)
    m["ape_b0"] = np.abs(m["floor_eth"] / m["price_eth"] - 1)
    return m


def _stats(g: pd.DataFrame) -> dict:
    ok = g[g["matched"]]
    return {"n_sales": len(g), "n_matched": len(ok),
            "mdape_served": None if ok.empty else float(ok["ape_served"].median()),
            "mdape_b0": None if ok.empty else float(ok["ape_b0"].median())}


def summarize(month: str, now: datetime | None = None, directory: Path | None = None,
              out_dir: Path | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if not settled(month, now):
        raise ValueError(f"{month} is not settled until {month_bounds(month)[1] + pd.Timedelta(days=SETTLE_DAYS)}")
    d = Path(directory or config.ML_NFT_DIR)
    first, end = month_bounds(month)
    ts = int(pd.Timestamp(now).timestamp())
    hist = fv_serving.history_asof(d, ts)
    rows = hist["rows"]
    clean = fv.clean_mask(rows, rows, ts)
    s = rows[clean & (rows["timestamp"] >= int(first.timestamp())) & (rows["timestamp"] < int(end.timestamp()))]
    sales = s[["slug", "token_id", "timestamp", "tx", "price_eth"]].astype({"token_id": str})
    est = load_estimates(first - pd.Timedelta(hours=MATCH_HOURS), end, d)
    if est.empty:
        raise ValueError(f"no logged estimates for {month}")
    m = match(sales, est)
    out = {"month": month, "decision": "D85", "generated_at": pd.Timestamp(now).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "logged_days": sorted(pd.to_datetime(est["logged_at"].unique(), unit="s").strftime("%Y-%m-%d").unique()),
           "rule": "clean sales (C1-C3, W1, W2 settled after 30 days) matched to the latest estimate logged before "
                   f"the sale within {MATCH_HOURS} h; APE = |estimate / price - 1|; B0 = the logged floor point",
           "pooled": _stats(m),
           "by_collection": {k: {**_stats(g), "method": config.NFT_FV_SERVE[k]} for k, g in m.groupby("slug")},
           "by_rarity_decile": {str(int(k)): _stats(g) for k, g in m[m["matched"]].groupby("rarity_decile")},
           "by_model_version": {k: _stats(g) for k, g in m[m["matched"]].groupby("model_version")}}
    out_dir = Path(out_dir or config.NFT_LIVE_ACCURACY_DIR)
    prev = previous(month, out_dir)
    out["alerts"] = alerts(out, prev)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{month}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (out_dir / f"{month}.md").write_text(markdown(out), encoding="utf-8")
    return out


def previous(month: str, out_dir: Path) -> dict | None:
    prev = (pd.Timestamp(f"{month}-01") - pd.offsets.MonthBegin(1)).strftime("%Y-%m")
    p = Path(out_dir) / f"{prev}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def behind(c: dict | None) -> bool:
    return bool(c and c["mdape_served"] is not None and c["mdape_b0"] is not None and c["mdape_served"] > c["mdape_b0"])


def alerts(cur: dict, prev: dict | None) -> dict:
    """ALERT for a collection whose served MdAPE is above B0's in this and the previous summarised month."""
    out = {}
    for k, c in cur["by_collection"].items():
        p = (prev or {}).get("by_collection", {}).get(k)
        out[k] = "ALERT" if behind(c) and behind(p) else ("behind B0" if behind(c) else "ok")
    return out


def _f(x) -> str:
    return "n/a" if x is None else f"{100 * x:.2f}%"


def markdown(s: dict) -> str:
    lines = [f"# Live accuracy {s['month']} (generated by `python -m ml.nft.live_accuracy`; do not edit)", "",
             f"Generated {s['generated_at']}. Monitoring only (D85): nothing changes serving automatically.", "",
             f"Rule: {s['rule']}.", "",
             "| Group | Sales | Matched | MdAPE served | MdAPE B0 (floor) | Status |", "|---|---|---|---|---|---|",
             f"| all | {s['pooled']['n_sales']} | {s['pooled']['n_matched']} | {_f(s['pooled']['mdape_served'])} | "
             f"{_f(s['pooled']['mdape_b0'])} | |"]
    for k, c in s["by_collection"].items():
        lines.append(f"| {k} ({c['method']}) | {c['n_sales']} | {c['n_matched']} | {_f(c['mdape_served'])} | "
                     f"{_f(c['mdape_b0'])} | {s['alerts'][k]} |")
    lines += ["", "| Rarity decile (1 = rarest) | Matched | MdAPE served | MdAPE B0 |", "|---|---|---|---|"]
    for k, c in s["by_rarity_decile"].items():
        lines.append(f"| {k} | {c['n_matched']} | {_f(c['mdape_served'])} | {_f(c['mdape_b0'])} |")
    return "\n".join(lines) + "\n"


def due_months(now: datetime, directory: Path | None = None, out_dir: Path | None = None) -> list[str]:
    """Settled months with logged estimates and no summary yet."""
    files = sorted(est_dir(directory).glob("*.csv.gz"))
    if not files:
        return []
    out_dir = Path(out_dir or config.NFT_LIVE_ACCURACY_DIR)
    months = sorted({p.name[:7] for p in files})
    return [m for m in months if settled(m, now) and not (out_dir / f"{m}.json").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Live accuracy log of item value estimates (D85)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--record", action="store_true")
    g.add_argument("--summarize", metavar="YYYY-MM")
    args = parser.parse_args()
    print(json.dumps(record() if args.record else summarize(args.summarize), indent=1, default=str))


if __name__ == "__main__":
    main()
