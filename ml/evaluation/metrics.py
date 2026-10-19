"""Evaluation metrics (docs/EVALUATION.md). Pure functions, no I/O.

A metric that is undefined for the given inputs (for example recall of a class that never occurs)
returns None, never a made-up number. classification_summary adds a note for each None.
"""

import math

import numpy as np
import pandas as pd


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


# ---------- price / return ----------

def mae(pred, actual) -> float:
    return float(np.mean(np.abs(_arr(pred) - _arr(actual))))


def rmse(pred, actual) -> float:
    return float(np.sqrt(np.mean((_arr(pred) - _arr(actual)) ** 2)))


def mape(pred, actual) -> float:
    """Mean absolute percentage error of prices, in percent (0-100+ scale)."""
    p, a = _arr(pred), _arr(actual)
    return float(np.mean(np.abs(p - a) / np.abs(a)) * 100)


def directional_accuracy(pred, actual) -> float | None:
    """Share of rows where sign(pred) == sign(actual), ignoring rows with pred == 0. None if all are 0."""
    p, a = _arr(pred), _arr(actual)
    keep = p != 0
    if not keep.any():
        return None
    return float(np.mean(np.sign(p[keep]) == np.sign(a[keep])))


def skill_vs_naive(mae_model: float, mae_naive: float) -> float | None:
    """1 - MAE_model / MAE_naive. Above 0 beats the naive forecast."""
    return None if mae_naive == 0 else float(1 - mae_model / mae_naive)


# ---------- classification ----------

def confusion_matrix(actual, pred, classes) -> list[list[int]]:
    """Rows = actual class, columns = predicted class, both in `classes` order."""
    a, p = list(actual), list(pred)
    pos = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(classes)), dtype=int)
    for x, y in zip(a, p):
        m[pos[x], pos[y]] += 1
    return m.tolist()


def accuracy(actual, pred) -> float:
    return float(np.mean(np.asarray(actual) == np.asarray(pred)))


def per_class_precision_recall(actual, pred, classes) -> dict:
    """Per class: precision (None if never predicted), recall (None if never actual), support, predicted."""
    m = np.asarray(confusion_matrix(actual, pred, classes))
    out = {}
    for i, c in enumerate(classes):
        tp, n_pred, n_true = m[i, i], m[:, i].sum(), m[i, :].sum()
        out[c] = {
            "precision": float(tp / n_pred) if n_pred else None,
            "recall": float(tp / n_true) if n_true else None,
            "support": int(n_true),
            "predicted": int(n_pred),
        }
    return out


def balanced_accuracy(actual, pred, classes) -> float | None:
    """Mean recall over the classes that occur in `actual`."""
    recalls = [v["recall"] for v in per_class_precision_recall(actual, pred, classes).values()]
    recalls = [r for r in recalls if r is not None]
    return float(np.mean(recalls)) if recalls else None


def macro_f1(actual, pred, classes) -> float | None:
    """Mean F1 = 2TP / (2TP + FP + FN) over classes that occur in actual or pred."""
    m = np.asarray(confusion_matrix(actual, pred, classes))
    f1s = []
    for i in range(len(classes)):
        tp, fp, fn = m[i, i], m[:, i].sum() - m[i, i], m[i, :].sum() - m[i, i]
        if 2 * tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f1s)) if f1s else None


def mcc(actual, pred, classes) -> float | None:
    """Multiclass Matthews correlation (Gorodkin). None when undefined (constant actual or pred)."""
    m = np.asarray(confusion_matrix(actual, pred, classes), dtype=float)
    s, c = m.sum(), np.trace(m)
    t, p = m.sum(axis=1), m.sum(axis=0)
    denom = math.sqrt((s ** 2 - (p ** 2).sum()) * (s ** 2 - (t ** 2).sum()))
    return None if denom == 0 else float((c * s - (t * p).sum()) / denom)


def one_hot(pred, classes) -> np.ndarray:
    pos = {c: i for i, c in enumerate(classes)}
    out = np.zeros((len(pred), len(classes)))
    for row, c in enumerate(pred):
        out[row, pos[c]] = 1.0
    return out


def brier_multiclass(prob, actual, classes) -> float:
    """Mean over rows of sum_k (p_k - y_k)^2. 0 is perfect, 2 is the worst."""
    return float(np.mean(((np.asarray(prob, dtype=float) - one_hot(actual, classes)) ** 2).sum(axis=1)))


def _auc_binary(score: np.ndarray, positive: np.ndarray) -> float | None:
    n_pos, n_neg = positive.sum(), (~positive).sum()
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def roc_auc_ovr(prob, actual, classes) -> float | None:
    """Macro one-vs-rest ROC-AUC over classes that occur in `actual` (and are not every row)."""
    prob, a = np.asarray(prob, dtype=float), np.asarray(actual)
    aucs = [_auc_binary(prob[:, i], a == c) for i, c in enumerate(classes)]
    aucs = [x for x in aucs if x is not None]
    return float(np.mean(aucs)) if aucs else None


