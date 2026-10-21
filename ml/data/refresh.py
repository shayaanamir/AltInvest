"""Daily refresh of the SERVING data (D40): fetch, then validate, every asset in config.ASSETS.

    python -m ml.data.refresh            # once; exit 0 if every asset ends servable, else 1
    python -m ml.data.refresh --loop     # once now, then daily at config.REFRESH_UTC until stopped
    python -m ml.data.refresh --force    # also allowed to write to the evaluation snapshot (D40)

Writes only to config.ML_RAW_DIR and config.ML_VALIDATION_DIR, and refuses the evaluation snapshot
(ml/data/raw, ml/reports/data) without --force. Per asset: back up the CSV, its .fetch.json and its validation
report; fetch into a staging folder and validate there (fetch.fetch, validate.build_report). New data must also
have no missing day and must not be shorter or end earlier than the data it replaces. Only a passing set
replaces the served files, each with os.replace (atomic on one filesystem). On any failure all three are restored,
so the asset keeps serving its last good data, with the D38 staleness note once it applies. A lock file stops two
refreshes (the ml service at startup and the ml-refresh sidecar) from running at once.
Writes refresh_status.json (per asset: ok/failed, reason, servable, last bar, time) in ML_VALIDATION_DIR.
"""

import argparse
import json
import os
import shutil
import signal
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ml import config
from ml.data import fetch, validate
from ml.data.loader import fetch_meta_path, load_raw, raw_csv_path
from ml.data.serving_gate import NotServable, servable_raw

STATUS_FILE = "refresh_status.json"
LOCK_FILE = ".refresh.lock"
LOCK_WAIT_SECONDS = 600       # a full refresh of three assets takes well under a minute
LOCK_STALE_SECONDS = 3600     # a lock this old was left by a killed run


class SnapshotProtected(RuntimeError):
    """The serving directories are (inside) the evaluation snapshot and --force was not given (D40)."""


class ValidationFailed(RuntimeError):
    """The fetched data did not pass validation."""


class OlderData(RuntimeError):
    """The fetched data has fewer rows or an earlier last bar than the data it would replace."""


