"""Tests for the serving-data refresh and the configurable data paths (Phase 6b, D40).

All fixtures are HAND-MADE bars (a small wobble plus clustered jumps, so they pass validation), NOT market data.
fetch.fetch is monkeypatched, so there are no network calls. Every test works in temporary directories; the
evaluation snapshot is replaced by a temporary stand-in, so a bug can never write to ml/data/raw.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

from ml import config
from ml.data import fetch, refresh, validate
from ml.data.loader import COLUMNS, fetch_meta_path, raw_csv_path

REPO_ROOT = Path(config.__file__).resolve().parent.parent


def _bars(asset: str, n: int) -> pd.DataFrame:
    """Hand-made daily bars: log returns 0.002 x sin(1.7 i), with +6% / -5% jumps on 3 days out of every 40."""
    i = np.arange(n)
    r = 0.002 * np.sin(i * 1.7)
    big = (i % 40) < 3
    r[big] = np.where(i[big] % 2 == 0, 0.06, -0.05)
    close = 100 * np.exp(np.cumsum(r))
    ts = pd.Timestamp("2025-09-13", tz="UTC") + pd.to_timedelta(i, unit="D")
    return pd.DataFrame({"asset": asset, "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "open": close,
                         "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1000.0})[COLUMNS]


def fake_fetch(n: int = 400, fail: Exception | None = None, edit=None, calls: list | None = None):
    """Stand-in for fetch.fetch: writes hand-made bars (optionally edited) to raw_dir, or raises `fail`."""
    def _fetch(asset, raw_dir=None):
        if calls is not None:
            calls.append(asset)
        if fail is not None:
            raise fail
        df = _bars(asset, n) if edit is None else edit(_bars(asset, n))
        raw_csv_path(asset, raw_dir).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(raw_csv_path(asset, raw_dir), index=False)
        meta = {"asset": asset, "source": "hand-made fixture", "fetched_at": "2026-10-21T00:05:00Z"}
        fetch_meta_path(asset, raw_dir).write_text(json.dumps(meta), encoding="utf-8")
        return meta
    return _fetch


@pytest.fixture
def dirs(monkeypatch, tmp_path):
    """Serving directories in tmp_path; the evaluation snapshot is a separate temporary stand-in."""
    raw, val = tmp_path / "serving" / "raw", tmp_path / "serving" / "validation"
    monkeypatch.setattr(config, "ML_RAW_DIR", raw)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", val)
    monkeypatch.setattr(config, "EVALUATION_RAW_DIR", tmp_path / "snapshot" / "raw")
    monkeypatch.setattr(config, "EVALUATION_VALIDATION_DIR", tmp_path / "snapshot" / "reports")
    return raw, val


def _files(raw, val) -> dict[str, bytes]:
    paths = [p for a in config.ASSETS for p in (raw / f"{a}_1d.csv", raw / f"{a}_1d.fetch.json",
                                                 val / f"{a}_validation.json")]
    return {p.name: p.read_bytes() for p in paths if p.exists()}


def _status(val) -> dict:
    return json.loads((val / refresh.STATUS_FILE).read_text(encoding="utf-8"))


def test_refresh_replaces_with_a_validated_set(monkeypatch, dirs):
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    s = _status(val)
    assert s["all_servable"] and set(s["assets"]) == set(config.ASSETS)
    for a in config.ASSETS:
        assert s["assets"][a] | {"time": None} == {"status": "ok", "reason": None, "servable": True,
                                                   "last_bar": "2026-10-17", "rows": 400, "time": None}
        report = json.loads(validate.report_path(a).read_text(encoding="utf-8"))
        assert report["passed"] and report["rows"] == 400 and report["last_timestamp"] == "2026-10-17T00:00:00Z"
    leftovers = [p.name for d in (raw, val) for p in d.iterdir()
                 if p.name.startswith(".") or p.suffix in (".bak", ".tmp")]
    assert leftovers == []                          # no staging folder, backup, temp file or lock left behind


@pytest.mark.parametrize("error", [fetch.FetchBlocked("HTTP 451 from Binance"), requests.ConnectionError("down")])
def test_fetch_failure_restores_csv_meta_and_report(monkeypatch, dirs, error):
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    before = _files(raw, val)
    monkeypatch.setattr(fetch, "fetch", fake_fetch(401, fail=error))
    assert refresh.run_once() == 0                  # still servable: the previous data was restored
    assert _files(raw, val) == before and len(before) == 9
    a = _status(val)["assets"]["btc"]
    assert a["status"] == "failed" and a["reason"].startswith(type(error).__name__) and a["servable"]
    assert a["last_bar"] == "2026-10-17"


def test_validation_failure_restores_csv_meta_and_report(monkeypatch, dirs):
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    before = _files(raw, val)

    def bad_high(df):                               # one row with high below close: fails ohlc_consistent
        df.loc[10, "high"] = df.loc[10, "close"] * 0.5
        return df

    monkeypatch.setattr(fetch, "fetch", fake_fetch(401, edit=bad_high))
    assert refresh.run_once() == 0
    assert _files(raw, val) == before
    assert _status(val)["assets"]["eth"]["reason"] == "ValidationFailed: checks failed: ['ohlc_consistent']"


def test_failure_while_replacing_restores_the_previous_set(monkeypatch, dirs):
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    before = _files(raw, val)
    real_replace = os.replace

    def flaky_replace(src, dst):                    # the CSV and meta are already replaced when the report fails
        if str(src).endswith("_validation.json.tmp"):
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(fetch, "fetch", fake_fetch(401))
    monkeypatch.setattr(refresh.os, "replace", flaky_replace)
    assert refresh.run_once() == 0
    assert _files(raw, val) == before


def test_failure_with_no_previous_data_leaves_nothing_and_exits_1(monkeypatch, dirs):
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(fail=fetch.FetchBlocked("HTTP 451")))
    assert refresh.run_once() == 1
    assert _files(raw, val) == {}
    s = _status(val)
    assert not s["all_servable"] and s["assets"]["sol"]["servable"] is False
    assert "is missing" in s["assets"]["sol"]["gate"]


@pytest.mark.parametrize("target", ["raw", "validation", "inside_raw"])
def test_refuses_the_evaluation_snapshot_without_force(monkeypatch, dirs, target):
    calls = []
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400, calls=calls))
    snap_raw, snap_val = config.EVALUATION_RAW_DIR, config.EVALUATION_VALIDATION_DIR
    if target == "raw":
        monkeypatch.setattr(config, "ML_RAW_DIR", snap_raw)
    elif target == "validation":
        monkeypatch.setattr(config, "ML_VALIDATION_DIR", snap_val)
    else:
        monkeypatch.setattr(config, "ML_RAW_DIR", snap_raw / "serving")
    with pytest.raises(refresh.SnapshotProtected):
        refresh.run_once()
    monkeypatch.setattr(sys, "argv", ["refresh"])
    monkeypatch.setattr(refresh.signal, "signal", lambda *args: None)     # keep pytest's own SIGTERM handler
    with pytest.raises(SystemExit, match="refusing to write to the evaluation snapshot"):
        refresh.main()
    assert calls == [] and not snap_raw.exists() and not snap_val.exists()
    assert refresh.run_once(force=True) == 0 and calls == list(config.ASSETS)


def test_lock_busy_skips_and_stale_lock_is_taken_over(monkeypatch, dirs):
    raw, _ = dirs
    calls = []
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400, calls=calls))
    lock = raw / refresh.LOCK_FILE
    raw.mkdir(parents=True)
    lock.write_text("pid 1\n")
    assert refresh.run_once(lock_wait=0) == 1 and calls == []
    old = lock.stat().st_mtime - refresh.LOCK_STALE_SECONDS - 10
    os.utime(lock, (old, old))
    assert refresh.run_once(lock_wait=0) == 0 and calls == list(config.ASSETS)
    assert not lock.exists()


@pytest.mark.parametrize("now, expected", [
    ("2026-10-21T00:04:59+00:00", "2026-10-21T00:05:00+00:00"),     # before 00:05: today
    ("2026-10-21T00:05:00+00:00", "2026-10-22T00:05:00+00:00"),     # exactly 00:05: it just ran, so tomorrow
    ("2026-10-21T13:00:00+00:00", "2026-10-22T00:05:00+00:00"),     # after 00:05: tomorrow
    ("2026-12-31T23:59:00+00:00", "2027-01-01T00:05:00+00:00"),     # year end
    ("2026-10-21T05:30:00+05:30", "2026-10-21T00:05:00+00:00"),     # IST input = 00:00 UTC
])
def test_next_run_by_hand(now, expected):
    assert refresh.next_run(datetime.fromisoformat(now), "00:05") == datetime.fromisoformat(expected)
    assert refresh.next_run(datetime.fromisoformat(now)).tzinfo == timezone.utc


PRINT_PATHS = ("from ml import config; from ml.data.loader import raw_csv_path; from ml.data.validate import "
               "report_path; print(config.ML_RAW_DIR); print(config.ML_VALIDATION_DIR); "
               "print(raw_csv_path('btc').parent); print(report_path('btc').parent)")


def _paths_in_subprocess(**env_vars) -> list[Path]:
    env = {k: v for k, v in os.environ.items() if k not in ("ML_RAW_DIR", "ML_VALIDATION_DIR")} | env_vars
    out = subprocess.run([sys.executable, "-c", PRINT_PATHS], cwd=REPO_ROOT, env=env, capture_output=True,
                         text=True, check=True).stdout
    return [Path(line).resolve() for line in out.splitlines()]


def test_data_paths_default_to_the_snapshot_dirs_when_env_unset(tmp_path):
    raw, val = (REPO_ROOT / "ml" / "data" / "raw").resolve(), (REPO_ROOT / "ml" / "reports" / "data").resolve()
    assert _paths_in_subprocess() == [raw, val, raw, val]
    assert _paths_in_subprocess(ML_RAW_DIR="", ML_VALIDATION_DIR="") == [raw, val, raw, val]
    r, v = (tmp_path / "r").resolve(), (tmp_path / "v").resolve()
    assert _paths_in_subprocess(ML_RAW_DIR=str(r), ML_VALIDATION_DIR=str(v)) == [r, v, r, v]


def _drop_row(i: int):
    return lambda df: df.drop(index=i).reset_index(drop=True)


def _shift_days(days: int):
    def shift(df):
        ts = pd.to_datetime(df["timestamp"], utc=True) - pd.Timedelta(days=days)
        return df.assign(timestamp=ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return shift


@pytest.mark.parametrize("n, edit, reason", [
    (401, _drop_row(200), "ValidationFailed: 1 missing day(s), first 2026-04-01T00:00:00Z"),   # longer, but a gap
    (399, None, "OlderData: new data has 399 rows ending 2026-10-16; served data has 400 rows ending 2026-10-17"),
    (400, _drop_row(0), "OlderData: new data has 399 rows ending 2026-10-17;"),               # fewer rows only
    (402, _shift_days(3), "OlderData: new data has 402 rows ending 2026-10-16;"),             # earlier last bar only
])
def test_refresh_rejects_gaps_and_older_data(monkeypatch, dirs, n, edit, reason):
    """Phase 6c: the previous CSV, meta and report stay in place, and the reason is recorded."""
    raw, val = dirs
    monkeypatch.setattr(fetch, "fetch", fake_fetch(400))
    assert refresh.run_once() == 0
    before = _files(raw, val)
    monkeypatch.setattr(fetch, "fetch", fake_fetch(n, edit=edit))
    assert refresh.run_once() == 0                  # still servable on the previous data
    assert _files(raw, val) == before and len(before) == 9
    a = _status(val)["assets"]["btc"]
    assert a["status"] == "failed" and a["reason"].startswith(reason) and a["servable"] and a["rows"] == 400
    monkeypatch.setattr(fetch, "fetch", fake_fetch(401))      # control: longer and later data is accepted
    assert refresh.run_once() == 0 and _status(val)["assets"]["btc"]["rows"] == 401
