"""Phase 9 step 9.2 price candidates: D44 approval helper, refit cadence, per-asset specs, pooled walk-forward
and the LSTM's no-look-ahead windows.

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
Tests that need a training library skip when it is not installed (the serving environment).
"""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation.approval import rank_and_confirm
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.walkforward import Fold, make_folds, run_folds
from ml.evaluation.walkforward_pooled import PooledSpec, pooled_train_sets, run_pooled
from ml.models import price_v2

N, B2, MIN_TRAIN = 300, 255, 100


def _raw(n_feature_rows=N, start="2020-01-01", phase=0.0):
    """Hand-made daily bars (not market data): a wave on a slow trend plus a wobble."""
    i = np.arange(n_feature_rows + config.WARMUP_ROWS, dtype=float)
    close = 100 + 15 * np.sin(i / 9 + phase) + 0.2 * i + 3 * np.cos(i / 2.3)
    return pd.DataFrame({
        "asset": "test",
        "timestamp": pd.to_datetime(start, utc=True) + pd.to_timedelta(i, unit="D"),
        "open": close, "high": close * 1.02, "low": close * 0.98, "close": close,
        "volume": 1000 + 200 * np.cos(i / 4) + 3 * i,
    })


def _data(h, raw=None, b2=B2):
    raw = _raw() if raw is None else raw
    return dev_data(raw.iloc[:config.WARMUP_ROWS + b2].copy(), h)


# --- D44 approval ---------------------------------------------------------------------------------------------

def _pooled(n_folds=10, step=7):
    rows = n_folds * step
    idx = pd.date_range("2021-01-01", periods=rows, freq="D", tz="UTC")
    folds = [Fold(100 + k * step, range(0, 93 + k * step), range(100 + k * step, 107 + k * step))
             for k in range(n_folds)]
    return pd.DataFrame({"origin": np.repeat([f.origin for f in folds], step)}, index=idx), folds


def test_approval_better_model_is_approved_and_equal_is_not():
    pooled, folds = _pooled()
    i = np.arange(len(pooled), dtype=float)
    base = 1.0 + 0.3 * np.sin(i)                                # hand-made losses
    res = rank_and_confirm(pooled, folds, {"a": base * 0.5, "b": base * 0.9, "lv": base}, ["a", "b"], ["lv"], 7)
    assert res["ranking_first_60pct"]["order"] == ["a", "b"] and res["ranking_first_60pct"]["n_folds"] == 6
    assert res["verdict"]["top_config"] == "a" and res["verdict"]["approved"] is True
    assert res["verdict"]["paired_diff_baseline_minus_model"]["block_size"] == 7
    same = rank_and_confirm(pooled, folds, {"a": base, "lv": base}, ["a"], ["lv"], 7)
    assert same["verdict"]["approved"] is False


def test_approval_uses_the_strongest_baseline_on_confirmation_folds():
    pooled, folds = _pooled()
    n_rank = 6 * 7
    weak = np.r_[np.full(n_rank, 0.1), np.full(len(pooled) - n_rank, 2.0)]   # good early, bad late
    strong = np.full(len(pooled), 1.0)
    res = rank_and_confirm(pooled, folds, {"m": np.full(len(pooled), 1.5), "weak": weak, "strong": strong},
                           ["m"], ["weak", "strong"], 7)
    assert res["verdict"]["baseline"] == "strong" and res["verdict"]["approved"] is False


def test_approval_refuses_nan_losses():
    pooled, folds = _pooled()
    bad = np.ones(len(pooled))
    bad[3] = np.nan
    with pytest.raises(ValueError):
        rank_and_confirm(pooled, folds, {"m": bad, "lv": np.ones(len(pooled))}, ["m"], ["lv"], 7)


# --- refit cadence and per-asset specs ------------------------------------------------------------------------

def test_refit_every_reuses_the_last_fit():
    calls = []
    wrapped = price_v2.RefitEvery(lambda train: (calls.append(len(train)), object())[1], 4)
    models = [wrapped(pd.DataFrame(index=range(k + 1))) for k in range(9)]
    assert calls == [1, 5, 9] and wrapped.n_fits == 3
    assert models[0] is models[3] and models[3] is not models[4] and models[4] is models[7]
    assert price_v2.refit_every_folds("prophet", 7) == 4 and price_v2.refit_every_folds("prophet", 30) == 1
    assert price_v2.refit_every_folds("lightgbm", 7) == 1


@pytest.mark.parametrize("h", [7, 30])
def test_ridge_reference_runs_at_both_horizons(h):
    folds = make_folds(N, B2, MIN_TRAIN, h, h)
    specs = price_v2.specs("ridge", h)
    pooled, _ = run_folds(_data(h), folds, specs, B2, horizon=h)
    for name in price_v2.RIDGE_CONFIGS:
        assert pooled[f"pred:{name}"].notna().all()
        assert specs[name].fit.n_fits == len(folds)


def test_lightgbm_runs_at_h7():
    pytest.importorskip("lightgbm")
    folds = make_folds(N, B2, MIN_TRAIN, 7, 7)
    pooled, _ = run_folds(_data(7), folds, price_v2.specs("lightgbm", 7), B2, horizon=7)
    assert pooled[["pred:lgbm_l7", "pred:lgbm_l15"]].notna().all().all()


