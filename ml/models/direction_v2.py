"""Phase 9 direction candidates (D42, D49), h = 30 only: LightGBM multiclass classifier (2 configs) next to the
existing logistic regression (4c, ml/models/direction.py). Same harness specs, FitCache, classes, clipping and
prior as 4c; LightGBM's features are standardised like logreg's (a monotone change, so trees split the same).
lightgbm is imported only when a LightGBM config is built.
"""

from ml.models import direction
from ml.models.price_v2 import LIGHTGBM_CONFIGS, LIGHTGBM_PARAMS

LGBM_LEAVES = {"lgbm_clf_l7": "lgbm_l7", "lgbm_clf_l15": "lgbm_l15"}    # the D42 grid
MODEL_CONFIGS = {"logreg": list(direction.CONFIGS), "lightgbm": list(LGBM_LEAVES)}


def _lgbm(name: str):
    import lightgbm
    return lightgbm.LGBMClassifier(objective="multiclass", **LIGHTGBM_PARAMS, **LIGHTGBM_CONFIGS[LGBM_LEAVES[name]])


def factories() -> dict:
    """Config name -> model factory for direction.FitCache (logreg from 4c, then LightGBM)."""
    out = dict(direction.CONFIGS)
    out.update({name: (lambda name=name: _lgbm(name)) for name in LGBM_LEAVES})
    return out


def declared() -> dict:
    return {"logreg": {k: repr(v()) for k, v in direction.CONFIGS.items()},
            "lightgbm": {k: {**LIGHTGBM_PARAMS, **LIGHTGBM_CONFIGS[v], "objective": "multiclass"}
                         for k, v in LGBM_LEAVES.items()},
            "baseline": "prior: train-fold class frequencies", "eps": direction.EPS,
            "target": "direction class (DOWN/FLAT/UP), each fold's own D19 thresholds", "horizon": 30}
