"""Phase 9 step 9.6 sealed test: the D50 decision rule, the once-only guard, and the scoring helpers.

All fixtures below are small HAND-MADE numbers from simple formulas, NOT market data. No network calls.
The real sealed test is never run here.
"""

import numpy as np
import pandas as pd
import pytest

from ml.evaluation import run_sealed_test as st


def _risk(nw):
    return {a: {30: {"not_worse": v}} for a, v in nw.items()}


def _range(conf_ok, test_ok):
    def part(ok):
        return {"coverage_in_bounds": ok, "tails_within_max": True}
    return {"confirmation": part(conf_ok), "test": part(test_ok)}


def test_ewma_is_served_for_all_assets_only_if_all_are_not_worse():
    ranges = {a: _range(True, True) for a in ("btc", "eth", "sol")}
    yes = st.decide(_risk({"btc": True, "eth": True, "sol": True}), ranges)
    no = st.decide(_risk({"btc": True, "eth": True, "sol": False}), ranges)
    assert yes["risk"]["serve_ewma_for_all_assets"] is True
    assert no["risk"]["serve_ewma_for_all_assets"] is False
    assert yes["price"]["serve"] is False and yes["direction"]["serve"] is False


def test_band_needs_confirmation_and_test():
    ranges = {"btc": _range(False, True), "eth": _range(True, False), "sol": _range(True, True)}
    d = st.decide(_risk({"btc": True, "eth": True, "sol": True}), ranges)
    assert d["range"]["serve_vol30_band_h30"] == {"btc": False, "eth": False, "sol": True}


def test_refuses_a_second_run(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "ML_ROOT", tmp_path)
    st.refuse_if_run()                                            # nothing there yet
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / st.SUMMARY).write_text("{}")
    with pytest.raises(SystemExit, match="already been run"):
        st.refuse_if_run()


def _frame(n=120, h=7):
    """Hand-made test rows: realised vol drifts; EWMA tracks it closer than vol_30d."""
    i = np.arange(n, dtype=float)
    actual = 0.02 + 0.01 * np.sin(i / 15)
    return pd.DataFrame({"vol_30d": np.full(n, 0.02), "ewma_vol": actual * 1.02, f"fwd_vol_{h}d": actual,
                         "fwd_return_30d": 0.05 * np.sin(i / 3)},
                        index=pd.date_range("2025-06-07", periods=n, freq="D", tz="UTC"))


def test_risk_test_scores_ewma_against_persistence():
    res = st.risk_test(_frame(), 7)
    assert res["qlike_ewma"] < res["qlike_persistence"]
    assert res["not_worse"] is True and res["paired_diff_persistence_minus_ewma"]["block_size"] == 7
    assert res["n_effective"] == 120 / 7


def test_range_test_uses_the_vol30_band():
    test = _frame()
    pre = pd.DataFrame({"vol_30d": np.linspace(0.01, 0.03, 50)})
    res = st.range_test(test, pre)
    half = st.Z["hi"] * 0.02 * np.sqrt(30)
    inside = np.mean(np.abs(test["fwd_return_30d"]) <= half)
    assert res["coverage"] == pytest.approx(inside) and res["n_crossed"] == 0
    assert res["high_vol_threshold"] == pytest.approx(np.percentile(pre["vol_30d"], 67))