def test_prophet_uses_train_closes_only_and_refits_every_4th_fold():
    pytest.importorskip("prophet")
    folds = make_folds(N, B2, MIN_TRAIN, 7, 7)[:5]
    raw = _raw()
    specs = price_v2.specs("prophet", 7)
    p1, _ = run_folds(_data(7, raw), folds, {"p": specs["prophet_cps005"]}, B2, horizon=7)
    assert specs["prophet_cps005"].fit.n_fits == 2                     # folds 0 and 4
    altered = raw.copy()                                               # change prices from fold 4's origin on
    altered.loc[config.WARMUP_ROWS + folds[4].origin:, ["open", "high", "low", "close"]] *= 2.0
    p2, _ = run_folds(_data(7, altered), folds, {"p": price_v2.specs("prophet", 7)["prophet_cps005"]}, B2, 7)
    # forecast log prices are unchanged; only log close[t] in "forecast - log close[t]" moves, by exactly ln 2
    late = p1["origin"] == folds[4].origin
    np.testing.assert_allclose(p1.loc[late, "pred:p"] - p2.loc[late, "pred:p"], np.log(2.0), atol=1e-9)
    np.testing.assert_array_equal(p1.loc[~late, "pred:p"], p2.loc[~late, "pred:p"])


# --- pooled walk-forward --------------------------------------------------------------------------------------

def _datas(h, b2_b=B2 - 40, start_b="2020-03-01"):
    """Asset a and an asset b that starts later and has an earlier b2 (like SOL vs BTC/ETH, reversed)."""
    return {"a": (_data(h), B2), "b": (_data(h, _raw(start=start_b, phase=1.0), b2_b), b2_b)}


def test_pooled_train_sets_respect_the_cutoff_and_each_b2():
    h = 7
    datas = _datas(h)
    cutoff = datas["a"][0].index[240]
    sets = pooled_train_sets(datas, cutoff, h)
    for asset, rows in sets.items():
        assert (rows.index < cutoff - pd.Timedelta(days=h)).all()
        assert rows[f"fwd_return_{h}d"].notna().all()
        assert len(rows) <= datas[asset][1] - h                       # labels end before that asset's b2


def test_pooled_fit_ignores_prices_from_the_cutoff_on(monkeypatch):
    monkeypatch.setattr(config, "MIN_TRAIN_ROWS", MIN_TRAIN)
    h = 7
    seen = []

    def fit(sets):
        seen.append({a: s.copy() for a, s in sets.items()})
        return None

    spec = {"spy": PooledSpec(fit, lambda model, asset, history, rows: np.zeros(len(rows)))}
    datas = _datas(h)
    out, info = run_pooled(datas, spec, h, every=4)
    k = len(seen) // 2
    cutoff_rows = {a: s.index.max() for a, s in seen[k].items()}
    altered = {}
    for asset, (data, b2) in datas.items():
        raw = _raw(start="2020-03-01", phase=1.0) if asset == "b" else _raw()
        first = int((raw["timestamp"] > cutoff_rows["a"] + pd.Timedelta(days=h)).idxmax())
        raw.loc[first:, ["open", "high", "low", "close", "volume"]] *= 3.1
        altered[asset] = (_data(h, raw, b2), b2)
    seen_before = seen[k]
    seen.clear()
    run_pooled(altered, spec, h, every=4)
    for asset in seen_before:
        pd.testing.assert_frame_equal(seen_before[asset], seen[k][asset], check_exact=True)
    assert info["n_fits"]["spy"] < sum(len(o["origin"].unique()) for o in out.values())   # cadence + shared dates


def test_lstm_prediction_at_t_ignores_rows_after_t(monkeypatch):
    pytest.importorskip("torch")
    from ml.models import lstm
    monkeypatch.setitem(lstm.SETTINGS, "max_epochs", 2)
    h = 7
    data = _data(h)
    model = lstm.fit({"a": data.iloc[:150]}, "lstm_h16", h)
    rows = range(200, 207)
    base = lstm.predict(model, "a", data, rows)
    changed = data.copy()
    changed.iloc[204:, :10] = changed.iloc[204:, :10] * 5.0          # features from row 204 on
    after = lstm.predict(model, "a", changed, rows)
    np.testing.assert_array_equal(base[:4], after[:4])               # rows 200-203 use windows ending <= 203
    assert not np.array_equal(base[4:], after[4:])
    again = lstm.fit({"a": data.iloc[:150]}, "lstm_h16", h)          # fixed seeds: same fit, same output
    np.testing.assert_array_equal(base, lstm.predict(again, "a", data, rows))
    # an asset with fewer rows than the lookback contributes nothing (and does not break the fit)
    short = lstm.fit({"a": data.iloc[:150], "b": data.iloc[:lstm.SETTINGS["lookback"] - 1]}, "lstm_h16", h)
    assert set(short.scalers) == {"a"}
    np.testing.assert_array_equal(base, lstm.predict(short, "a", data, rows))
