"""Response bodies for /predict and /risk (Phase 6a). Pure: no FastAPI, no models, no artifacts.

Reads raw rows for FEATURES only (ewma_vol, vol_30d and ret_1d, all backward-looking): no labels are built and
no metric is computed on any split. Served:
- price: the last-value baseline, prediction_30d = 0 and no predicted price or interval (D35);
- risk: the served volatility config.RISK_VOL_COLUMN, mapped to risk_score by the pooled percentile over its
  history for all assets (D36); sharpe per D37. Since D82 that is persistence vol_30d (D27): the D51 EWMA approval
  was withdrawn under top-only selection (D81). EWMA (ml.features.features.ewma_vol, as in the Phase 9
  evaluation) is still computed and logged for the D46 monitor, but not served;
- signal and confidence: ml.signal.signal_logic.generate_signal (D33).
Staleness is measured from the latest bar's close (its open time + 1 day), when its data became complete (D38).
Every asset passes the serving gate first (D40): its CSV must match a passed validation report, else NotServable.
"""

import math
from collections.abc import Mapping
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.loader import load_raw
from ml.data.serving_gate import NotServable, servable_raw
from ml.evaluation import metrics as m
from ml.evaluation.backtest import percentile_rank
from ml.features.features import build_features, ewma_vol
from ml.signal.signal_logic import generate_signal

BAR = pd.Timedelta(days=1)
DECISIONS_IN_FORCE = ("D6", "D27", "D33", "D35", "D36", "D37", "D38", "D40", "D81", "D82")
NOTE_PRICE = ("No model beats the no-change baseline (D35): prediction_30d is the last-value baseline (0%); "
              "no predicted price or interval.")


