"""Phase 9 risk candidates (D42, D49): forecast of the realised daily volatility over the next h days.

Target: fwd_vol_{h}d (std of the h daily log returns after t; D24 uses its log). Baseline: persistence vol_30d.
Candidates (1 config each): EWMA vol (lambda 0.94) and GARCH(1,1) with Student-t errors. GARCH (D48):
parameters are fitted on the fold's TRAIN returns only; the conditional-variance recursion then runs through
every daily return up to row s, and the prediction is sqrt of the mean forecast variance over days s+1..s+h.
All are HistorySpecs for ml/evaluation/walkforward_history.py. arch is imported inside the fit.
"""

from dataclasses import dataclass
from functools import partial

import numpy as np
import pandas as pd

from ml import config
from ml.evaluation.walkforward_history import HistorySpec
from ml.features.features import ewma_vol

BASELINE = "persistence_vol30"
MODEL_CONFIGS = {"ewma": ["ewma"], "garch": ["garch_t"]}
GARCH_SETTINGS = {"mean": "Constant", "vol": "GARCH", "p": 1, "q": 1, "dist": "t", "rescale": False,
                  "scale": 100.0, "recursion_start": "variance of the train residuals at feature row 0"}


@dataclass
class FittedGarch:
    mu: float
    omega: float
    alpha: float
    beta: float
    nu: float
    sigma2_start: float                                         # in (scale x return)^2 units


def _no_fit(train: pd.DataFrame, inputs: pd.DataFrame) -> None:
    return None


def persistence_predict(_, history: pd.DataFrame, rows: range) -> np.ndarray:
    return history["vol_30d"].to_numpy()[rows.start:rows.stop]


def ewma_predict(_, history: pd.DataFrame, rows: range) -> np.ndarray:
    return ewma_vol(history["close"]).to_numpy()[rows.start:rows.stop]


def garch_fit(train: pd.DataFrame, inputs: pd.DataFrame) -> FittedGarch:
    """Parameters from the fold's TRAIN rows' daily returns only (ret_1d, known at each train row)."""
    from arch import arch_model
    s = GARCH_SETTINGS["scale"]
    r = s * train["ret_1d"].to_numpy(dtype=float)
    res = arch_model(r, mean="Constant", vol="GARCH", p=1, q=1, dist="t", rescale=False).fit(disp="off")
    p = res.params
    resid = r - p["mu"]
    return FittedGarch(float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"]),
                       float(p["nu"]), float(np.var(resid)))


def garch_variances(m: FittedGarch, returns: np.ndarray) -> np.ndarray:
    """sigma2_next[t] = conditional variance for day t+1 given returns <= t (scaled units)."""
    e2 = (GARCH_SETTINGS["scale"] * returns - m.mu) ** 2
    out = np.empty(len(e2))
    s2 = m.sigma2_start
    for t in range(len(e2)):
        s2 = m.omega + m.alpha * e2[t] + m.beta * s2
        out[t] = s2
    return out


def garch_predict(m: FittedGarch, history: pd.DataFrame, rows: range, horizon: int) -> np.ndarray:
    """sqrt(mean of the forecast variances for days s+1..s+h), back in daily log-return units."""
    nxt = garch_variances(m, history["ret_1d"].to_numpy(dtype=float))[rows.start:rows.stop]
    persist = m.alpha + m.beta
    k = np.arange(horizon)                                      # step k+1: omega x sum persist^j + persist^k x next
    geo = np.array([np.sum(persist ** np.arange(i)) for i in k])
    paths = m.omega * geo[None, :] + (persist ** k)[None, :] * nxt[:, None]
    return np.sqrt(paths.mean(axis=1)) / GARCH_SETTINGS["scale"]


def specs(horizon: int) -> dict[str, HistorySpec]:
    return {BASELINE: HistorySpec(_no_fit, persistence_predict),
            "ewma": HistorySpec(_no_fit, ewma_predict),
            "garch_t": HistorySpec(garch_fit, partial(garch_predict, horizon=horizon))}


def declared() -> dict:
    return {"baseline": {BASELINE: "vol_30d at t (served today, D27)"},
            "ewma": {"lambda": config.EWMA_LAMBDA, "forecast": "EWMA vol at t for every day of the horizon"},
            "garch_t": {**GARCH_SETTINGS, "fit": "fold train returns only (D48)",
                        "recursion": "through every daily return up to t (D48)",
                        "forecast": "sqrt(mean of the h forecast variances)"}}
