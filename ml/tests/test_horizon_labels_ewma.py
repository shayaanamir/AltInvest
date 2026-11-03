"""Phase 9 setup (step 9.1, D41): horizon-parameterised labels, EWMA volatility, training-library isolation.

All fixtures are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.features.features import build_features, ewma_vol
from ml.labels.labels import build_labels, fwd_return, fwd_return_30d, fwd_vol, fwd_vol_30d

N = 200
REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_LIBS = ("prophet", "cmdstanpy", "torch", "lightgbm", "arch", "onnx", "onnxruntime")


def _close(n=N):
    """Hand-made closes (not market data): a wave on a slow trend."""
    i = np.arange(n, dtype=float)
    ts = pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D")
    return pd.Series(100 + 15 * np.sin(i / 9) + 0.2 * i + 3 * np.cos(i / 2.3), index=ts, name="close")


def _bars(close):
    return pd.DataFrame({"asset": "test", "timestamp": close.index, "open": close.values,
                         "high": close.values * 1.02, "low": close.values * 0.98, "close": close.values,
                         "volume": 1000.0 + np.arange(len(close))})


# --- labels --------------------------------------------------------------------------------------------------

def test_default_horizon_is_unchanged():
    close = _close()
    default = build_labels(close)
    assert list(default.columns) == ["fwd_return_30d", "fwd_vol_30d"]
    pd.testing.assert_frame_equal(default, build_labels(close, 30), check_exact=True)
    pd.testing.assert_series_equal(fwd_return_30d(close), fwd_return(close, 30), check_exact=True)
    pd.testing.assert_series_equal(fwd_vol_30d(close), fwd_vol(close, 30), check_exact=True)
    # the 30-day label is still the plain formula
    expected = np.log(close.shift(-30) / close)
    pd.testing.assert_series_equal(fwd_return_30d(close), expected, check_exact=True)


@pytest.mark.parametrize("t", [0, 50, N - 8])
def test_7d_labels_match_hand_formula(t):
    close = _close()
    labels = build_labels(close, 7)
    assert list(labels.columns) == ["fwd_return_7d", "fwd_vol_7d"]
    c = close.to_numpy()
    assert labels["fwd_return_7d"].iloc[t] == pytest.approx(np.log(c[t + 7] / c[t]), rel=1e-12)
    r_after = np.log(c[t + 1:t + 8] / c[t:t + 7])           # the 7 daily returns t+1..t+7
    assert labels["fwd_vol_7d"].iloc[t] == pytest.approx(np.std(r_after, ddof=1), rel=1e-12)


def test_7d_labels_nan_only_in_last_7_rows():
    labels = build_labels(_close(), 7)
    assert labels.iloc[-7:].isna().all().all()
    assert labels.iloc[:-7].notna().all().all()


@pytest.mark.parametrize("h", [7, 30])
def test_labels_ignore_rows_after_t_plus_h(h):
    close = _close()
    t = 100
    changed = close.copy()
    changed.iloc[t + h + 1:] *= 3.7
    a, b = build_labels(close, h).iloc[:t + 1], build_labels(changed, h).iloc[:t + 1]
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    # not vacuous: a row whose window reaches the change does move
    assert build_labels(close, h).iloc[t + 1, 0] != build_labels(changed, h).iloc[t + 1, 0]


@pytest.mark.parametrize("bad", [0, -7, 7.0, "7", True, None])
def test_bad_horizon_raises(bad):
    with pytest.raises(ValueError):
        build_labels(_close(), bad)


# --- EWMA volatility -----------------------------------------------------------------------------------------

def test_ewma_recursion_and_seed():
    close = _close()
    ew = ewma_vol(close)
    start = config.WARMUP_ROWS
    assert ew.iloc[:start].isna().all() and ew.iloc[start:].notna().all()
    assert ew.index.equals(close.index)
    vol_30d = build_features(_bars(close))["vol_30d"]
    assert ew.iloc[start] == pytest.approx(vol_30d.loc[close.index[start]], rel=1e-12)  # seed = vol_30d
    r = np.log(close / close.shift(1)).to_numpy()
    lam = config.EWMA_LAMBDA
    s2 = ew.iloc[start] ** 2
    for t in range(start + 1, start + 6):
        s2 = lam * s2 + (1 - lam) * r[t] ** 2
        assert ew.iloc[t] ** 2 == pytest.approx(s2, rel=1e-12)


@pytest.mark.parametrize("t", [30, 31, 90, N - 1])
def test_ewma_same_on_truncated_series(t):
    close = _close()
    pd.testing.assert_series_equal(ewma_vol(close).iloc[:t + 1], ewma_vol(close.iloc[:t + 1]), check_exact=True)


@pytest.mark.parametrize("t", [30, 100])
def test_future_prices_do_not_change_past_ewma(t):
    close = _close()
    changed = close.copy()
    changed.iloc[t + 1:] *= 3.7
    pd.testing.assert_series_equal(ewma_vol(close).iloc[:t + 1], ewma_vol(changed).iloc[:t + 1], check_exact=True)
    # not vacuous: the jump at t+1 is a large return, so EWMA moves from row t+1 on
    assert ewma_vol(changed).iloc[t + 1] != ewma_vol(close).iloc[t + 1]


def test_ewma_short_series_and_bad_lambda():
    assert ewma_vol(_close(config.WARMUP_ROWS)).isna().all()
    for lam in (0.0, 1.0, 1.5):
        with pytest.raises(ValueError):
            ewma_vol(_close(), lam)


# --- training libraries stay out of the serving path (D45) ---------------------------------------------------

def test_serving_imports_work_without_training_libraries():
    """Blocks the training libraries in a fresh interpreter, then imports config and the serving path."""
    code = (
        "import sys\n"
        f"for m in {TRAINING_LIBS!r}: sys.modules[m] = None\n"
        "import ml.config, ml.labels.labels, ml.features.features, ml.serving.responses, ml.api.service\n"
        "print('ok')\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().endswith("ok")
