"""D85 live accuracy log: matching, settling, alerts and the job runner. No live data needed."""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from ml.nft import fv_jobs, live_accuracy as la

H = 3600


def _est(logged_at, token="1", est=1.1, floor=1.0, slug="azuki", decile=5, version="v"):
    return {"logged_at": logged_at, "slug": slug, "token_id": token, "method": "model", "y_hat": np.log(est / floor),
            "floor_eth": floor, "floor_time": logged_at - 60, "estimated_value_eth": est, "no_prior_sale": False,
            "rarity_decile": decile, "model_version": version}


def test_each_sale_takes_the_latest_estimate_logged_before_it_within_48_hours():
    t0 = 1_000_000
    est = pd.DataFrame([_est(t0, est=1.0), _est(t0 + 24 * H, est=1.2), _est(t0 + 48 * H, est=9.0),
                        _est(t0, token="2", est=2.0), _est(t0 - 100 * H, token="3", est=3.0)])
    sales = pd.DataFrame({"slug": "azuki", "token_id": ["1", "1", "2", "3"], "tx": list("abcd"),
                          "timestamp": [t0 + 30 * H, t0 + 48 * H, t0 + 49 * H, t0], "price_eth": [1.0, 1.5, 2.5, 3.0]})
    m = la.match(sales, est).set_index("tx")
    assert m.loc["a", "estimated_value_eth"] == 1.2                       # latest before the sale, not the next one
    assert m.loc["b", "estimated_value_eth"] == 1.2                       # an estimate AT the sale time is not used
    assert not m.loc["c", "matched"]                                      # 49 h old: too old
    assert not m.loc["d", "matched"]                                      # logged long before
    assert m.loc["a", "ape_served"] == pytest.approx(0.2) and m.loc["a", "ape_b0"] == pytest.approx(0.0)


def test_a_month_is_summarised_only_once_its_sales_are_30_days_old():
    assert not la.settled("2026-11", datetime(2026, 12, 30, tzinfo=timezone.utc))
    assert la.settled("2026-11", datetime(2026, 12, 31, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="not settled"):
        la.summarize("2026-11", datetime(2026, 12, 15, tzinfo=timezone.utc))


def test_alert_needs_two_consecutive_months_behind_b0():
    cur = {"by_collection": {"azuki": {"mdape_served": 0.05, "mdape_b0": 0.04},
                             "milady": {"mdape_served": 0.03, "mdape_b0": 0.04},
                             "doodles-official": {"mdape_served": 0.06, "mdape_b0": 0.04}}}
    prev = {"by_collection": {"azuki": {"mdape_served": 0.05, "mdape_b0": 0.04},
                              "doodles-official": {"mdape_served": 0.03, "mdape_b0": 0.04}}}
    assert la.alerts(cur, prev) == {"azuki": "ALERT", "milady": "ok", "doodles-official": "behind B0"}
    assert la.alerts(cur, None)["azuki"] == "behind B0"


def test_due_months_are_settled_logged_and_not_yet_summarised(tmp_path):
    d, out = tmp_path / "nft", tmp_path / "docs"
    la.est_dir(d).mkdir(parents=True)
    for day in ("2026-11-14", "2026-11-30", "2026-12-01"):
        (la.est_dir(d) / f"{day}.csv.gz").write_bytes(b"")
    now = datetime(2027, 1, 1, 0, 30, tzinfo=timezone.utc)
    assert la.due_months(now, d, out) == ["2026-11"]
    out.mkdir()
    (out / "2026-11.json").write_text("{}", encoding="utf-8")
    assert la.due_months(now, d, out) == []


def test_jobs_report_failures_and_never_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(fv_jobs.config, "ML_NFT_DIR", tmp_path)
    monkeypatch.setattr(fv_jobs.fv_refit, "due", lambda now: True)
    monkeypatch.setattr(fv_jobs.fv_refit, "refit", lambda r: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(fv_jobs.live_accuracy, "record", lambda now: {"rows": 3})
    monkeypatch.setattr(fv_jobs.live_accuracy, "due_months", lambda now: [])
    s = fv_jobs.after_refresh(datetime(2026, 12, 1, 0, 10, tzinfo=timezone.utc))
    assert s["jobs"]["refit"] == {"status": "failed", "error": "RuntimeError: boom"}
    assert s["jobs"]["record"]["status"] == "ok"
    assert json.loads((tmp_path / fv_jobs.STATUS_FILE).read_text(encoding="utf-8"))["jobs"]["record"]["result"] == {"rows": 3}


def test_markdown_lists_every_collection_and_decile():
    s = {"month": "2026-11", "generated_at": "x", "rule": "r",
         "pooled": {"n_sales": 2, "n_matched": 1, "mdape_served": 0.03, "mdape_b0": 0.04},
         "by_collection": {"azuki": {"n_sales": 2, "n_matched": 1, "mdape_served": 0.03, "mdape_b0": 0.04,
                                     "method": "model"}},
         "by_rarity_decile": {"1": {"n_matched": 1, "mdape_served": 0.03, "mdape_b0": 0.04}},
         "alerts": {"azuki": "ok"}}
    md = la.markdown(s)
    assert "| azuki (model) | 2 | 1 | 3.00% | 4.00% | ok |" in md and "| 1 | 1 | 3.00% | 4.00% |" in md
