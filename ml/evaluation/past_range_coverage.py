"""Full-history coverage of the past ranges (Phase 11, D87, D88). MONITORING ONLY: the method does not change
based on this report (no tuning of z, lag or the volatility measure).

    python -m ml.evaluation.past_range_coverage         -> ml/reports/past_range_coverage.json

For every asset in config.ASSETS: the share of days whose close was inside the 50% and 80% past ranges, over every
day that has a range (ml.serving.past_ranges.series, the same code the API serves), plus the share per calendar
year. Reads config.ML_RAW_DIR (the evaluation snapshot unless ML_RAW_DIR is set). Nominal: 0.50 and 0.80.
"""

import json
from datetime import datetime, timezone

from ml import config
from ml.data.loader import load_raw
from ml.data.validate import ML_ROOT
from ml.gitinfo import git_metadata
from ml.serving import past_ranges as pr

OUT = ML_ROOT / "reports" / "past_range_coverage.json"


def asset_report(asset: str) -> dict:
    pts = pr.series(load_raw(asset))
    years = sorted({p["date"][:4] for p in pts})
    return {
        "first_date": pts[0]["date"] if pts else None,
        "last_date": pts[-1]["date"] if pts else None,
        "full_history": pr.coverage(pts),
        "by_year": {y: pr.coverage(p for p in pts if p["date"].startswith(y)) for y in years},
    }


def build() -> dict:
    return {
        "what": "Share of days the close was inside the 50% / 80% past range (the cone drawn 30 days earlier)",
        "monitoring_only": True,
        "nominal": {"share_50": 0.5, "share_80": 0.8},
        "lag_days": config.PAST_RANGE_LAG_DAYS,
        "volatility_measure": config.RISK_VOL_COLUMN,
        "raw_dir": str(config.ML_RAW_DIR),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **git_metadata(),
        "assets": {a: asset_report(a) for a in config.ASSETS},
    }


def main() -> None:
    rep = build()
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    for a, r in rep["assets"].items():
        c = r["full_history"]
        print(f"{a}: {r['first_date']} to {r['last_date']}, {c['days']} days, "
              f"inside 50%: {c['share_50']:.3f}, inside 80%: {c['share_80']:.3f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
