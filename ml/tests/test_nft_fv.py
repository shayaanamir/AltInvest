"""Phase 10 step 10.6a (D76): fair-value features, leakage rules, forbidden columns, folds and the selection rule.
Hand-made frames, no network, no model fitted (except the real-data checks, which only compute features)."""

import json

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import nft_fv_protocol as proto
from ml.evaluation.nft_approval import date_block_ci
from ml.models import nft_fair_value as fvm
from ml.nft import fv_features as fv
from ml.nft import fv_leakage as L
from ml.nft import snapshot
from ml.nft import traits as tr

SLUG = "azuki"
T0 = int(pd.Timestamp("2025-03-01", tz="UTC").timestamp())
DAY = 86400


def _items(n=12):
    traits = pd.DataFrame([{"slug": SLUG, "token_id": str(i), "trait_type": "Background",
                            "value": "Red" if i < 4 else "Blue", "id_like": False} for i in range(n)]
                          + [{"slug": SLUG, "token_id": str(i), "trait_type": "Serial", "value": f"s{i}",
                              "id_like": True} for i in range(n)])
    tokens = pd.DataFrame({"slug": SLUG, "token_id": [str(i) for i in range(n)]})
    tokens = tokens.merge(tr.rarity_all(tokens, traits[~traits["id_like"]], known_only=True), on=["slug", "token_id"])
    return tokens, traits


def _sale(token, t_days, price=1.0, flag="", floor=1.0):
    ts = T0 + int(t_days * DAY)
    return {"slug": SLUG, "token_id": str(token), "timestamp": ts,
            "date": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d"), "tx": f"x{token}-{ts}",
            "price_eth": price, "floor_point_eth": floor, "wash_flag": flag, "clean": flag == ""}


POINTS = pd.DataFrame({"slug": SLUG, "time": [float(T0 - 40 * DAY + j * DAY) for j in range(80)],
                       "token_unit": [1.0 + 0.01 * j for j in range(80)]})


def _build(rows):
    tokens, traits = _items()
    h = fv.history(pd.DataFrame(rows))
    static, _ = fv.static_features(tokens, traits)
    return h, fv.build(h, POINTS, static, traits).set_index("hid")


def test_trailing_windows_are_strictly_before_the_sale_and_exclude_its_own_timestamp():
    rows = [_sale(i % 12, 0.1 * i, price=2.0) for i in range(6)] + [_sale(7, 1.0, 50.0), _sale(8, 1.0, 50.0)]
    h, f = _build(rows)
    at = h.index[h["timestamp"] == T0 + DAY]
    # the two sales at the same timestamp see only the 6 earlier ones, never each other
    assert f.loc[at, "coll_sales_1d"].tolist() == [6.0, 6.0]
    assert f.loc[at, "coll_prem_med_7d"].tolist() == pytest.approx([np.log(2.0)] * 2)
    assert np.isnan(f.loc[0, "coll_prem_med_7d"]) and f.loc[0, "coll_sales_7d"] == 0     # nothing before it
    assert np.isnan(f.loc[4, "coll_prem_med_7d"]) and f.loc[5, "coll_prem_med_7d"] == pytest.approx(np.log(2.0))


def test_previous_sale_is_strictly_before_and_later_prices_never_change_a_row():
    rows = [_sale(1, 0, 2.0), _sale(1, 3, 4.0), _sale(1, 9, 8.0)]
    h, f = _build(rows)
    assert np.isnan(f.loc[0, "prev_prem"]) and f.loc[0, "prev_n"] == 0
    assert f.loc[1, "prev_prem"] == pytest.approx(np.log(2.0)) and f.loc[1, "prev_days"] == pytest.approx(3.0)
    assert f.loc[2, "prev_n"] == 2
    _, f2 = _build(rows[:2] + [_sale(1, 9, 800.0), _sale(2, 10, 9.0)])
    pd.testing.assert_frame_equal(f.loc[[0, 1]], f2.loc[[0, 1]])


def test_w1_rows_leave_the_history_but_w2_rows_stay_as_they_looked_at_the_time():
    h = fv.history(pd.DataFrame([_sale(1, 0, flag="W1"), _sale(2, 1, flag="W2"), _sale(3, 2)]))
    assert h["token_id"].tolist() == ["2", "3"] and h["clean"].tolist() == [False, True]


