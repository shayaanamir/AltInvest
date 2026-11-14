"""Phase 10 floor-volatility candidates (D59), declared before any run: 1 config per model type.

Reuses the Phase 9 predictors (plan rule 1): persistence vol_30d (baseline), EWMA lambda 0.94 through
ml.features.features.ewma_vol, and the GARCH(1,1) variance recursion and h-day forecast of ml.models.risk_v2.
The only new piece is the GARCH fit with NORMAL errors (D59; Phase 9 used Student-t): parameters from the
fold's TRAIN returns only, recursion through every return up to t (D48). arch is imported inside the fit.
"""

from functools import partial

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation.walkforward_history import HistorySpec
from ml.models import risk_v2

BASELINE = risk_v2.BASELINE
MODEL_CONFIGS = {"ewma": ["ewma"], "garch": ["garch_normal"]}
GARCH_SETTINGS = {**risk_v2.GARCH_SETTINGS, "dist": "normal"}


def garch_fit_normal(train: pd.DataFrame, inputs: pd.DataFrame) -> risk_v2.FittedGarch:
    from arch import arch_model
    r = GARCH_SETTINGS["scale"] * train["ret_1d"].to_numpy(dtype=float)
    res = arch_model(r, mean="Constant", vol="GARCH", p=1, q=1, dist="normal", rescale=False).fit(disp="off")
    p = res.params
    return risk_v2.FittedGarch(float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"]),
                               float("nan"), float(np.var(r - p["mu"])))


def specs(horizon: int = config.HORIZON_DAYS) -> dict[str, HistorySpec]:
    return {BASELINE: HistorySpec(risk_v2._no_fit, risk_v2.persistence_predict),
            "ewma": HistorySpec(risk_v2._no_fit, risk_v2.ewma_predict),
            "garch_normal": HistorySpec(garch_fit_normal, partial(risk_v2.garch_predict, horizon=horizon))}


def declared() -> dict:
    return {"baseline": {BASELINE: "vol_30d of the floor at t (trailing 30 daily log returns)"},
            "ewma": {"lambda": config.EWMA_LAMBDA, "forecast": "EWMA vol at t for every day of the horizon",
                     "function": "ml.features.features.ewma_vol"},
            "garch_normal": {**GARCH_SETTINGS, "fit": "fold train returns only (D48)",
                             "recursion": "through every daily return up to t (D48)",
                             "forecast": "sqrt(mean of the h forecast variances)"}}