def serving_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Feature table (vol_30d is the served persistence measure, D82) plus ewma_vol, computed exactly as in the
    Phase 9 evaluation: ewma_vol of the closes of the feature rows (run_walkforward.dev_data aligns close to the
    feature index). Trailing: closes <= t only."""
    feats = build_features(raw)
    close = raw.sort_values("timestamp").set_index("timestamp")["close"].loc[feats.index]
    feats["ewma_vol"] = ewma_vol(close).to_numpy()
    return feats


def feature_tables(assets=config.ASSETS) -> dict[str, pd.DataFrame]:
    """Serving table of every pooled asset (D36). Refuses all of them if any one fails the serving gate (D40)
    or has a gap in its bars (build_features refuses gaps)."""
    out = {}
    for a in assets:
        raw = servable_raw(a)
        try:
            out[a] = serving_table(raw)
        except ValueError as e:
            raise NotServable(f"{a}: bars cannot be served ({e})") from None
    return out


def iso_utc(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pooled_risk_score(x: float, pool) -> tuple[float, float]:
    """D36: (risk_score, p). p = percentile rank of x in the pool (ties count half); risk_score = 100 x (1 - p)."""
    rank = percentile_rank(pool, x)
    if rank is None:
        raise ValueError("empty pool")
    p = rank / 100
    return 100 * (1 - p), p


def pool_values(feats: Mapping[str, pd.DataFrame], today: pd.Timestamp) -> np.ndarray:
    """The served vol (config.RISK_VOL_COLUMN, D82) of every asset in `feats` on all dates <= today (D36). Later
    rows never enter the pool; warm-up rows without a value are left out."""
    vals = np.concatenate([f.loc[f.index <= today, config.RISK_VOL_COLUMN].to_numpy() for f in feats.values()])
    return vals[~np.isnan(vals)]


def sharpe_trailing(ret_1d: pd.Series) -> float | None:
    """D37: mean / std (ddof=1) of the trailing SHARPE_WINDOW_DAYS daily log returns x sqrt(365), rf 0.

    None if there are fewer returns than the window."""
    r = ret_1d.to_numpy()[-config.SHARPE_WINDOW_DAYS:]
    return m.sharpe(r, config.ANNUALISATION_DAYS) if len(r) == config.SHARPE_WINDOW_DAYS else None


def bar_age_hours(last_bar: pd.Timestamp, now: datetime) -> float:
    """Hours since the latest bar closed (its open time + 1 day)."""
    return (pd.Timestamp(now) - (last_bar + BAR)) / pd.Timedelta(hours=1)


def risk_inputs(asset: str, now: datetime, feats: Mapping[str, pd.DataFrame] | None = None) -> dict:
    """Every input /risk, /predict and /debug use for one asset. `feats` defaults to feature_tables()."""
    feats = feature_tables() if feats is None else feats
    own = feats[asset]
    today = own.index[-1]
    vol = float(own[config.RISK_VOL_COLUMN].iloc[-1])
    pool = pool_values(feats, today)
    score, p = pooled_risk_score(vol, pool)
    age = bar_age_hours(today, now)
    stale = age > config.STALE_DATA_HOURS
    return {
        "last_bar": today.strftime("%Y-%m-%d"), "last_bar_close": iso_utc(today + BAR),
        "age_hours": age, "stale": stale,
        "stale_note": f"data stale: last bar {today.strftime('%Y-%m-%d')}" if stale else None,
        "served_vol_column": config.RISK_VOL_COLUMN, "served_vol": vol,
        "ewma_vol": float(own["ewma_vol"].iloc[-1]), "vol_30d": float(own["vol_30d"].iloc[-1]),  # D46 monitor inputs
        "volatility": vol * math.sqrt(config.ANNUALISATION_DAYS),
        "sharpe_ratio": sharpe_trailing(own["ret_1d"]), "returns_available": len(own),
        "pool_assets": list(feats), "pool_size": len(pool), "p": p, "risk_score": score,
    }


def _note(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _risk_note(feats_assets) -> str:
    names = ", ".join(a.upper() for a in feats_assets)
    if config.RISK_VOL_COLUMN == "ewma_vol":
        return (f"Risk model: EWMA volatility (lambda {config.EWMA_LAMBDA}), which beat 30-day persistence in "
                f"walk-forward and was not worse on the sealed test (D50, D51). risk_score is the percentile of "
                f"today's EWMA volatility among {names} up to today (D36), higher = safer.")
    return (f"Risk measure: 30-day volatility (persistence). No risk model is served: no model beat this simple "
            f"measure under the project's selection rule (D81, D82). risk_score is "
            f"the percentile of today's 30-day volatility among {names} up to today (D36), higher = safer.")


def risk(asset: str, now: datetime, feats: Mapping[str, pd.DataFrame] | None = None) -> dict:
    """RiskResponse body (docs/CONTRACT.md)."""
    x = risk_inputs(asset, now, feats)
    sharpe = x["sharpe_ratio"]
    return {
        "asset": asset.upper(),
        "risk_score": round(x["risk_score"], 6),
        "volatility": round(x["volatility"], 6),
        "sharpe_ratio": None if sharpe is None else round(sharpe, 6),
        "timestamp": iso_utc(now),
        "note": _note(_risk_note(x["pool_assets"]), x["stale_note"]),
    }


def predict(asset: str, now: datetime, feats: Mapping[str, pd.DataFrame] | None = None) -> dict:
    """PredictionResponse body (docs/CONTRACT.md) under D35; signal and confidence from generate_signal (D33)."""
    x = risk_inputs(asset, now, feats)
    sig = generate_signal(asset)
    return {
        "asset": asset.upper(),
        "predicted_price": None,
        "prediction_30d": 0.0,                       # D35: the last-value baseline forecasts no change
        "confidence": sig["confidence"],
        "model_version": config.MODEL_VERSION_PRICE,
        "timestamp": iso_utc(now),
        "lower_bound": None,
        "upper_bound": None,
        "risk_score": round(x["risk_score"], 6),     # the same number as /risk (D36)
        "trend": None,
        "agreement": None,
        "signal": sig["signal"],
        "boosted_confidence": None,
        "ensemble_price": None,
        "note": _note(NOTE_PRICE, sig["note"], x["stale_note"]),
    }


def model_versions() -> dict:
    return {"price": config.MODEL_VERSION_PRICE, "risk": config.MODEL_VERSION_RISK}


def debug(asset: str, now: datetime, feats: Mapping[str, pd.DataFrame] | None = None) -> dict:
    """The inputs behind /predict and /risk (D6: extras only here)."""
    x = risk_inputs(asset, now, feats)
    return {
        "asset": asset.upper(),
        "timestamp": iso_utc(now),
        "inputs": {k: v for k, v in x.items() if k != "stale_note"},
        "stale_after_hours": config.STALE_DATA_HOURS,
        "sharpe_window_days": config.SHARPE_WINDOW_DAYS,
        "served": {"price_model": False, "risk_model": config.RISK_MODEL_SERVED,
                   "direction": config.DIRECTION_SERVED[asset]},
        "model_version": model_versions(),
        "decisions_in_force": list(DECISIONS_IN_FORCE),
    }


def data_last_bars(assets=config.ASSETS) -> dict[str, str | None]:
    """Date of each asset's latest bar; None if its raw file is missing."""
    out = {}
    for a in assets:
        try:
            out[a] = load_raw(a)["timestamp"].iloc[-1].strftime("%Y-%m-%d")
        except FileNotFoundError:
            out[a] = None
    return out
