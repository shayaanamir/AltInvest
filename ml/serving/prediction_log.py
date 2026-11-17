"""Forward log of what the API served (Phase 6d): one row per asset per latest bar, on SERVING data only (D40).

After each refresh, append_served() writes that day's /predict and /risk values to
config.ML_VALIDATION_DIR / config.PREDICTION_LOG_FILE (JSON lines). Idempotent: a row whose (asset, last_bar) is
already logged is skipped, so a second refresh on the same day adds nothing. An asset that is not servable is
skipped. Refuses the evaluation snapshot directories, like the refresh. ml.evaluation.live_score scores the rows
once their 30-day horizon has passed.
"""

import json
from datetime import datetime

from ml import config
from ml.data.serving_gate import NotServable
from ml.serving import responses as rs

FIELDS_PREDICT = ("prediction_30d", "signal", "confidence", "model_version")
FIELDS_RISK = ("risk_score", "volatility")


def log_path():
    return config.ML_VALIDATION_DIR / config.PREDICTION_LOG_FILE


def read_log() -> list[dict]:
    """Every logged row. A line that isn't a JSON object (say, half-written when the process was killed) is skipped
    and reported, so one bad line never stops the refresh's logging or the live scorecard (audit G-45 A2)."""
    path = log_path()
    if not path.exists():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"prediction log: skipped corrupt line {n} of {path.name} ({e.msg})", flush=True)
            continue
        if not isinstance(row, dict):
            print(f"prediction log: skipped line {n} of {path.name} (not a JSON object)", flush=True)
            continue
        rows.append(row)
    return rows


def served_row(asset: str, now: datetime, feats) -> dict:
    """The logged values for one asset: what /predict and /risk returned, plus the inputs live_score needs."""
    x = rs.risk_inputs(asset, now, feats)
    p, r = rs.predict(asset, now, feats), rs.risk(asset, now, feats)
    close = float(rs.servable_raw(asset)["close"].iloc[-1])
    return {"asset": asset, "last_bar": x["last_bar"], "logged_at": rs.iso_utc(now), "close": close,
            "vol_30d": x["vol_30d"], "ewma_vol": x["ewma_vol"],            # D46 monitor: EWMA vs persistence (served, D82)
            **{k: p[k] for k in FIELDS_PREDICT}, **{k: r[k] for k in FIELDS_RISK}}


def append_served(now: datetime) -> list[str]:
    """Log today's served values for every servable asset; returns the assets added."""
    from ml.data.refresh import check_targets          # lazy: refresh calls this module after it runs
    check_targets(force=False)
    try:
        feats = rs.feature_tables()
    except NotServable as e:
        print(f"prediction log skipped: {e}", flush=True)
        return []
    seen = {(row.get("asset"), row.get("last_bar")) for row in read_log()}
    new = [row for row in (served_row(a, now, feats) for a in config.ASSETS)
           if (row["asset"], row["last_bar"]) not in seen]
    if new:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # A write cut off mid-line leaves no newline: start on a fresh line so the new rows stay readable (G-45 A2).
        broken_tail = path.exists() and path.stat().st_size > 0 and not path.read_bytes().endswith(b"\n")
        with path.open("a", encoding="utf-8") as f:
            if broken_tail:
                f.write("\n")
            f.writelines(json.dumps(row) + "\n" for row in new)
    return [row["asset"] for row in new]
