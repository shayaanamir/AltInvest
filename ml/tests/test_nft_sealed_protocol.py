"""Phase 10 step 10.8 preparation (D79): the sealed-test protocol, tested without any sealed data."""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.evaluation import run_nft_sealed_fv as st
from ml.nft import item_data


def test_window_months_and_cutoffs_are_as_declared():
    m = st.months(st.SEALED)
    assert [x["month"] for x in m] == ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
                                       "2026-09", "2026-10", "2026-11"]
    assert str(m[0]["train_end"].date()) == "2026-01-25" and str(m[-1]["test_end"].date()) == "2026-11-11"
    assert all(x["test_start"] - x["train_end"] == pd.Timedelta(days=7) for x in m)
    assert st.SEALED["first"] == config.NFT_FV_SEALED_START == "2026-02-01"
    d = st.months(st.DRY_RUN)                                   # the 10.6 confirmation folds 6-9
    assert [str(x["train_end"].date()) for x in d] == ["2025-09-24", "2025-10-25", "2025-11-24", "2025-12-25"]
    assert str(d[-1]["test_end"].date()) == "2026-01-25"


def test_history_loader_and_sealed_loader_refuse_every_step_now_that_the_sealed_test_is_spent():
    """10.9b MINOR 5: both loaders raise unconditionally, 10.8 included."""
    for f in (item_data.load_history, item_data.load_sealed):
        for step in ("10.7", "10.8", "10.9", ""):
            with pytest.raises(PermissionError, match="spent"):
                f(step)


def _rows(served_err, base_err):
    dates = pd.date_range("2026-02-01", periods=60).strftime("%Y-%m-%d")
    rows = pd.DataFrame({"date": np.repeat(dates, 2), "slug": ["azuki", "lilpudgys"] * 60, "y": 0.0})
    rows[f"ape:{config.NFT_FV_CANDIDATE}"] = served_err
    for b, e in zip(st.BASELINES, base_err):
        rows[f"ape:{b}"] = e
    return rows


def test_served_configuration_uses_b2_where_configured_and_the_pass_rule():
    serve = {"azuki": "model", "lilpudgys": "b2"}
    rows = _rows(0.02, (0.05, 0.06, 0.04))
    ape = st.served_ape(rows, serve)
    assert ape[rows["slug"] == "azuki"].tolist() == [0.02] * 60 and ape[rows["slug"] == "lilpudgys"].tolist() == [0.04] * 60
    v = st.decide(rows, serve)
    assert v["best_baseline"] == "B2_decile_90d" and v["pass"] and v["outcome"].startswith("PASS")
    v = st.decide(_rows(0.05, (0.05, 0.06, 0.04)), serve)                # served no better than B2: FAIL
    assert not v["pass"] and v["outcome"] == "FAIL: every collection serves B2" and v["range_served"] is None


def test_sealed_mode_refuses_a_second_run(monkeypatch, tmp_path):
    rep = tmp_path / "sealed.json"
    rep.write_text("{}")
    monkeypatch.setitem(st.REPORTS, "sealed", rep)
    monkeypatch.setattr("sys.argv", ["x", "--sealed"])
    monkeypatch.setattr("ml.gitinfo.git_metadata", lambda: {"git_commit": "x", "git_dirty": False})
    called = []
    monkeypatch.setattr(item_data, "load_history", lambda step: called.append(step))
    with pytest.raises(SystemExit, match="runs once"):
        st.main()
    assert called == []                                             # refused before any data was read
