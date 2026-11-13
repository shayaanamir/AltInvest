"""Fair-value baselines and candidates (Phase 10 step 10.6a, D76): THE one file that lists them, fixed before any run.

Target y = log(price_eth / floor_point_eth) (D70 floor point strictly before the sale). Fair value = floor x exp(y_hat).
BASELINES (fitted inside each training fold only; not trials):
  B0_floor          y_hat = 0. Range: per collection, the 0.10 / 0.90 quantiles of the training fold's y.
  B1_rarity_decile  y_hat = the training fold's median y of the sale's (collection, rarity decile); 0 when that
                    cell has fewer than 5 training rows. Rarity decile = ceil(10 x rarity_rank / tokens ranked) per
                    collection (rarity_score: traits only, ID-like categories excluded, see fv_features). Range:
                    y_hat + the per-collection 0.10 / 0.90 quantiles of the training residuals y - y_hat.
  B2_decile_90d     (D76 amended; D60 baseline (b) restored) y_hat = decile_prem_med_90d: the median premium of
                    the feature-history sales of the same (collection, rarity decile) in [t - 90 days, t), strictly
                    before the sale; 0 when fewer than 5 such sales. Fits nothing. Range: y_hat + the per-collection
                    0.10 / 0.90 quantiles of the training rows' residuals y - y_hat.
CANDIDATES (6 LightGBM configs = the trial count; no additions after the first run; D25 max 4 per model type):
  model type 'pooled' (4): one model over all 7 collections with every feature (collection as a categorical).
  model type 'per_collection' (2): one model per collection with the STATIC features except collection, that
  collection's trait columns and the DYNAMIC features.
  Shared settings: 400 rounds, learning_rate 0.05, min_data_in_leaf 100, feature_fraction 0.8, bagging 0.8 every
  round, lambda_l2 1.0, seed 0, deterministic, 4 threads, no early stopping (it would need held-out rows).
RANGE of a candidate (fixed method, selects nothing, adds no trial): two LightGBM quantile models (alpha 0.10 and
0.90) with the candidate's own structure and settings except the objective, fitted on the same training fold.
The two predictions are sorted per row (ordered_range), so the low end never exceeds the high end; the number of
crossed rows is counted and reported.
"""

import numpy as np
import pandas as pd

from ml.nft import fv_features as fv

QUANTILES = (0.10, 0.90)
B1_MIN_ROWS = 5
N_ROUNDS = 400
COMMON = {"learning_rate": 0.05, "min_data_in_leaf": 100, "feature_fraction": 0.8, "bagging_fraction": 0.8,
          "bagging_freq": 1, "lambda_l2": 1.0, "seed": 0, "deterministic": True, "force_row_wise": True,
          "num_threads": 4, "verbose": -1}
CANDIDATES = {
    "pooled": {
        "fv_pooled_l2_nl15": {"objective": "regression", "num_leaves": 15},
        "fv_pooled_l2_nl63": {"objective": "regression", "num_leaves": 63},
        "fv_pooled_l1_nl15": {"objective": "regression_l1", "num_leaves": 15},
        "fv_pooled_l1_nl63": {"objective": "regression_l1", "num_leaves": 63},
    },
    "per_collection": {
        "fv_percoll_l2_nl15": {"objective": "regression", "num_leaves": 15},
        "fv_percoll_l1_nl15": {"objective": "regression_l1", "num_leaves": 15},
    },
}
NAMES = [n for cs in CANDIDATES.values() for n in cs]
TRIAL_COUNT = len(NAMES)
assert TRIAL_COUNT <= 6 and all(len(cs) <= 4 for cs in CANDIDATES.values())


def model_type(name: str) -> str:
    return next(m for m, cs in CANDIDATES.items() if name in cs)


def params(name: str, quantile: float | None = None) -> dict:
    p = {**COMMON, **CANDIDATES[model_type(name)][name]}
    if quantile is not None:
        p.update(objective="quantile", alpha=quantile)
    return p


def range_key(name: str) -> tuple:
    """Candidates that differ only in the point objective share their quantile models."""
    return model_type(name), CANDIDATES[model_type(name)][name]["num_leaves"]


def _per_slug_quantiles(slug: pd.Series, resid: np.ndarray) -> dict:
    return {s: np.quantile(resid[(slug == s).to_numpy()], QUANTILES) for s in slug.unique()}