def test_floor_features_use_points_strictly_before_the_sale():
    point_time = int(POINTS["time"].iloc[45])                               # a sale exactly at a point's time
    rows = [{**_sale(1, 0), "timestamp": point_time}]
    _, f = _build(rows)
    assert f.loc[0, "floor_age_hours"] == pytest.approx(24.0)              # that point is not used
    assert f.loc[0, "floor_ret_1d"] == pytest.approx(np.log(POINTS["token_unit"].iloc[44] / POINTS["token_unit"].iloc[43]))


def test_trait_premia_skip_id_like_categories_and_need_5_rows():
    rows = [_sale(i, 0.1 * i, price=3.0) for i in range(4)] * 2               # Red tokens 0-3, 8 rows
    rows = [{**r, "timestamp": r["timestamp"] + k, "tx": f"{r['tx']}-{k}"} for k, r in enumerate(rows)]
    _, f = _build(rows + [_sale(0, 2, 1.0)])
    last = f.index[-1]
    assert f.loc[last, "trait_prem_n"] == 1 and f.loc[last, "trait_prem_max"] == pytest.approx(np.log(3.0))
    assert f.loc[0, "trait_prem_n"] == 0 and np.isnan(f.loc[0, "trait_prem_max"])


def test_model_matrix_refuses_forbidden_and_id_like_columns():
    tokens, traits = _items()
    static, tcols = fv.static_features(tokens, traits)
    assert fv.trait_column(SLUG, "Serial") not in tcols                       # ID-like: never a column
    frame = pd.DataFrame(0.0, index=[0], columns=fv.feature_columns(tcols) + list(fv.FORBIDDEN)
                         + [fv.trait_column(SLUG, "Serial")])
    id_like = {SLUG: ["Serial"]}
    assert list(fv.matrix(frame, fv.feature_columns(tcols), id_like).columns) == fv.feature_columns(tcols)
    for bad in ["sale_type", "payment_currency", "marketplace", "token_id", "buyer", "seller", "tx",
                fv.trait_column(SLUG, "Serial"), "price_eth", "premium"]:
        with pytest.raises(ValueError):
            fv.matrix(frame, fv.feature_columns(tcols) + [bad], id_like)
    with pytest.raises(ValueError):
        fv.matrix(frame.assign(extra=1.0), fv.feature_columns(tcols) + ["extra"], id_like)


def test_candidates_are_declared_in_one_file_within_the_limits():
    assert fvm.TRIAL_COUNT == 6 and all(len(c) <= 4 for c in fvm.CANDIDATES.values())
    assert fvm.range_key("fv_pooled_l2_nl15") == fvm.range_key("fv_pooled_l1_nl15")
    assert fvm.params("fv_pooled_l1_nl63", 0.1)["objective"] == "quantile"


def test_baselines_fit_on_the_training_fold_only():
    train = pd.DataFrame({"slug": SLUG, "rarity_decile": [1.0] * 6 + [2.0] * 3, "y": [1, 2, 3, 4, 5, 6, 9, 9, 9.0]})
    test = pd.DataFrame({"slug": SLUG, "rarity_decile": [1.0, 2.0, 3.0]})
    y_hat, lo, hi = fvm.baseline_b1(train, test)
    assert y_hat.tolist() == [3.5, 0.0, 0.0]                                  # decile 2 has 3 < 5 rows
    y0, lo0, hi0 = fvm.baseline_b0(train, test)
    assert y0.tolist() == [0, 0, 0] and lo0[0] == pytest.approx(np.quantile(train["y"], 0.1))


def test_folds_are_monthly_expanding_with_a_7_day_embargo_inside_development():
    f = proto.folds()
    assert len(f) == 9 and [x["part"] for x in f] == ["rank"] * 5 + ["confirm"] * 4
    assert str(f[0]["test_start"].date()) == "2025-05-01" and str(f[-1]["test_end"].date()) == "2026-01-25"
    for x in f:
        assert x["test_start"] - x["train_end"] == pd.Timedelta(days=7)
    assert f[-1]["test_end"] <= pd.Timestamp(config.NFT_FV_SEALED_START, tz="UTC") - pd.Timedelta(days=7)
    frame = pd.DataFrame({"timestamp": [int(pd.Timestamp(d, tz="UTC").timestamp()) for d in
                                        ["2025-04-23", "2025-04-24", "2025-04-30", "2025-05-01", "2025-05-31"]]})
    train, test = proto.fold_rows(frame, f[0])
    assert train.tolist() == [True, False, False, False, False] and test.tolist() == [False, False, False, True, True]


