"""C4: the seed never writes predictions or risk_scores for the ML-covered assets."""
from db import seed_predictions_risk as seed
from db.queries import ML_COVERED_ASSETS


def test_seed_has_no_ml_covered_rows():
    assert not {p["asset"] for p in seed.PREDICTIONS} & set(ML_COVERED_ASSETS)
    assert not {r["asset"] for r in seed.RISK_SCORES} & set(ML_COVERED_ASSETS)


def test_seed_still_writes_other_assets():
    assert seed.PREDICTIONS and seed.RISK_SCORES
