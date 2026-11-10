"""D66 causality (Phase 10 step 10.5b): for every t, guard_spikes(series[:t+1])[t] == guard_spikes(series)[t], so a
held day is never revised later. Checked on all 7 real collections (the tracked frozen floor.parquet) and on
synthetic series. The full daily_floor rows are checked the same way: a later point never changes an earlier row."""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.nft import floor as fl, snapshot


def _prefix_equal(x: np.ndarray) -> list[int]:
    full_model, full_held = fl.guard_spikes(x)
    bad = []
    for t in range(len(x)):
        m, h = fl.guard_spikes(x[:t + 1])
        if m[t] != full_model[t] or h[t] != full_held[t]:
            bad.append(t)
    return bad


def _real_floor():
    path = snapshot.snapshot_dir() / "floor.parquet"
    if not path.exists():
        pytest.skip("frozen floor.parquet missing")
    return pd.read_parquet(path)


@pytest.mark.parametrize("slug", config.NFT_SLUGS)
def test_guard_is_causal_on_every_real_collection(slug):
    f = _real_floor()
    g = f[f["slug"] == slug].sort_values("date")
    x = g["floor_eth_asof"].to_numpy(dtype=float)
    assert len(x) > 700
    assert _prefix_equal(x) == []
    model, held = fl.guard_spikes(x)
    np.testing.assert_array_equal(model, g["floor_eth_model"].to_numpy())          # what the snapshot stores
    np.testing.assert_array_equal(held, g["floor_spike"].to_numpy())


@pytest.mark.parametrize("seed", range(20))
def test_guard_is_causal_on_synthetic_series_with_spikes_and_level_shifts(seed):
    rng = np.random.default_rng(seed)
    x = np.exp(np.cumsum(rng.normal(0, 0.05, 300)))
    for i in rng.choice(np.arange(1, 300), 25, replace=False):      # one-day spikes up and down
        x[i] *= rng.choice([0.05, 0.2, 3.0, 10.0])
    for i in rng.choice(np.arange(1, 300), 5, replace=False):       # lasting level shifts
        x[i:] *= rng.choice([0.3, 2.5])
    assert _prefix_equal(x) == []


def test_guard_edge_cases_are_causal():
    for x in ([1.0], [1.0, 3.0], [1.0, 0.4, 0.41, 0.42], [1.0, 2.0, 4.0, 8.0, 16.0], [5.0, 0.1, 0.1, 5.0, 0.1, 0.1],
              [1.0, 2.0001, 1.0, 0.4999]):
        assert _prefix_equal(np.array(x)) == [], x


def test_daily_floor_rows_never_change_when_later_points_arrive():
    pts = _real_floor()                                               # source points come from the base snapshot
    points = pd.read_parquet(snapshot.snapshot_dir() / "floor_points.parquet")
    p = points[points["slug"] == "azuki"].sort_values("time")
    full = fl.daily_floor(p, "2026-11-10")
    for cut_day in ("2025-01-31", "2025-02-16", "2025-12-31", "2026-07-01"):
        cut = int(pd.Timestamp(cut_day, tz="UTC").timestamp())
        part = fl.daily_floor(p[p["time"] <= cut], cut_day)
        pd.testing.assert_frame_equal(part.reset_index(drop=True),
                                      full[full["date"] <= cut_day].reset_index(drop=True))
    assert len(pts)