class RefreshBusy(RuntimeError):
    """Another refresh holds the lock."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _inside(path: Path, root: Path) -> bool:
    p, r = Path(path).resolve(), Path(root).resolve()
    return p == r or r in p.parents


def check_targets(force: bool) -> None:
    """D40: never write to the evaluation snapshot without --force."""
    snapshot = (config.EVALUATION_RAW_DIR, config.EVALUATION_VALIDATION_DIR)
    hits = [str(d) for d in (config.ML_RAW_DIR, config.ML_VALIDATION_DIR) if any(_inside(d, s) for s in snapshot)]
    if hits and not force:
        raise SnapshotProtected(f"refusing to write to the evaluation snapshot {hits} (D40); set ML_RAW_DIR and "
                                "ML_VALIDATION_DIR to serving directories, or pass --force")


def next_run(now: datetime, at: str = config.REFRESH_UTC) -> datetime:
    """The first time strictly after `now` that is `at` ("HH:MM") UTC."""
    hh, mm = (int(x) for x in at.split(":"))
    now = now.astimezone(timezone.utc)
    t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)


@contextmanager
def refresh_lock(wait: float = LOCK_WAIT_SECONDS):
    """Exclusive lock file in ML_RAW_DIR; waits up to `wait` seconds, takes over a stale lock."""
    path = config.ML_RAW_DIR / LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > LOCK_STALE_SECONDS:
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RefreshBusy(f"another refresh holds {path}") from None
            time.sleep(1)
    try:
        os.write(fd, f"pid {os.getpid()} since {_iso(_utc_now())}\n".encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _restore(files: dict[str, Path], backups: dict[str, Path]) -> None:
    """Put the previous set back; a file that did not exist before is removed again."""
    for k, p in files.items():
        if backups[k].exists():
            os.replace(backups[k], p)
        else:
            p.unlink(missing_ok=True)


def _current_extent(asset: str) -> tuple[int, pd.Timestamp] | None:
    """(rows, last timestamp) of the CSV now served, or None if there is none or it cannot be read."""
    try:
        df = load_raw(asset)
    except (OSError, ValueError, KeyError):
        return None
    return (len(df), df["timestamp"].max()) if len(df) else None


def check_new_data(report: dict, current: tuple[int, pd.Timestamp] | None) -> None:
    """Gaps and going backwards are failures (Phase 6c): the previous files stay in place."""
    if report["missing_days_count"]:
        raise ValidationFailed(f"{report['missing_days_count']} missing day(s), first {report['missing_days'][0]}")
    if current is not None:
        rows, last = current
        new_last = pd.Timestamp(report["last_timestamp"])
        if report["rows"] < rows or new_last < last:
            raise OlderData(f"new data has {report['rows']} rows ending {new_last.date()}; "
                            f"served data has {rows} rows ending {last.date()}")


def servable_state(asset: str) -> dict:
    try:
        df = servable_raw(asset)
        return {"servable": True, "last_bar": df["timestamp"].max().strftime("%Y-%m-%d"), "rows": len(df)}
    except NotServable as e:
        return {"servable": False, "last_bar": None, "rows": None, "gate": str(e)}


def refresh_asset(asset: str) -> dict:
    """Fetch and validate one asset; replace its served files only if everything passed."""
    files = {"csv": raw_csv_path(asset), "meta": fetch_meta_path(asset), "report": validate.report_path(asset)}
    backups = {k: p.with_name(p.name + ".bak") for k, p in files.items()}
    staging = config.ML_RAW_DIR / f".staging-{asset}"
    tmp_report = files["report"].with_name(files["report"].name + ".tmp")
    shutil.rmtree(staging, ignore_errors=True)
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            shutil.copy2(p, backups[k])
        else:
            backups[k].unlink(missing_ok=True)
    try:
        fetch.fetch(asset, raw_dir=staging)
        report = validate.build_report(asset, raw_dir=staging)
        report["raw_file"] = validate.repo_relative(files["csv"]).as_posix()
        if not report["passed"]:
            raise ValidationFailed(f"checks failed: {[c for c, ok in report['checks'].items() if not ok]}")
        check_new_data(report, _current_extent(asset))
        tmp_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        os.replace(raw_csv_path(asset, staging), files["csv"])
        os.replace(fetch_meta_path(asset, staging), files["meta"])
        os.replace(tmp_report, files["report"])
        result = {"status": "ok", "reason": None}
    except BaseException as e:          # also on SystemExit/KeyboardInterrupt: restore, then re-raise
        _restore(files, backups)
        if not isinstance(e, Exception):
            raise
        result = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        tmp_report.unlink(missing_ok=True)
        for b in backups.values():
            b.unlink(missing_ok=True)
    return {**result, **servable_state(asset), "time": _iso(_utc_now())}


def _write_status(status: dict) -> None:
    out = config.ML_VALIDATION_DIR / STATUS_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
    os.replace(tmp, out)


def run_once(force: bool = False, lock_wait: float = LOCK_WAIT_SECONDS) -> int:
    """Refresh every asset once. 0 if every asset ends servable, else 1."""
    check_targets(force)
    try:
        with refresh_lock(lock_wait):
            assets = {a: refresh_asset(a) for a in config.ASSETS}
    except RefreshBusy as e:
        print(f"refresh skipped: {e}", flush=True)
        return 1
    status = {"decision": "D40", "generated_at": _iso(_utc_now()), "raw_dir": str(config.ML_RAW_DIR),
              "validation_dir": str(config.ML_VALIDATION_DIR), "assets": assets,
              "all_servable": all(s["servable"] for s in assets.values())}
    _write_status(status)
    for a, s in assets.items():
        reason = "" if s["reason"] is None else f" ({s['reason']})"
        served = f"serving last bar {s['last_bar']} ({s['rows']} rows)" if s["servable"] else "NOT servable"
        print(f"{a}: {s['status']}{reason}; {served}", flush=True)
    return 0 if status["all_servable"] else 1


def loop(force: bool) -> None:
    """Refresh now, then daily at config.REFRESH_UTC, until stopped."""
    while True:
        try:
            run_once(force)
        except SnapshotProtected:
            raise
        except Exception as e:                      # keep the daily schedule alive; the error is logged
            print(f"refresh error: {type(e).__name__}: {e}", flush=True)
        wake = next_run(_utc_now())
        print(f"next refresh at {_iso(wake)}", flush=True)
        while (left := (wake - _utc_now()).total_seconds()) > 0:
            time.sleep(min(left, 60))


def _stop(signum, frame):
    raise SystemExit(0)                             # docker stop: restore any half-done asset, release the lock


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the serving data: fetch, then validate (D40)")
    parser.add_argument("--loop", action="store_true", help=f"run now, then daily at {config.REFRESH_UTC} UTC")
    parser.add_argument("--force", action="store_true", help="allow writing to the evaluation snapshot")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _stop)
    try:
        if args.loop:
            loop(args.force)
        sys.exit(run_once(args.force))
    except SnapshotProtected as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
