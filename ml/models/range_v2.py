"""Phase 9 range candidates (D42, D49): 80% interval of the h-day log return, h = 30 or 7.

Baseline: vol_30d band = vol_30d x sqrt(h) x the normal 0.10 / 0.90 quantiles (centred on a 0 return).
Candidates: EWMA band (same, with EWMA vol, lambda 0.94; 1 config) and quantile LightGBM (one model per
quantile; a config is the pair; num_leaves 7 or 15). Every bound is a HistorySpec for
ml/evaluation/walkforward_history.py (D48): spec names are '<config>:lo' and '<config>:hi'.
Bounds are log returns; at serving, bound price = last close x exp(bound).
"""

from functools import partial
from statistics import NormalDist

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation.walkforward_history import HistorySpec
from ml.features.features import FEATURE_COLUMNS, ewma_vol
from ml.models.price_v2 import LIGHTGBM_CONFIGS, LIGHTGBM_PARAMS

BASELINE = "vol30_band"
MODEL_CONFIGS = {"ewma_band": ["ewma_band"], "qlgbm": ["qlgbm_l7", "qlgbm_l15"]}
QLGBM_LEAVES = {"qlgbm_l7": "lgbm_l7", "qlgbm_l15": "lgbm_l15"}       # the D42 grid
Z = {side: NormalDist().inv_cdf(q) for side, q in zip(("lo", "hi"), config.RANGE_QUANTILES)}


def _band(vol: np.ndarray, horizon: int, side: str) -> np.ndarray:
    return Z[side] * vol * np.sqrt(horizon)


def _no_fit(train: pd.DataFrame, inputs: pd.DataFrame) -> None:
    return None


def vol30_predict(_, history: pd.DataFrame, rows: range, horizon: int, side: str) -> np.ndarray:
    return _band(history["vol_30d"].to_numpy()[rows.start:rows.stop], horizon, side)


def ewma_predict(_, history: pd.DataFrame, rows: range, horizon: int, side: str) -> np.ndarray:
    """EWMA vol at each row s from closes <= s (ewma_vol is trailing)."""
    vol = ewma_vol(history["close"]).to_numpy()[rows.start:rows.stop]
    return _band(vol, horizon, side)


def qlgbm_fit(train: pd.DataFrame, inputs: pd.DataFrame, config_name: str, horizon: int, side: str):
    import lightgbm
    q = config.RANGE_QUANTILES[0 if side == "lo" else 1]
    model = lightgbm.LGBMRegressor(objective="quantile", alpha=q, **LIGHTGBM_PARAMS,
                                   **LIGHTGBM_CONFIGS[QLGBM_LEAVES[config_name]])
    model.fit(train[FEATURE_COLUMNS].to_numpy(dtype=float), train[f"fwd_return_{horizon}d"].to_numpy())
    return model


def qlgbm_predict(model, history: pd.DataFrame, rows: range) -> np.ndarray:
    return model.predict(history[FEATURE_COLUMNS].to_numpy(dtype=float)[rows.start:rows.stop])


def specs(horizon: int) -> dict[str, HistorySpec]:
    out = {}
    for side in ("lo", "hi"):
        out[f"{BASELINE}:{side}"] = HistorySpec(_no_fit, partial(vol30_predict, horizon=horizon, side=side))
        out[f"ewma_band:{side}"] = HistorySpec(_no_fit, partial(ewma_predict, horizon=horizon, side=side))
        for name in MODEL_CONFIGS["qlgbm"]:
            out[f"{name}:{side}"] = HistorySpec(partial(qlgbm_fit, config_name=name, horizon=horizon, side=side),
                                                qlgbm_predict)
    return out


def declared() -> dict:
    return {"baseline": {BASELINE: "vol_30d x sqrt(h) x normal quantiles", "z": Z},
            "ewma_band": {"lambda": config.EWMA_LAMBDA, "z": Z, "rule": "EWMA vol x sqrt(h) x normal quantiles"},
            "qlgbm": {name: {**LIGHTGBM_PARAMS, **LIGHTGBM_CONFIGS[leaves], "objective": "quantile",
                             "quantiles": list(config.RANGE_QUANTILES)} for name, leaves in QLGBM_LEAVES.items()},
            "centre": "0 return for both bands", "quantiles": list(config.RANGE_QUANTILES)}
