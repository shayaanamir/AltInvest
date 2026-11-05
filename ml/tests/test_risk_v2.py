"""Phase 9 step 9.4 risk: QLIKE, the persistence / EWMA specs, and GARCH (fit on train, recursion to t, D48).

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
The GARCH tests skip when arch is not installed (the serving environment).
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.run_walkforward_risk_v2 import qlike
from ml.evaluation.walkforward import make_folds
from ml.evaluation.walkforward_history import run_history_folds
from ml.features.features import ewma_vol
from ml.models import risk_v2

N, B2, MIN_TRAIN = 300, 255, 100


def _raw(n_feature_rows=N):
    """Hand-made daily bars (not market data): a wave on a slow trend plus a wobble whose size drifts."""
    i = np.arange(n_feature_rows + config.WARMUP_ROWS, dtype=float)
    close = 100 + 15 * np.sin(i / 9) + 0.2 * i + (3 + 2 * np.sin(i / 40)) * np.cos(i / 2.3)
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _data(h, raw=None):
    raw = _raw() if raw is None else raw
    return dev_data(raw.iloc[:config.WARMUP_ROWS + B2].copy(), h)


def test_qlike_by_hand():
    assert qlike([1.0], [1.0])[0] == 0.0                          # perfect forecast
    r = 2.0 ** 2 / 1.0 ** 2
    assert qlike([1.0], [2.0])[0] == pytest.approx(r - np.log(r) - 1)
    assert (qlike([0.5, 2.0], [1.0, 1.0]) > 0).all()             # any miss costs


@pytest.mark.parametrize("h", [7, 30])
def test_persistence_and_ewma_specs(h):
    data = _data(h)
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    specs = {k: v for k, v in risk_v2.specs(h).items() if k != "garch_t"}
    pooled, _ = run_history_folds(data, folds, specs, B2, h, 1)
    rows = pooled["row"].to_numpy()
    np.testing.assert_array_equal(pooled["pred:persistence_vol30"], data["vol_30d"].to_numpy()[rows])
    np.testing.assert_allclose(pooled["pred:ewma"], ewma_vol(data["close"]).to_numpy()[rows])


def test_garch_forecast_matches_the_recursion_by_hand():
    m = risk_v2.FittedGarch(mu=0.0, omega=0.1, alpha=0.1, beta=0.8, nu=8.0, sigma2_start=1.0)
    r = np.array([0.01, -0.02, 0.005])                            # scaled by 100 inside: 1, -2, 0.5
    s2, nxt = 1.0, []
    for e in (1.0, -2.0, 0.5):
        s2 = 0.1 + 0.1 * e * e + 0.8 * s2
        nxt.append(s2)
    np.testing.assert_allclose(risk_v2.garch_variances(m, r), nxt)
    hist = pd.DataFrame({"ret_1d": r})
    path, v = [], nxt[-1]
    for _ in range(3):                                           # days s+1, s+2, s+3
        path.append(v)
        v = 0.1 + 0.9 * v
    got = risk_v2.garch_predict(m, hist, range(2, 3), horizon=3)
    assert got[0] == pytest.approx(np.sqrt(np.mean(path)) / 100)


@pytest.mark.parametrize("h", [7, 30])
def test_risk_forecast_at_t_ignores_closes_after_t(h):
    pytest.importorskip("arch")
    raw = _raw()
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    base, _ = run_history_folds(_data(h, raw), folds, risk_v2.specs(h), B2, h, 1)
    t = folds[1].origin
    changed = raw.copy()
    changed.loc[config.WARMUP_ROWS + t + 1:, ["open", "high", "low", "close", "volume"]] *= 2.3
    changed.loc[config.WARMUP_ROWS + t + 3:, "close"] *= 1.1                 # also change later returns
    after, _ = run_history_folds(_data(h, changed), folds, risk_v2.specs(h), B2, h, 1)
    cols = [c for c in base.columns if c.startswith("pred:")]
    upto = base["row"] <= t
    np.testing.assert_array_equal(base.loc[upto, cols].to_numpy(), after.loc[upto, cols].to_numpy())
    assert not np.array_equal(base.loc[~upto, "pred:garch_t"].to_numpy(), after.loc[~upto, "pred:garch_t"].to_numpy())


def test_garch_parameters_come_from_train_rows_only():
    pytest.importorskip("arch")
    data = _data(7)
    train, inputs = data.iloc[:150], data.iloc[:160]
    a = risk_v2.garch_fit(train, inputs)
    b = risk_v2.garch_fit(train, data)                             # more inputs, same train rows
    assert a == b
    assert 0 <= a.alpha and 0 <= a.beta and a.alpha + a.beta < 1.0 + 1e-9
