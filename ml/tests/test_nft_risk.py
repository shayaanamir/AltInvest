"""Phase 10 step 10.3: floor-volatility rows, candidates and the pooled approval (D59 as amended).
Hand-made fixtures, no network, no snapshot files."""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import metrics as m
from ml.evaluation import nft_approval as ap
from ml.evaluation import run_nft_risk
from ml.evaluation.walkforward import SealedTestError, make_folds
from ml.evaluation.walkforward_history import run_history_folds
from ml.features.features import ewma_vol
from ml.models import nft_risk, risk_v2
from ml.nft import risk_data, snapshot

H = config.HORIZON_DAYS


def _floor(n=420, seed=0, slug="c"):
    """A made-up floor series: a random walk in logs with a calm half and a wild half."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 1, n) * np.where(np.arange(n) < n // 2, 0.02, 0.06)
    dates = pd.date_range("2024-09-17", periods=n, freq="D").strftime("%Y-%m-%d")
    v = 5.0 * np.exp(np.cumsum(r))
    return pd.DataFrame({"slug": slug, "date": dates, "floor_eth_model": v, "floor_eth_asof": v})


def test_features_match_the_hand_formulas_and_drop_the_warm_up():
    f = _floor()
    close = risk_data.floor_series(f)
    feats = risk_data.features(close)
    r = np.log(f["floor_eth_model"]).diff().to_numpy()
    assert len(feats) == len(f) - config.WARMUP_ROWS and feats.index[0] == close.index[config.WARMUP_ROWS]
    assert feats["ret_1d"].iloc[0] == pytest.approx(r[30])
    assert feats["vol_30d"].iloc[5] == pytest.approx(np.std(r[6:36], ddof=1))
    assert list(feats.columns) == risk_data.FEATURES + ["close"]


def test_floor_series_refuses_gaps_duplicates_and_missing_floors():
    f = _floor()
    with pytest.raises(ValueError, match="consecutive calendar days"):
        risk_data.floor_series(f.drop(index=10))
    with pytest.raises(ValueError, match="consecutive calendar days"):
        risk_data.floor_series(pd.concat([f, f.iloc[[5]]]))
    bad = f.copy()
    bad.loc[7, "floor_eth_model"] = np.nan
    with pytest.raises(ValueError, match="positive number"):
        risk_data.floor_series(bad)


def test_dev_frame_never_contains_or_depends_on_a_sealed_test_row():
    f = _floor()
    data, b2, n = risk_data.dev_frame(f)
    assert n == 390 and b2 == 331 and len(data) == b2             # floor(0.85 x 390) = 331
    test_start = risk_data.test_start_date(f)
    assert test_start == f["date"].iloc[config.WARMUP_ROWS + b2]
    assert data.index[-1].strftime("%Y-%m-%d") < test_start
    assert data["fwd_vol_30d"].iloc[-H:].isna().all()             # labels that would need test floors do not exist
    changed = f.copy()
    changed.loc[changed["date"] >= test_start, "floor_eth_model"] *= 7.0
    pd.testing.assert_frame_equal(data, risk_data.dev_frame(changed)[0])
    test, b2_t, _ = risk_data.test_frame(f)
    assert b2_t == b2 and test.index[0].strftime("%Y-%m-%d") == test_start and len(test) == n - b2 - H


def test_candidates_are_declared_once_and_reuse_the_phase_9_functions():
    assert nft_risk.MODEL_CONFIGS == {"ewma": ["ewma"], "garch": ["garch_normal"]}
    specs = nft_risk.specs()
    assert specs["ewma"].predict is risk_v2.ewma_predict                       # the served ewma_vol function
    assert specs[nft_risk.BASELINE].predict is risk_v2.persistence_predict
    assert nft_risk.declared()["ewma"]["lambda"] == config.EWMA_LAMBDA == 0.94
    assert nft_risk.GARCH_SETTINGS["dist"] == "normal" and config.NFT_MIN_TRAIN_ROWS == 180
    hist = risk_data.features(risk_data.floor_series(_floor()))
    np.testing.assert_allclose(risk_v2.ewma_predict(None, hist, range(100, 110)),
                               ewma_vol(hist["close"]).to_numpy()[100:110])


def test_no_prediction_uses_a_floor_after_its_own_row():
    pytest.importorskip("arch")
    data, b2, _ = risk_data.dev_frame(_floor())
    hist = data[risk_data.FEATURES + ["close"]]
    rows = range(250, 260)
    later = _floor().copy()
    later.loc[later.index > config.WARMUP_ROWS + 259, "floor_eth_model"] *= 3.0     # only floors after row 259
    hist2 = risk_data.dev_frame(later)[0][risk_data.FEATURES + ["close"]]
    assert not hist2.iloc[260:].equals(hist.iloc[260:])
    for name, spec in nft_risk.specs().items():
        fitted = spec.fit(data.iloc[:220], hist.iloc[:251])
        a = spec.predict(fitted, hist.iloc[:rows.stop], rows)
        b = spec.predict(fitted, hist2.iloc[:rows.stop], rows)
        np.testing.assert_allclose(a, b, err_msg=name)
        assert np.all(np.asarray(a) > 0)


def test_harness_refuses_test_rows_and_takes_the_nft_feature_columns():
    data, b2, _ = risk_data.dev_frame(_floor())
    folds = make_folds(len(data), b2, config.NFT_MIN_TRAIN_ROWS, H, H)
    assert [f.origin for f in folds] == [210, 240, 270, 300] and folds[-1].predict.stop == b2 - H
    specs = {k: v for k, v in nft_risk.specs().items() if k != "garch_normal"}
    pooled, _ = run_history_folds(data, folds, specs, b2, H, every=1, feature_columns=risk_data.FEATURES)
    assert pooled["fwd_vol_30d"].notna().all() and len(pooled) == b2 - H - 210
    with pytest.raises(SealedTestError):
        run_history_folds(risk_data.with_labels(risk_data.floor_series(_floor())), folds, specs, b2, H, every=1,
                          feature_columns=risk_data.FEATURES)


def test_date_block_ci_equals_the_row_bootstrap_for_one_collection_and_moves_dates_together():
    rng = np.random.default_rng(1)
    a, b = rng.normal(1.0, 1, 200), rng.normal(0.8, 1, 200)
    dates = pd.date_range("2025-01-01", periods=200, freq="D").strftime("%Y-%m-%d").to_numpy()
    ours, ref = ap.date_block_ci(dates, a, b, block=30), m.paired_bootstrap_ci(a, b, np.mean, block_size=30)
    assert ours["low"] == pytest.approx(ref["low"]) and ours["high"] == pytest.approx(ref["high"])
    assert ours["estimate"] == pytest.approx(ref["estimate"]) and ours["n_dates"] == 200
    two = ap.date_block_ci(np.r_[dates, dates], np.r_[a, a], np.r_[b, b], block=30)   # a copy adds no information
    assert two["low"] == pytest.approx(ref["low"]) and two["high"] == pytest.approx(ref["high"])
    assert ap.date_block_ci(dates[:20], a[:20], b[:20], block=30) is None


def _rows(gain, n=120, seed=0):
    rng = np.random.default_rng(seed)
    base = rng.normal(1.0, 0.05, n)
    dates = pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d").to_numpy()
    return {"dates": dates, "in_rank": np.arange(n) < 72, "losses": {"base": base, "m": base - gain}}


def test_pooled_approval_needs_the_ci_and_no_collection_worse():
    good = ap.pooled_rank_and_confirm({"a": _rows(0.2), "b": _rows(0.1, seed=1)}, ["m"], "base", 30)
    v = good["verdict"]
    assert v["approved"] and v["paired_diff_baseline_minus_model"]["low"] > 0
    assert v["per_collection_baseline_minus_model"] == pytest.approx({"a": 0.2, "b": 0.1})
    assert good["confirmation_last_40pct"]["n_pooled"] == 96 and good["confirmation_last_40pct"]["n_dates"] == 48
    mixed = ap.pooled_rank_and_confirm({"a": _rows(0.5), "b": _rows(-0.01, seed=1)}, ["m"], "base", 30)["verdict"]
    assert mixed["pooled_ci_excludes_0"] and not mixed["every_collection_not_worse"] and not mixed["approved"]
    none = ap.pooled_rank_and_confirm({"a": _rows(0.0), "b": _rows(0.0, seed=1)}, ["m"], "base", 30)["verdict"]
    assert not none["approved"]


def test_report_serves_persistence_when_nothing_is_approved_and_counts_trials():
    pytest.importorskip("arch")
    floor = pd.concat([_floor(seed=s, slug=f"c{s}") for s in (0, 1)])
    report = run_nft_risk.build(floor)
    assert report["trial_count"]["total"] == 2 and set(report["pooled"]) == {"ewma", "garch"}
    assert report["served_volatility"] == (report["winner"] or nft_risk.BASELINE)
    pooled_rows = [r for r in report["verdict_table"] if r["scope"].startswith("pooled")]
    assert len(pooled_rows) == 2 and len(report["verdict_table"]) == 2 + 2 * 2
    meta = report["collections"]["c0"]["metadata"]
    assert meta["max_label_row_reached"] <= meta["b2_test_start_row"] and meta["n_folds"] == 4


def test_runner_refuses_a_snapshot_that_does_not_match_its_manifest(monkeypatch):
    monkeypatch.setattr(snapshot, "mismatches", lambda date=None, tables=(): ["floor.parquet"])
    with pytest.raises(SystemExit, match=r"does not match its manifest \(D62\)"):
        run_nft_risk.main()


def test_top_only_protocol_ranks_all_candidates_together_and_confirms_only_the_top():
    rows = {s: _rows(0.0, seed=k) for k, s in enumerate(("a", "b"))}
    for r in rows.values():                      # model "g" ranks best (lower loss) but is worse on confirmation
        base = r["losses"]["base"]
        r["losses"]["g"] = np.where(r["in_rank"], base - 0.3, base + 0.1)
        r["losses"]["e"] = base - 0.1
    out = ap.pooled_top_only(rows, {"ewma": ["e"], "garch": ["g"]}, "base", 30)
    assert out["ranking_order_all_candidates"] == ["g", "e"] and out["top_model"] == "garch"
    assert not out["approved"] and out["winner"] is None          # e would pass alone, but it is never confirmed
    assert ap.pooled_rank_and_confirm(rows, ["e"], "base", 30)["verdict"]["approved"]


def test_top_only_on_the_10_3_report_approves_nothing():
    import json
    from ml.data.validate import ML_ROOT
    r = json.loads((ML_ROOT / "reports" / "nft" / "walkforward_risk.json").read_text(encoding="utf-8"))
    rank = {m: p["ranking_first_60pct"]["mean_loss"][p["verdict"]["top_config"]] for m, p in r["pooled"].items()}
    top = min(rank, key=rank.get)
    assert top == "garch" and rank["garch"] < rank["ewma"]
    assert r["pooled"][top]["verdict"]["approved"] is False       # so under D25/D44 as written: nothing approved
