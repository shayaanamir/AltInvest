"""Phase 9 step 9.6: the ONE-TIME sealed test (D44, D50). Runs exactly the D50 configs, nothing else.

    python -m ml.evaluation.run_sealed_test

Test rows: [b2, n - h) of each asset's feature table (the last h rows have no label). Nothing is fitted: EWMA
vol, persistence vol_30d and the vol_30d band are functions of closes <= t, so no test row is used for anything
but scoring. Writes ml/reports/{asset}/test_final.json and ml/reports/test_final_summary.json with the D50
serve / don't-serve decisions. Refuses to run if any of those files already exists (the test is used once).
  RISK (h = 30 all assets; h = 7 BTC, ETH, reports only): paired 95% CI (block = h) of QLIKE(persistence) -
    QLIKE(EWMA); 'not worse' = CI upper bound >= 0. EWMA is served for all assets only if all 3 are not worse at 30.
  RANGE (h = 30): vol_30d band calibration; served per asset only if it passes on confirmation AND on test.
"""

import json
from datetime import datetime, timezone

import numpy as np

from ml import config
from ml.data.dataset_summary import require_validated
from ml.data.loader import load_raw
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation import interval_metrics as im
from ml.evaluation import metrics as m
from ml.evaluation.run_baselines import _clean
from ml.evaluation.run_walkforward import dev_data
from ml.evaluation.run_walkforward_risk_v2 import qlike
from ml.evaluation.splits import make_splits
from ml.features.features import ewma_vol
from ml.gitinfo import git_metadata
from ml.models.range_v2 import Z

RISK_HORIZONS = {30: tuple(config.ASSETS), 7: ("btc", "eth")}      # D50; h = 7 is reports only
RANGE_H = 30
TOTAL_TRIALS = {"price": 60, "range": 18, "risk": 12, "direction": 12}   # D50
REPORT, SUMMARY = "test_final.json", "test_final_summary.json"


def report_paths() -> list:
    return [ML_ROOT / "reports" / a / REPORT for a in config.ASSETS] + [ML_ROOT / "reports" / SUMMARY]


def refuse_if_run() -> None:
    done = [str(p) for p in report_paths() if p.exists()]
    if done:
        raise SystemExit(f"the sealed test has already been run (D44, D50: used once): {done}")


def sealed_rows(asset: str, horizon: int):
    """(rows [b2, n - h) with features, labels and ewma_vol; b2; n; the pre-test frame for thresholds)."""
    raw = load_raw(asset)
    n = len(raw) - config.WARMUP_ROWS
    b2 = make_splits(n, embargo=horizon)["test"].start
    data = dev_data(raw, horizon)
    data["ewma_vol"] = ewma_vol(data["close"]).to_numpy()            # trailing: closes <= t only
    test = data.iloc[b2:]
    test = test[test[f"fwd_vol_{horizon}d"].notna()]
    return test, b2, n, data.iloc[:b2 - horizon]


def _dates(frame) -> list[str]:
    return [frame.index[0].strftime("%Y-%m-%d"), frame.index[-1].strftime("%Y-%m-%d")]


def risk_test(test, horizon: int) -> dict:
    y = test[f"fwd_vol_{horizon}d"].to_numpy()
    q_p, q_e = qlike(test["vol_30d"].to_numpy(), y), qlike(test["ewma_vol"].to_numpy(), y)
    ci = m.paired_bootstrap_ci(q_p, q_e, np.mean, block_size=horizon)
    return {"n": len(test), "n_effective": len(test) / horizon, "date_range": _dates(test),
            "qlike_ewma": float(q_e.mean()), "qlike_persistence": float(q_p.mean()),
            "paired_diff_persistence_minus_ewma": ci,
            "spearman_ewma": m.spearman(test["ewma_vol"].to_numpy(), y),
            "spearman_persistence": m.spearman(test["vol_30d"].to_numpy(), y),
            "not_worse": bool(ci is not None and ci["high"] >= 0),
            "rule": "D50: not worse = upper bound of the paired 95% CI (block = h) of QLIKE(persistence) - "
                    "QLIKE(EWMA) >= 0"}


