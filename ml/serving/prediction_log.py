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
    path = log_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def served_row(asset: str, now: datetime, feats) -> dict:
    """The logged values for one asset: what /predict and /risk returned, plus the inputs live_score needs."""
    x = rs.risk_inputs(asset, now, feats)
    p, r = rs.predict(asset, now, feats), rs.risk(asset, now, feats)
    close = float(rs.servable_raw(asset)["close"].iloc[-1])
    return {"asset": asset, "last_bar": x["last_bar"], "logged_at": rs.iso_utc(now), "close": close,
            "vol_30d": x["vol_30d"], **{k: p[k] for k in FIELDS_PREDICT}, **{k: r[k] for k in FIELDS_RISK}}


def append_served(now: datetime) -> list[str]:
    """Log today's served values for every servable asset; returns the assets added."""
    from ml.data.refresh import check_targets          # lazy: refresh calls this module after it runs
    check_targets(force=False)
    try:
        feats = rs.feature_tables()
    except NotServable as e:
        print(f"prediction log skipped: {e}", flush=True)
        return []
    seen = {(row["asset"], row["last_bar"]) for row in read_log()}
    new = [row for row in (served_row(a, now, feats) for a in config.ASSETS)
           if (row["asset"], row["last_bar"]) not in seen]
    if new:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.writelines(json.dumps(row) + "\n" for row in new)
    return [row["asset"] for row in new]
