"""Unit tests for ml.evaluation.metrics and the baseline rules.

All fixtures below are small HAND-MADE numbers, NOT market data. Expected values are computed by hand
in the comments. No network calls.
"""

import math

import numpy as np
import pandas as pd
import pytest

from ml.evaluation import baselines as bl
from ml.evaluation import metrics as m

ABC = ("A", "B", "C")
# actual A A B C, predicted A B B A -> confusion [[1,1,0],[0,1,0],[1,0,0]]
ACT, PRED = ["A", "A", "B", "C"], ["A", "B", "B", "A"]


# ---------- price ----------

def test_mae_rmse_mape():
    assert m.mae([1, 2, 3], [2, 2, 5]) == pytest.approx(1.0)              # (1+0+2)/3
    assert m.rmse([1, 2, 3], [2, 2, 5]) == pytest.approx(math.sqrt(5 / 3))  # sqrt((1+0+4)/3)
    assert m.mape([110, 90], [100, 100]) == pytest.approx(10.0)           # 10% and 10%


def test_directional_accuracy_ignores_zero_predictions():
    # row 3 predicts 0 -> ignored; signs match on rows 1 and 4, not row 2 -> 2/3
    assert m.directional_accuracy([0.1, -0.2, 0, 0.3], [0.2, 0.1, -5, 0.1]) == pytest.approx(2 / 3)
    assert m.directional_accuracy([0, 0], [1, -1]) is None


def test_skill_vs_naive():
    assert m.skill_vs_naive(2.0, 4.0) == pytest.approx(0.5)
    assert m.skill_vs_naive(4.0, 4.0) == pytest.approx(0.0)


# ---------- classification ----------

def test_confusion_and_basic_scores():
    assert m.confusion_matrix(ACT, PRED, ABC) == [[1, 1, 0], [0, 1, 0], [1, 0, 0]]
    assert m.accuracy(ACT, PRED) == pytest.approx(0.5)
    # recall A=1/2, B=1, C=0 -> mean 0.5
    assert m.balanced_accuracy(ACT, PRED, ABC) == pytest.approx(0.5)
    # F1 = 2TP/(2TP+FP+FN): A 2/4, B 2/3, C 0/1 -> mean 7/18
    assert m.macro_f1(ACT, PRED, ABC) == pytest.approx(7 / 18)


def test_per_class_precision_recall():
    pcr = m.per_class_precision_recall(ACT, PRED, ABC)
    assert pcr["A"] == {"precision": 0.5, "recall": 0.5, "support": 2, "predicted": 2}
    assert pcr["B"] == {"precision": 0.5, "recall": 1.0, "support": 1, "predicted": 2}
    assert pcr["C"]["precision"] is None and pcr["C"]["recall"] == 0.0


def test_mcc_hand_value():
    # s=4, c=2, t=[2,1,1], p=[2,2,0]: (2*4 - 6) / sqrt((16-8)*(16-6)) = 2/sqrt(80)
    assert m.mcc(ACT, PRED, ABC) == pytest.approx(2 / math.sqrt(80))


def test_perfect_predictor():
    a = ["A", "B", "C", "A", "B"]
    assert m.accuracy(a, a) == 1.0
    assert m.mcc(a, a, ABC) == pytest.approx(1.0)
    assert m.balanced_accuracy(a, a, ABC) == 1.0 and m.macro_f1(a, a, ABC) == 1.0
    assert m.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_all_wrong_binary_predictor():
    a, p = [0, 1, 0, 1], [1, 0, 1, 0]
    assert m.accuracy(a, p) == 0.0
    assert m.mcc(a, p, (0, 1)) == pytest.approx(-1.0)


def test_constant_predictor_balanced_accuracy():
    a = ["A", "B", "C", "A", "B", "C"]
    p = ["A"] * 6
    assert m.balanced_accuracy(a, p, ABC) == pytest.approx(1 / 3)
    assert m.mcc(a, p, ABC) is None                     # undefined, not invented


def test_absent_class_is_null_with_note():
    a, p = ["A", "B", "A", "B"], ["A", "B", "B", "B"]   # C never occurs and is never predicted
    s = m.classification_summary(a, p, ABC)
    assert s["per_class"]["C"]["recall"] is None and s["per_class"]["C"]["precision"] is None
    assert "['C']" in s["note"]
    assert s["balanced_accuracy"] == pytest.approx((0.5 + 1.0) / 2)   # over A and B only


def test_brier_multiclass():
    # row 1 perfect (0); row 2: (0.5-0)^2 + (0.5-1)^2 = 0.5 -> mean 0.25
    assert m.brier_multiclass([[1, 0], [0.5, 0.5]], ["a", "b"], ("a", "b")) == pytest.approx(0.25)


def test_roc_auc_ovr():
    # class 1 scores [0.1, 0.4, 0.35, 0.8], actual [0,0,1,1]: 3 of 4 pos/neg pairs ordered -> 0.75
    p1 = np.array([0.1, 0.4, 0.35, 0.8])
    prob = np.c_[1 - p1, p1]
    assert m.roc_auc_ovr(prob, [0, 0, 1, 1], (0, 1)) == pytest.approx(0.75)


# ---------- risk ranking ----------