def range_test(test, pre) -> dict:
    """vol_30d band at h = 30 on test; high-vol rows use the upper RISK_PERCENTILES threshold of pre-test rows."""
    vol, y = test["vol_30d"].to_numpy(), test[f"fwd_return_{RANGE_H}d"].to_numpy()
    lo, hi = Z["lo"] * vol * np.sqrt(RANGE_H), Z["hi"] * vol * np.sqrt(RANGE_H)
    threshold = float(np.percentile(pre["vol_30d"], config.RISK_PERCENTILES[1]))
    s = im.summary(lo, hi, y, vol > threshold)
    return {"date_range": _dates(test), "n_effective": len(test) / RANGE_H, "high_vol_threshold": threshold,
            **s, **im.passes(s)}


def confirmation_pass(asset: str) -> dict:
    wf = json.loads((ML_ROOT / "reports" / asset / "walkforward_range.json").read_text(encoding="utf-8"))
    s = wf["horizons"][f"h{RANGE_H}"]["summaries"]["confirmation_last_40pct"]["vol30_band"]
    return {"coverage": s["coverage"], "lower_tail_miss": s["lower_tail_miss"],
            "upper_tail_miss": s["upper_tail_miss"], **im.passes(s)}


def decide(risk: dict, ranges: dict) -> dict:
    """D50, applied mechanically. risk: {asset: {h: result}}; ranges: {asset: {"confirmation", "test"}}."""
    serve_ewma = all(risk[a][30]["not_worse"] for a in config.ASSETS)
    band = {a: bool(all(r[k]["coverage_in_bounds"] and r[k]["tails_within_max"] for k in ("confirmation", "test")))
            for a, r in ranges.items()}
    return {"risk": {"serve_ewma_for_all_assets": serve_ewma,
                     "not_worse_h30": {a: risk[a][30]["not_worse"] for a in config.ASSETS},
                     "otherwise": "persistence vol_30d stays (D27, D36)"},
            "range": {"serve_vol30_band_h30": band, "predicted_price": "null (D35)"},
            "price": {"serve": False, "reason": "0 of 60 approved (D35 stays)"},
            "direction": {"serve": False, "reason": "nothing passes; D33 stays; ETH logreg closed (D50)"}}


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    refuse_if_run()
    for asset in config.ASSETS:
        require_validated(asset)
    risk, ranges, meta = {a: {} for a in config.ASSETS}, {}, {}
    for asset in config.ASSETS:
        for h, assets in RISK_HORIZONS.items():
            test, b2, n, pre = sealed_rows(asset, h)
            meta[asset] = {"n_feature_rows": n, "b2_test_start_row": b2, "test_first_date": test.index[0].strftime("%Y-%m-%d")}
            if asset in assets:
                risk[asset][h] = risk_test(test, h)
            if h == RANGE_H:
                ranges[asset] = {"confirmation": confirmation_pass(asset), "test": range_test(test, pre)}
    decision = decide(risk, ranges)
    stamp = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git_metadata(),
             "decision_rule": "D50", "total_trials_phase_9": {**TOTAL_TRIALS, "total": sum(TOTAL_TRIALS.values())}}
    for asset in config.ASSETS:
        out = ML_ROOT / "reports" / asset / REPORT
        out.write_text(json.dumps(_clean({"asset": asset, **stamp, **meta[asset],
                                          "risk": {f"h{h}": r for h, r in risk[asset].items()},
                                          "range_h30": ranges[asset], "decision": decision}), indent=2),
                       encoding="utf-8")
        print(f"wrote {out}")
    summary = ML_ROOT / "reports" / SUMMARY
    summary.write_text(json.dumps(_clean({**stamp, "decision": decision}), indent=2), encoding="utf-8")
    print(f"wrote {summary}\n{json.dumps(decision, indent=1)}")


if __name__ == "__main__":
    main()
