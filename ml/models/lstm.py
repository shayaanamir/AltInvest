"""Pooled LSTM price candidate (D42): one model trained on BTC+ETH+SOL rows, scored per asset.

Target: fwd_return_{h}d. Input: the last LOOKBACK rows of FEATURE_COLUMNS ending at row t (all <= t).
Every scaler and the early-stopping split use the fold's TRAIN rows only: features are standardised per asset
with that asset's train mean/std; the target is divided by the pooled train std. Early stopping: the last
VAL_FRACTION of each asset's train rows, with an h-row gap before them so no fitting label reaches into them.
torch is imported inside the functions, so importing this module needs no training library.
"""

import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ml.features.features import FEATURE_COLUMNS

CONFIGS = {"lstm_h16": 16, "lstm_h32": 32}                      # 1 layer, hidden size (D42)
SETTINGS = {"layers": 1, "lookback": 60, "val_fraction": 0.15, "max_epochs": 50, "patience": 5,
            "batch_size": 256, "learning_rate": 1e-3, "loss": "mse", "optimizer": "adam", "seed": 0,
            "threads": min(4, os.cpu_count() or 1)}


@dataclass
class FittedLSTM:
    net: Any
    scalers: dict                                               # asset -> (mean, std) of its train features
    y_scale: float
    epochs: int
    best_val_loss: float


def _windows(x: np.ndarray, positions: np.ndarray, lookback: int) -> np.ndarray:
    """x[p - lookback + 1 .. p] for each position p (rows <= p only)."""
    view = np.lib.stride_tricks.sliding_window_view(x, lookback, axis=0)      # (n - L + 1, F, L)
    return np.ascontiguousarray(view[positions - lookback + 1].transpose(0, 2, 1), dtype=np.float32)


def _net(hidden: int):
    import torch

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = torch.nn.LSTM(len(FEATURE_COLUMNS), hidden, num_layers=1, batch_first=True)
            self.head = torch.nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    return Net()


def _seed():
    import torch
    torch.manual_seed(SETTINGS["seed"])
    torch.set_num_threads(SETTINGS["threads"])
    torch.use_deterministic_algorithms(True)


def fit(train_sets: dict[str, pd.DataFrame], config: str, horizon: int) -> FittedLSTM:
    """train_sets: asset -> its train rows from feature row 0 (features + the h-day label), in time order.

    An asset with fewer than `lookback` train rows (SOL before the early BTC/ETH cutoffs) has no complete window
    and contributes nothing to this fit. The predicted asset always has >= MIN_TRAIN_ROWS train rows."""
    import torch
    _seed()
    lb, y_col = SETTINGS["lookback"], f"fwd_return_{horizon}d"
    scalers, xs_fit, ys_fit, xs_val, ys_val = {}, [], [], [], []
    for asset, tr in train_sets.items():
        if len(tr) < lb:
            continue
        x = tr[FEATURE_COLUMNS].to_numpy(dtype=float)
        mean, std = x.mean(axis=0), x.std(axis=0)
        std = np.where(std == 0, 1.0, std)
        scalers[asset] = (mean, std)
        y = tr[y_col].to_numpy(dtype=float)
        pos = np.arange(lb - 1, len(tr))
        n_val = int(np.ceil(SETTINGS["val_fraction"] * len(pos)))
        val, fit_pos = pos[len(pos) - n_val:], pos[:max(0, len(pos) - n_val - horizon)]
        xz = (x - mean) / std
        xs_fit.append(_windows(xz, fit_pos, lb)); ys_fit.append(y[fit_pos])
        xs_val.append(_windows(xz, val, lb)); ys_val.append(y[val])
    y_fit = np.concatenate(ys_fit)
    y_scale = float(np.std(y_fit)) or 1.0
    xf, yf = torch.from_numpy(np.concatenate(xs_fit)), torch.from_numpy((y_fit / y_scale).astype(np.float32))
    xv = torch.from_numpy(np.concatenate(xs_val))
    yv = torch.from_numpy((np.concatenate(ys_val) / y_scale).astype(np.float32))

    net = _net(CONFIGS[config])
    opt = torch.optim.Adam(net.parameters(), lr=SETTINGS["learning_rate"])
    gen = torch.Generator().manual_seed(SETTINGS["seed"])
    best, best_state, bad, epochs = float("inf"), None, 0, 0
    for epoch in range(SETTINGS["max_epochs"]):
        net.train()
        for idx in torch.randperm(len(xf), generator=gen).split(SETTINGS["batch_size"]):
            opt.zero_grad()
            loss = torch.nn.functional.mse_loss(net(xf[idx]), yf[idx])
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            val_loss = float(torch.nn.functional.mse_loss(net(xv), yv))
        epochs = epoch + 1
        if val_loss < best:
            best, bad = val_loss, 0
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= SETTINGS["patience"]:
                break
    if best_state is None:
        raise ValueError(f"{config}: validation loss was never finite; nothing to keep")
    net.load_state_dict(best_state)
    net.eval()
    return FittedLSTM(net, scalers, y_scale, epochs, best)


def predict(fitted: FittedLSTM, asset: str, history: pd.DataFrame, rows: range) -> np.ndarray:
    """Predicted h-day log return for `rows` of `asset`. history: that asset's feature rows [0, rows.stop)."""
    import torch
    if len(history) < rows.stop:
        raise ValueError("history must cover every predicted row")
    mean, std = fitted.scalers[asset]
    xz = (history[FEATURE_COLUMNS].to_numpy(dtype=float)[:rows.stop] - mean) / std
    x = torch.from_numpy(_windows(xz, np.arange(rows.start, rows.stop), SETTINGS["lookback"]))
    with torch.no_grad():
        return fitted.net(x).numpy().astype(float) * fitted.y_scale
