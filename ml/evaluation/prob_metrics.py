"""Metrics for predicted class probabilities (Phase 4c, D31). Pure functions, no I/O.

Kept apart from metrics.py so that module stays under 300 lines (AGENTS rule 7).
"""

import numpy as np

from ml.evaluation.metrics import calibration_bins


def log_loss_rows(prob, actual, classes) -> np.ndarray:
    """Per-row multiclass log loss: -ln p(actual class). Probabilities must already be clipped above 0."""
    p = np.asarray(prob, dtype=float)
    col = np.array([classes.index(a) for a in actual])
    return -np.log(p[np.arange(len(p)), col])


def ece(prob, actual, classes, n_bins: int = 10) -> dict:
    """Expected calibration error per class (one-vs-rest) and their mean.

    ece = sum over bins of count/n * |mean predicted probability - observed frequency|; empty bins add 0.
    """
    p, a = np.asarray(prob, dtype=float), np.asarray(actual)
    per_class = {}
    for k, cls in enumerate(classes):
        bins = calibration_bins(p[:, k], (a == cls).astype(float), n_bins)
        per_class[cls] = float(sum(b["count"] / len(a) * abs(b["mean_prob"] - b["observed_freq"])
                                   for b in bins if b["count"]))
    return {"per_class": per_class, "macro": float(np.mean(list(per_class.values())))}
