"""Power check of the walk-forward confirmation protocol (D25, D28, D29). No models are run.

    python -m ml.evaluation.power_check --asset btc

Reads the paired 95% CIs already written by run_walkforward_price and run_walkforward_risk (computed with
metrics.paired_bootstrap_ci on the last-40% confirmation set) and writes ml/reports/{asset}/power_check.json.
The CI half-width approximates the smallest difference the protocol can detect. A true difference equal
to the half-width is detected only about half the time; about 80% power needs roughly 1.43x the half-width
((1.96 + 0.84) / 1.96, normal approximation).
"""

import argparse
import json
from datetime import datetime, timezone

from ml import config
from ml.data.snapshot_guard import require_snapshot
from ml.data.validate import ML_ROOT
from ml.evaluation.run_baselines import _clean
from ml.gitinfo import git_metadata

LABEL = "smallest difference the protocol can reliably detect (approximate)"
POWER_80_FACTOR = (1.96 + 0.84) / 1.96


def half_width(ci: dict) -> float:
    """Half the width of a CI: (high - low) / 2."""
    return (ci["high"] - ci["low"]) / 2


def pct_of(value: float, base: float) -> float:
    """value as a percent of base."""
    return 100 * value / base


def _source(path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    md = report["metadata"]
    return report, {"file": path.relative_to(ML_ROOT.parent).as_posix(), "git_commit": md["git_commit"],
                    "git_dirty": md["git_dirty"], "generated_at": md["generated_at"]}


def run(asset: str) -> dict:
    out_dir = ML_ROOT / "reports" / asset
    price, price_src = _source(out_dir / "walkforward_price.json")
    risk, risk_src = _source(out_dir / "walkforward_risk.json")

    pc = price["confirmation_last_40pct"]
    p_ci = pc["paired_diff_mae_last_value_minus_top"]
    p_hw = half_width(p_ci)
    rc = risk["confirmation_last_40pct"]
    r_ci = rc["paired_diff_spearman_top_minus_persistence"]
    r_hw = half_width(r_ci)

    return _clean({
        "label": LABEL,
        "price": {
            "n_effective": pc["n_effective"], "n_pooled": pc["n_pooled"], "top_config": pc["top_config"],
            "paired_ci95": {"metric": "MAE(last-value) - MAE(top) of fwd_return_30d", **p_ci},
            "ci_half_width": p_hw,
            "mae_return_last_value": pc["mae_return_last_value"],
            "half_width_pct_of_last_value_mae": pct_of(p_hw, pc["mae_return_last_value"]),
            "half_width_x_1.43_pct_of_last_value_mae": pct_of(p_hw * POWER_80_FACTOR, pc["mae_return_last_value"]),
        },
        "risk": {
            "n_effective": rc["n_effective"], "n_pooled": rc["n_pooled"], "top_config": rc["top_config"],
            "paired_ci95": {"metric": "Spearman(top) - Spearman(persistence)", **r_ci},
            "ci_half_width_spearman": r_hw,
            "half_width_x_1.43_spearman": r_hw * POWER_80_FACTOR,
        },
        "note": ("Approximate. A true difference equal to the half-width is detected about 50% of the time; "
                 "about 80% power needs roughly 1.43x the half-width (normal approximation). A negative verdict "
                 "means 'no demonstrated gain', not 'no skill' (D29)."),
        "metadata": {"asset": asset,
                     "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     **git_metadata(), "sources": [price_src, risk_src]},
    })


def main() -> None:
    require_snapshot()                                  # D40: evaluation snapshot only
    parser = argparse.ArgumentParser(description="Power check of the walk-forward confirmation protocol")
    parser.add_argument("--asset", required=True, choices=config.ASSETS)
    asset = parser.parse_args().asset
    report = run(asset)
    out = ML_ROOT / "reports" / asset / "power_check.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