def classification_summary(actual, pred, classes) -> dict:
    """All hard-prediction metrics, with a note for every value that is null."""
    pcr = per_class_precision_recall(actual, pred, classes)
    out = {
        "accuracy": accuracy(actual, pred),
        "balanced_accuracy": balanced_accuracy(actual, pred, classes),
        "macro_f1": macro_f1(actual, pred, classes),
        "mcc": mcc(actual, pred, classes),
        "brier_one_hot": brier_multiclass(one_hot(pred, classes), actual, classes),
        "per_class": pcr,
        "confusion_matrix": {"labels": list(classes), "rows_actual_cols_predicted": confusion_matrix(actual, pred, classes)},
    }
    notes = []
    absent = [c for c, v in pcr.items() if v["support"] == 0]
    never = [c for c, v in pcr.items() if v["predicted"] == 0]
    if absent:
        notes.append(f"class(es) {absent} never occur in the actual labels: their recall is null; "
                     "balanced_accuracy averages recall over the classes that do occur")
    if never:
        notes.append(f"class(es) {never} are never predicted: their precision is null")
    if out["mcc"] is None:
        notes.append("mcc is null: undefined when the predictions (or the actual labels) are a single class")
    if notes:
        out["note"] = "; ".join(notes)
    return out


# ---------- risk ranking ----------

def spearman(pred, actual) -> float | None:
    """Rank correlation. None if either input is constant."""
    rp = pd.Series(_arr(pred)).rank(method="average")
    ra = pd.Series(_arr(actual)).rank(method="average")
    if rp.std() == 0 or ra.std() == 0:
        return None
    return float(np.corrcoef(rp, ra)[0, 1])


# ---------- intervals ----------

def empirical_coverage(lower, upper, actual) -> float:
    a = _arr(actual)
    return float(np.mean((a >= _arr(lower)) & (a <= _arr(upper))))


def mean_width(lower, upper) -> float:
    return float(np.mean(_arr(upper) - _arr(lower)))


# ---------- calibration ----------

def calibration_bins(prob, outcome, n_bins: int = 10) -> list[dict]:
    """Equal-width bins on [0, 1]: count, mean predicted probability and observed frequency per bin."""
    p, y = _arr(prob), _arr(outcome)
    idx = np.minimum((p * n_bins).astype(int), n_bins - 1)
    bins = []
    for b in range(n_bins):
        sel = idx == b
        bins.append({
            "bin_low": b / n_bins, "bin_high": (b + 1) / n_bins, "count": int(sel.sum()),
            "mean_prob": float(p[sel].mean()) if sel.any() else None,
            "observed_freq": float(y[sel].mean()) if sel.any() else None,
        })
    return bins


# ---------- strategy (non-overlapping windows) ----------

def cumulative_return(window_returns) -> float:
    """Compounded simple return over consecutive windows."""
    return float(np.prod(1 + _arr(window_returns)) - 1)


def max_drawdown(window_returns) -> float:
    """Largest fall of the equity curve from a previous peak (negative or 0). Equity starts at 1."""
    equity = np.r_[1.0, np.cumprod(1 + _arr(window_returns))]
    return float((equity / np.maximum.accumulate(equity) - 1).min())


def sharpe(window_returns, periods_per_year: float) -> float | None:
    """mean / std of per-window returns, annualised by sqrt(periods_per_year). None if std is 0."""
    r = _arr(window_returns)
    sd = r.std(ddof=1) if len(r) > 1 else 0.0
    return None if sd == 0 else float(r.mean() / sd * math.sqrt(periods_per_year))


# ---------- uncertainty ----------

def bootstrap_ci(values, stat_fn, block_size: int = 30, n_boot: int = 1000, seed: int = 0,
                 level: float = 0.95) -> dict | None:
    """Moving-block bootstrap CI of stat_fn(values). Blocks keep neighbouring (overlapping) rows together.

    None if there are fewer values than one block.
    """
    v = np.asarray(values, dtype=float)
    n = len(v)
    if n < block_size or block_size < 1:
        return None
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block_size)
    starts = rng.integers(0, n - block_size + 1, size=(n_boot, n_blocks))
    offsets = np.arange(block_size)
    stats = np.empty(n_boot)
    for i in range(n_boot):
        sample = v[(starts[i][:, None] + offsets).ravel()[:n]]
        stats[i] = stat_fn(sample)
    alpha = (1 - level) / 2
    return {"low": float(np.quantile(stats, alpha)), "high": float(np.quantile(stats, 1 - alpha)),
            "level": level, "block_size": block_size, "n_boot": n_boot, "seed": seed}
