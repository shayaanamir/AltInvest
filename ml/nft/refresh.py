"""Daily refresh of the NFT serving data (plan step 10.2; the same pattern as ml.data.refresh, D40).

    python -m ml.nft.refresh            (once)
    python -m ml.nft.refresh --loop     (now, then daily at config.NFT_REFRESH_UTC; after each refresh the
                                         fair-value jobs run: monthly refit D83, live accuracy log D85)
    python -m ml.nft.refresh --cycle    (one refresh plus the fair-value jobs; what --loop runs each day)

The loop runs every cycle in a child process, so the memory of the refresh, the refit and the live log (about
0.5 GB) is returned when the cycle ends; the waiting loop itself holds only the interpreter (10.9b).

Writes only to config.ML_NFT_DIR and refuses a directory inside the frozen snapshots (D62). Each stage runs
on its own: a stage that fails leaves its previous files in place and the others still run. New floor data
that is shorter or older than what is stored is rejected. The result of every run is written to
nft_refresh_status.json in ML_NFT_DIR. Keys come from the environment (or .env) and are never printed.
"""

import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ml import config
from ml.data.refresh import next_run
from ml.nft import collect, store
from ml.nft.opensea import Client

STATUS_FILE = "nft_refresh_status.json"


class SnapshotProtected(RuntimeError):
    """The target directory is inside the frozen evaluation snapshots."""


class OlderData(ValueError):
    """New floor data has fewer points or an earlier last point than the stored file."""


def check_target() -> None:
    target, root = Path(config.ML_NFT_DIR).resolve(), config.NFT_SNAPSHOT_ROOT.resolve()
    if target == root or root in target.parents:
        raise SnapshotProtected(f"refusing to write to the NFT evaluation snapshots {target} (D62); set ML_NFT_DIR "
                                "to a serving directory")


def refresh_floor(client: Client) -> int:
    path = config.ML_NFT_DIR / "floor_points.csv"
    old = store.read_csv(path) if path.exists() else None
    backup = path.read_bytes() if old is not None else None
    new = collect.collect_floor(client)
    if old is not None and (len(new) < len(old) or new["time"].max() < old["time"].max()):
        path.write_bytes(backup)
        raise OlderData(f"new floor data has {len(new)} points ending {new['time'].max():.0f}; stored has "
                        f"{len(old)} ending {old['time'].max():.0f}; kept the stored file")
    return len(new)


def run_once(now: datetime | None = None) -> dict:
    """Runs every stage; returns and writes the status. Never raises for a failed stage."""
    check_target()
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    config.ML_NFT_DIR.mkdir(parents=True, exist_ok=True)
    stages, client = {}, None

    def stage(name, fn):
        try:
            stages[name] = {"status": "ok", "result": fn()}
        except Exception as exc:                                # keep the previous files; report the reason
            stages[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        print(f"[nft-refresh] {name}: {stages[name]['status']}", flush=True)

    try:
        client = Client()
    except Exception as exc:
        stages["client"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    if client is not None:
        if not (config.ML_NFT_DIR / "collections.json").exists():
            stage("meta", lambda: sorted(collect.collect_meta(client)))
        stage("floor", lambda: refresh_floor(client))
        stage("intraday", lambda: len(collect.collect_intraday(client, today)))
        stage("sales", lambda: collect.collect_sales(client, int(now.timestamp())))
    stage("eth", lambda: collect.collect_eth()["bars_written"])
    if (config.ML_NFT_DIR / "collections.json").exists():
        stage("traits", lambda: collect.collect_traits(collect.load_meta()))
    status = {"ran_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "stages": stages,
              "all_ok": all(s["status"] == "ok" for s in stages.values())}
    (config.ML_NFT_DIR / STATUS_FILE).write_text(json.dumps(status, indent=1, default=str), encoding="utf-8")
    return status


def cycle() -> None:
    from ml.nft import fv_jobs
    run_once()
    try:
        fv_jobs.after_refresh()
    except Exception as exc:                                    # the jobs report their own failures
        print(f"[nft-refresh] fair-value jobs failed: {type(exc).__name__}: {exc}", flush=True)


def loop(run=subprocess.run) -> None:
    while True:
        code = run([sys.executable, "-m", "ml.nft.refresh", "--cycle"]).returncode
        print(f"[nft-refresh] cycle exited with {code}", flush=True)
        wake = next_run(datetime.now(timezone.utc), config.NFT_REFRESH_UTC)
        print(f"[nft-refresh] next refresh at {wake.strftime('%Y-%m-%dT%H:%M:%SZ')}", flush=True)
        while (left := (wake - datetime.now(timezone.utc)).total_seconds()) > 0:
            time.sleep(min(left, 60))


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the NFT serving data")
    parser.add_argument("--loop", action="store_true", help=f"run now, then daily at {config.NFT_REFRESH_UTC} UTC")
    parser.add_argument("--cycle", action="store_true", help="one refresh plus the fair-value jobs (used by --loop)")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        if args.loop:
            loop()
        if args.cycle:
            cycle()
            sys.exit(0)
        status = run_once()
    except SnapshotProtected as exc:
        sys.exit(str(exc))
    print(json.dumps({k: v["status"] for k, v in status["stages"].items()}))
    sys.exit(0 if status["all_ok"] else 1)


if __name__ == "__main__":
    main()
