"""Live (forward) scorecard (Phase 6d): how the values the API served on day t turned out 30 days later.

    python -m ml.evaluation.live_score       (serving directories only; refuses the evaluation snapshot, D40)

Reads ml.serving.prediction_log rows and the servable raw bars (serving gate, D40). A row dated t is scored only
when the bar t + HORIZON_DAYS exists; the realised values use bars t+1..t+30 only, through the label functions
(labels.fwd_return_30d, labels.fwd_vol_30d), so no bar after t+30 is read. Until a row's horizon has passed it is
counted as pending and nothing is scored; no number is invented. The served values equal the baselines today
(D27, D35), so the served error IS the baseline error; once a model is served this shows the difference.
Writes config.ML_VALIDATION_DIR / config.LIVE_SCORECARD_FILE.
"""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.serving_gate import NotServable, servable_raw
from ml.evaluation import metrics as m
from ml.labels.labels import fwd_return_30d, fwd_vol_30d
from ml.serving.prediction_log import read_log

MIN_ROWS_SPEARMAN = 3


def realised(close: pd.Series) -> pd.DataFrame:
    """Realised forward log return and vol for every bar of a close series indexed by bar date."""
    return pd.DataFrame({"ret": fwd_return_30d(close), "vol": fwd_vol_30d(close)})


def score_rows(rows: list[dict], closes: dict[str, pd.Series]) -> list[dict]:
    """Each logged row with its realised values, or pending if bar t+30 is not in `closes` yet."""
    real = {a: realised(c) for a, c in closes.items()}
    out = []
    for row in rows:
        t = pd.Timestamp(row["last_bar"], tz="UTC")
        r = real.get(row["asset"])
        if r is None or t not in r.index or pd.isna(r.at[t, "ret"]):
            out.append({**row, "status": "pending", "scorable_from": (t + pd.Timedelta(days=config.HORIZON_DAYS))
                        .strftime("%Y-%m-%d")})
            continue
        forecast = float(np.log1p(row["prediction_30d"] / 100))          # served percent -> log return
        out.append({**row, "status": "scored", "realised_log_return": float(r.at[t, "ret"]),
                    "realised_vol_30d": float(r.at[t, "vol"]), "forecast_log_return": forecast})
    return out


def _summary(scored: list[dict]) -> dict:
    n = len(scored)
    if n == 0:
        return {"n_scored": 0}
    ret = np.array([r["realised_log_return"] for r in scored])
    fc = np.array([r["forecast_log_return"] for r in scored])
    vol = np.array([r["realised_vol_30d"] for r in scored])
    vol_t = np.array([r["vol_30d"] for r in scored])
    calls = [r for r in scored if r["signal"] in ("BUY", "SELL")]
    hits = [(r["signal"] == "BUY") == (r["realised_log_return"] > 0) for r in calls]
    return {
        "n_scored": n,
        "price_mae_log_return_served": m.mae(fc, ret),
        "price_mae_log_return_last_value": m.mae(np.zeros(n), ret),
        "mean_realised_log_return": float(ret.mean()),
        "risk_mae_vol_persistence": m.mae(vol_t, vol),
        "risk_spearman_persistence": m.spearman(vol_t, vol) if n >= MIN_ROWS_SPEARMAN else None,
        "direction_calls": len(calls),
        "direction_hit_rate": float(np.mean(hits)) if calls else None,
    }


def build(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rows = read_log()
    closes = {}
    for a in config.ASSETS:
        try:
            raw = servable_raw(a)
            closes[a] = raw.set_index("timestamp")["close"]
        except NotServable:
            pass                                        # its rows stay pending
    scored = score_rows(rows, closes)
    done = [r for r in scored if r["status"] == "scored"]
    pending = [r for r in scored if r["status"] == "pending"]
    per_asset = {a: _summary([r for r in done if r["asset"] == a]) for a in config.ASSETS}
    note = ("No logged prediction has reached its 30-day horizon yet; nothing is scored." if not done else
            "Served values equal the baselines (D27, D33, D35), so served error = baseline error.")
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_logged": len(rows), "n_scored": len(done), "n_pending": len(pending),
        "first_scorable": min((r["scorable_from"] for r in pending), default=None),
        "all_assets": _summary(done), "per_asset": per_asset, "note": note,
        "horizon_days": config.HORIZON_DAYS, "source": str(config.ML_VALIDATION_DIR / config.PREDICTION_LOG_FILE),
    }


def main() -> None:
    from ml.data.refresh import SnapshotProtected, check_targets
    try:
        check_targets(force=False)
    except SnapshotProtected as e:
        raise SystemExit(str(e)) from None
    card = build()
    out = config.ML_VALIDATION_DIR / config.LIVE_SCORECARD_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(f"wrote {out}: {card['n_scored']} scored, {card['n_pending']} pending")


if __name__ == "__main__":
    main()