def test_spearman_hand_value_and_constant():
    # ranks x 1..5, ranks y 1,2,3.5,5,3.5 -> 8 / sqrt(10 * 9.5)
    assert m.spearman([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]) == pytest.approx(8 / math.sqrt(95))
    assert m.spearman([1, 1, 1], [1, 2, 3]) is None


# ---------- intervals and calibration ----------

def test_coverage_and_width():
    lo, hi = [0, 0, 0, 0], [1, 1, 1, 1]
    assert m.empirical_coverage(lo, hi, [0.5, 1, 1.5, -0.1]) == pytest.approx(0.5)   # 0.5 and 1 inside
    assert m.mean_width(lo, hi) == pytest.approx(1.0)


def test_calibration_bins():
    bins = m.calibration_bins([0.05, 0.15, 0.95, 1.0], [0, 1, 1, 1], n_bins=10)
    assert len(bins) == 10
    assert bins[0]["count"] == 1 and bins[0]["observed_freq"] == 0.0
    assert bins[9]["count"] == 2 and bins[9]["mean_prob"] == pytest.approx(0.975)
    assert bins[5]["count"] == 0 and bins[5]["mean_prob"] is None


# ---------- strategy ----------

def test_strategy_metrics():
    assert m.cumulative_return([0.1, -0.1]) == pytest.approx(-0.01)        # 1.1*0.9 - 1
    assert m.max_drawdown([0.1, -0.5, 0.2]) == pytest.approx(-0.5)         # 1.1 -> 0.55
    assert m.sharpe([0.1, 0.3], 4) == pytest.approx(0.2 / math.sqrt(0.02) * 2)
    assert m.sharpe([0.0, 0.0], 4) is None


# ---------- bootstrap ----------

def test_bootstrap_reproducible_and_sane():
    v = np.sin(np.arange(120) / 5)
    a = m.bootstrap_ci(v, np.mean, block_size=30, n_boot=200, seed=0)
    b = m.bootstrap_ci(v, np.mean, block_size=30, n_boot=200, seed=0)
    c = m.bootstrap_ci(v, np.mean, block_size=30, n_boot=200, seed=1)
    assert a == b and a != c
    assert a["low"] <= v.mean() <= a["high"]
    # one block covering the whole series: every resample is the series itself
    full = m.bootstrap_ci(v, np.mean, block_size=120, n_boot=50)
    assert full["low"] == pytest.approx(v.mean()) and full["high"] == pytest.approx(v.mean())
    assert m.bootstrap_ci(v[:10], np.mean, block_size=30) is None


# ---------- paired bootstrap (hand-made fixtures, not market data) ----------

def _spearman_rows(x):
    return m.spearman(x[:, 0], x[:, 1])


def test_paired_bootstrap_identical_inputs_contains_zero():
    t = np.arange(150, dtype=float)
    actual = np.sin(t / 7) + 0.01 * t
    pred = np.c_[actual + np.cos(t / 3), actual]
    ci = m.paired_bootstrap_ci(pred, pred.copy(), _spearman_rows, block_size=30, n_boot=200)
    assert ci["estimate"] == 0.0 and ci["low"] <= 0.0 <= ci["high"]


def test_paired_bootstrap_better_predictor_above_zero():
    t = np.arange(150, dtype=float)
    actual = np.sin(t / 7) + 0.01 * t
    good = np.c_[actual + 0.05 * np.cos(t * 1.3), actual]      # nearly perfect ranking
    bad = np.c_[np.cos(t * 2.1), actual]                        # unrelated to the actual values
    ci = m.paired_bootstrap_ci(good, bad, _spearman_rows, block_size=30, n_boot=200)
    assert ci["estimate"] > 0 and ci["low"] > 0


def test_paired_bootstrap_reproducible_and_validates():
    t = np.arange(120, dtype=float)
    a, b = np.c_[np.sin(t / 5), t], np.c_[np.cos(t / 5), t]
    one = m.paired_bootstrap_ci(a, b, _spearman_rows, n_boot=100, seed=3)
    assert one == m.paired_bootstrap_ci(a, b, _spearman_rows, n_boot=100, seed=3)
    assert one != m.paired_bootstrap_ci(a, b, _spearman_rows, n_boot=100, seed=4)
    assert m.paired_bootstrap_ci(a[:10], b[:10], _spearman_rows) is None
    with pytest.raises(ValueError):
        m.paired_bootstrap_ci(a, b[:-1], _spearman_rows)


# ---------- baseline rules ----------

def test_majority_class_and_tie_break():
    assert bl.majority_class(pd.Series(["B", "C", "C", None]), ABC) == "C"
    assert bl.majority_class(pd.Series(["C", "A"]), ABC) == "A"            # tie -> earlier class


def test_window_starts_are_non_overlapping_and_labelled():
    labelled = pd.Series([True] * 100 + [False] * 30)
    assert bl.window_starts(range(10, 130), labelled) == [10, 40, 70]      # 100 has no label
    r = bl.strategy_window_returns(pd.Series(np.log([1.1, 0.9, 1.0])), [0, 1, 2])
    assert r["buy_and_hold"] == pytest.approx([0.1, -0.1, 0.0])
    assert r["always_hold"].tolist() == [0.0, 0.0, 0.0]
