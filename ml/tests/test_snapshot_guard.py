"""Tests for the evaluation guard (Phase 6c, D40): report writers run only on the evaluation snapshot.

No data is read and no report is written: each module's first step after the guard is replaced by a stub that
raises, so "runs normally" means main() got past the guard. Paths are temporary; no network calls.
"""

import importlib
import sys

import pytest

from ml import config
from ml.data import snapshot_guard

GUARDED = ["ml.evaluation.run_backtest", "ml.evaluation.run_baselines", "ml.evaluation.run_walkforward",
           "ml.evaluation.run_walkforward_direction", "ml.evaluation.run_walkforward_price",
           "ml.evaluation.run_walkforward_risk", "ml.evaluation.power_check", "ml.evaluation.direction_mechanism",
           "ml.evaluation.risk_mapping_check", "ml.data.dataset_summary"]
FIRST_STEP = {"ml.evaluation.power_check": "run"}           # the others call require_validated first


class Proceeded(Exception):
    """Raised by the stub: main() passed the guard."""


@pytest.fixture
def on_snapshot(monkeypatch):
    monkeypatch.setattr(config, "ML_RAW_DIR", config.EVALUATION_RAW_DIR)
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", config.EVALUATION_VALIDATION_DIR)


@pytest.mark.usefixtures("on_snapshot")
def test_helper_passes_on_the_snapshot_and_refuses_anything_else(monkeypatch, tmp_path):
    assert snapshot_guard.snapshot_mismatches() == []
    snapshot_guard.require_snapshot()
    monkeypatch.setattr(config, "ML_RAW_DIR", config.EVALUATION_RAW_DIR / ".." / "raw")    # same dir, other spelling
    snapshot_guard.require_snapshot()
    monkeypatch.setattr(config, "ML_VALIDATION_DIR", tmp_path / "validation")
    assert snapshot_guard.snapshot_mismatches() == [f"ML_VALIDATION_DIR={tmp_path / 'validation'}"]
    with pytest.raises(SystemExit, match=r"ML_VALIDATION_DIR=.* is not the evaluation snapshot \(D40\)"):
        snapshot_guard.require_snapshot()
    monkeypatch.setattr(config, "ML_RAW_DIR", tmp_path / "raw")
    assert len(snapshot_guard.snapshot_mismatches()) == 2


@pytest.mark.usefixtures("on_snapshot")
@pytest.mark.parametrize("name", GUARDED)
def test_each_report_writer_refuses_serving_dirs_and_runs_on_the_snapshot(monkeypatch, tmp_path, name):
    module = importlib.import_module(name)

    def stub(*args, **kwargs):
        raise Proceeded

    monkeypatch.setattr(module, FIRST_STEP.get(name, "require_validated"), stub)
    monkeypatch.setattr(sys, "argv", [name, "--asset", "btc"])
    with pytest.raises(Proceeded):
        module.main()                                         # on the snapshot: runs normally
    monkeypatch.setattr(config, "ML_RAW_DIR", tmp_path / "serving" / "raw")
    with pytest.raises(SystemExit, match=r"refusing to write evaluation reports: ML_RAW_DIR=.*\(D40\)"):
        module.main()                                         # serving dirs: exits before the stub runs
