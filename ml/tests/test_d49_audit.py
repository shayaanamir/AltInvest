"""D82: the D49 audit reads the logged Phase 9 results and applies top-only selection (D81); nothing is re-run."""

import json

import pytest

from ml.evaluation import d49_audit


def test_top_only_ranks_all_configs_together_and_confirms_only_the_top():
    out = d49_audit.audit()
    for a in d49_audit.ASSETS:
        for h in ("h30", "h7"):
            r = out["results"][a]["risk"][h]
            assert r["top_model"] == "garch" and r["approved_top_only"] is None      # GARCH ranks first, CI has 0
            assert r["ranking_loss"]["garch:garch_t"] < r["ranking_loss"]["ewma:ewma"]
        assert out["results"][a]["direction"]["h30"]["top_config"] == "logreg_c0.1"
    assert out["results"]["eth"]["direction"]["h30"]["approved_top_only"] == "logreg"
    assert out["ewma_approved_top_only_h30"] == {"btc": False, "eth": False, "sol": False}
    assert out["matches_current_approval"] is False and "WITHDRAWN" in out["outcome"]


def test_committed_audit_report_matches_the_logs():
    committed = json.loads(d49_audit.OUT.read_text(encoding="utf-8"))
    assert committed["results"] == d49_audit.audit()["results"]


def test_audit_refuses_configs_ranked_on_different_rows():
    m = {"a": {"ranking_first_60pct": {"n_pooled": 10, "date_range": ["x", "y"], "mean_loss": {"a": 1, "b": 2}}},
         "c": {"ranking_first_60pct": {"n_pooled": 11, "date_range": ["x", "y"], "mean_loss": {"c": 1, "b": 2}}}}
    with pytest.raises(ValueError, match="different rows"):
        d49_audit.top_only(m, "b", "test")