def test_median_bootstrap_resamples_dates_like_the_mean_version():
    rng = np.random.default_rng(1)
    dates = np.repeat(pd.date_range("2025-10-01", periods=40).strftime("%Y-%m-%d"), 3)
    a, b = rng.random(len(dates)), rng.random(len(dates))
    mine = proto.date_block_stat_ci(dates, a, b, stat=np.mean, n_boot=200)
    ref = date_block_ci(dates, a, b, block=7, n_boot=200)
    assert mine["low"] == pytest.approx(ref["low"]) and mine["high"] == pytest.approx(ref["high"])


def _rows(model_err_rank, model_err_conf):
    dates = pd.date_range("2025-05-01", periods=60).strftime("%Y-%m-%d")
    rows = pd.DataFrame({"date": np.repeat(dates, 2), "y": 0.0})
    rows["part"] = np.where(rows["date"] < "2025-05-31", "rank", "confirm")
    for n, e in {"B0_floor": 0.5, "B1_rarity_decile": 0.4, "good": None, "bad": 0.9}.items():
        err = np.where(rows["part"] == "rank", model_err_rank, model_err_conf) if e is None else e
        rows[f"ape:{n}"] = np.abs(np.exp(err) - 1)
        rows[f"lo:{n}"], rows[f"hi:{n}"] = -1.0, 1.0
    return rows


def test_only_the_top_ranked_candidate_is_confirmed_and_d32_is_required():
    out = proto.select(_rows(0.1, 0.1), ["bad", "good"])
    assert out["ranking_first_60pct"]["order"] == ["good", "bad"] and out["verdict"]["top_candidate"] == "good"
    assert out["verdict"]["baseline"] == "B1_rarity_decile" and out["verdict"]["approved"]
    worse_on_rank = proto.select(_rows(0.45, 0.1), ["good"])                  # beats B1 only on confirmation
    assert not worse_on_rank["verdict"]["beats_better_baseline_on_ranking_folds_D32"]
    assert not worse_on_rank["verdict"]["approved"]


def test_ape_is_on_price():
    assert proto.ape(np.log(1.2), 0.0) == pytest.approx(0.2) and proto.ape(0.0, np.log(2.0)) == pytest.approx(0.5)


def _real():
    if not (snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V3) / "sales.parquet").exists():
        pytest.skip("v3 item snapshot files are local only (D64)")
    return L.prepare()


def test_real_features_match_the_cut_data_reference_and_no_forbidden_column_reaches_a_matrix():
    p = _real()
    assert p["h"]["date"].max() < "2026-01-25" and p["dev"]["floor_points"]["time"].max() < L.item_data.dev_end_timestamp()
    clean = p["features"][p["features"]["clean"]]
    res = L.check_reference(p, clean.sample(n=150, random_state=1))
    assert all(v["n_equal"] == v["n"] for v in res["per_feature"].values())
    forb = L.check_forbidden(p)
    assert forb["leaks_into_any_matrix"] == [] and forb["matrix_refuses_each_banned_column"]
    assert fv.trait_column("milady", "Number") in forb["banned_columns"]


def test_committed_leakage_report_covers_2000_sales_and_every_feature_is_equal():
    if not L.REPORT.exists():
        pytest.skip("run python -m ml.nft.fv_leakage")
    r = json.loads(L.REPORT.read_text(encoding="utf-8"))
    c1, c2 = r["check1_reference_on_cut_data"], r["check2_pipeline_on_cut_data"]
    assert c1["n_sales"] >= 2000 and set(fv.DYNAMIC + fv.STATIC) <= set(c1["per_feature"])
    assert all(v["n_equal"] == v["n"] for c in (c1, c2) for v in c["per_feature"].values())
    assert r["check3_forbidden_columns"]["leaks_into_any_matrix"] == []
