"""Evaluation guard (D40): report writers run only on the evaluation snapshot.

Splits are derived from n (D16, D18), so evaluating on the serving data (newer, longer CSVs) would move the sealed
test boundary. Every report writer under ml/evaluation and ml.data.dataset_summary calls require_snapshot() first.
"""

import sys
from pathlib import Path

from ml import config


def snapshot_mismatches() -> list[str]:
    """'NAME=path' for each data directory that is not the evaluation snapshot default."""
    pairs = (("ML_RAW_DIR", config.ML_RAW_DIR, config.EVALUATION_RAW_DIR),
             ("ML_VALIDATION_DIR", config.ML_VALIDATION_DIR, config.EVALUATION_VALIDATION_DIR))
    return [f"{name}={cur}" for name, cur, snap in pairs if Path(cur).resolve() != Path(snap).resolve()]


def require_snapshot() -> None:
    """Exit 1 with a D40 message unless both data directories are the evaluation snapshot."""
    bad = snapshot_mismatches()
    if bad:
        sys.exit(f"refusing to write evaluation reports: {', '.join(bad)} is not the evaluation snapshot (D40). "
                 "Unset ML_RAW_DIR and ML_VALIDATION_DIR; evaluating newer data needs a new D-number that fixes "
                 "the split dates.")
