"""Phase 9 step 9.5 direction: LightGBM classifier configs next to the 4c logistic regression.

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
The LightGBM test skips when lightgbm is not installed (the serving environment).
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.run_walkforward_direction import prob_columns
from ml.evaluation.walkforward import make_folds, run_folds
from ml.models import direction, direction_v2

N, B2, MIN_TRAIN = 300, 255, 100


def _data():
    """Hand-made daily bars (not market data): a wave on a slow trend plus a wobble."""
    i = np.arange(N + config.WARMUP_ROWS, dtype=float)
    close = 100 + 15 * np.sin(i / 9) + 0.2 * i + 3 * np.cos(i / 2.3)
    raw = pd.DataFrame({"asset": "test",
                        "timestamp": pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(i, unit="D"),
                        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close,
                        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i})
    return dev_data(raw.iloc[:config.WARMUP_ROWS + B2].copy())


def test_configs_keep_the_4c_logreg_and_add_two_lightgbm():
    assert direction_v2.MODEL_CONFIGS["logreg"] == list(direction.CONFIGS)
    assert len(direction_v2.MODEL_CONFIGS["lightgbm"]) == 2
    assert set(direction_v2.factories()) == set(direction.CONFIGS) | set(direction_v2.LGBM_LEAVES)


def test_lightgbm_probabilities_through_the_harness():
    pytest.importorskip("lightgbm")
    folds = make_folds(N, B2, MIN_TRAIN, 30, 30)
    cache = direction.FitCache({k: v for k, v in direction_v2.factories().items() if k.startswith("lgbm")})
    pooled, _ = run_folds(_data(), folds, direction.specs(cache), B2)
    for name in direction_v2.LGBM_LEAVES:
        p = pooled[prob_columns(name)].to_numpy()
        np.testing.assert_allclose(p.sum(axis=1), 1.0)
        assert (p >= direction.EPS / 2).all()
    assert cache.fits["lgbm_clf_l7"] == len(folds)               # one fit per fold, shared by the 3 classes