def baseline_b0(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q = _per_slug_quantiles(train["slug"], train["y"].to_numpy())
    lo = test["slug"].map(lambda s: q[s][0]).to_numpy(dtype=float)
    hi = test["slug"].map(lambda s: q[s][1]).to_numpy(dtype=float)
    return np.zeros(len(test)), lo, hi


def b1_medians(train: pd.DataFrame) -> dict:
    g = train.groupby(["slug", "rarity_decile"])["y"]
    med, n = g.median(), g.size()
    return {k: (float(med[k]) if n[k] >= B1_MIN_ROWS else 0.0) for k in med.index}


def baseline_b1(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    med = b1_medians(train)
    pred = lambda df: np.array([med.get(k, 0.0) for k in zip(df["slug"], df["rarity_decile"])])  # noqa: E731
    q = _per_slug_quantiles(train["slug"], train["y"].to_numpy() - pred(train))
    y_hat = pred(test)
    lo = y_hat + test["slug"].map(lambda s: q[s][0]).to_numpy(dtype=float)
    hi = y_hat + test["slug"].map(lambda s: q[s][1]).to_numpy(dtype=float)
    return y_hat, lo, hi


def b2_predict(df: pd.DataFrame) -> np.ndarray:
    return df["decile_prem_med_90d"].fillna(0.0).to_numpy(dtype=float)


def baseline_b2(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q = _per_slug_quantiles(train["slug"], train["y"].to_numpy() - b2_predict(train))
    y_hat = b2_predict(test)
    lo = y_hat + test["slug"].map(lambda s: q[s][0]).to_numpy(dtype=float)
    hi = y_hat + test["slug"].map(lambda s: q[s][1]).to_numpy(dtype=float)
    return y_hat, lo, hi


BASELINE_FNS = {"B0_floor": baseline_b0, "B1_rarity_decile": baseline_b1, "B2_decile_90d": baseline_b2}


def ordered_range(lo, hi) -> tuple[np.ndarray, np.ndarray, int]:
    """(low, high, n_crossed): the two quantile predictions sorted per row, so low <= high always."""
    lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
    return np.minimum(lo, hi), np.maximum(lo, hi), int(np.sum(lo > hi))


def columns_for(name: str, slug: str | None, trait_cols: list[str]) -> list[str]:
    if model_type(name) == "pooled":
        return fv.feature_columns(trait_cols)
    own = [c for c in trait_cols if c.startswith(fv.trait_column(slug, ""))]
    return [c for c in fv.STATIC if c != "collection"] + own + fv.DYNAMIC


def _fit(p: dict, X: pd.DataFrame, y: np.ndarray):
    import lightgbm as lgb
    cats = [c for c in X.columns if c == "collection" or c.startswith("trait__")]
    return lgb.train(p, lgb.Dataset(X, y, categorical_feature=cats, free_raw_data=True), num_boost_round=N_ROUNDS)


def fit_predict(name: str, train: pd.DataFrame, test: pd.DataFrame, trait_cols: list[str], id_like: dict,
                quantile: float | None = None, models: dict | None = None) -> np.ndarray:
    """Point prediction (or one quantile) of candidate `name` for `test`, fitted on `train` only. When `models`
    is a dict, the fitted boosters are stored in it by collection (None for pooled)."""
    out = np.full(len(test), np.nan)
    groups = [(None, np.ones(len(train), bool), np.ones(len(test), bool))] if model_type(name) == "pooled" else \
        [(s, (train["slug"] == s).to_numpy(), (test["slug"] == s).to_numpy()) for s in sorted(test["slug"].unique())]
    for slug, tr_mask, te_mask in groups:
        cols = columns_for(name, slug, trait_cols)
        model = _fit(params(name, quantile), fv.matrix(train[tr_mask], cols, id_like), train["y"].to_numpy()[tr_mask])
        out[te_mask] = model.predict(fv.matrix(test[te_mask], cols, id_like))
        if models is not None:
            models[slug] = model
    return out


def declared() -> dict:
    return {"target": "y = log(price_eth / floor_point_eth), floor point strictly before the sale (D70)",
            "baselines": {"B0_floor": "y_hat = 0; range = per-collection training y quantiles 0.10 / 0.90",
                          "B1_rarity_decile": f"training median y per (collection, rarity decile), 0 if < {B1_MIN_ROWS} "
                                              "rows; range = y_hat + per-collection training residual quantiles",
                          "B2_decile_90d": "median premium of same (collection, decile) sales in [t - 90d, t), 0 if "
                                           "< 5; range = y_hat + per-collection training residual quantiles"},
            "candidates": CANDIDATES, "common_settings": COMMON, "n_rounds": N_ROUNDS, "trial_count": TRIAL_COUNT,
            "range_method": "LightGBM quantile alpha 0.10 / 0.90, same structure and settings as the candidate",
            "quantiles": list(QUANTILES)}
