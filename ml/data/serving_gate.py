"""The serving gate (D40): serve an asset only if its validation report passed AND matches the CSV served.

Match = same row count and same last timestamp. A missing or unreadable CSV or report, a report that did not
pass, or a mismatch raises NotServable, which the API maps to 503. Paths come from config.ML_RAW_DIR and
config.ML_VALIDATION_DIR through the loader and validate.report_path (one source, AGENTS rule 6).
"""

import json

import pandas as pd

from ml.data.loader import load_raw, raw_csv_path
from ml.data.validate import repo_relative, report_path


class NotServable(RuntimeError):
    """An asset's data may not be served (D40, AGENTS rule 4). The API returns 503."""


def _report(asset: str) -> dict:
    path = report_path(asset)
    if not path.exists():
        raise NotServable(f"{asset}: validation report {repo_relative(path)} is missing")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise NotServable(f"{asset}: validation report {repo_relative(path)} is unreadable ({e})") from None
    if report.get("passed") is not True:
        raise NotServable(f"{asset}: validation report {repo_relative(path)} did not pass")
    return report


def servable_raw(asset: str) -> pd.DataFrame:
    """The raw bars to serve for `asset` (loader output), after the D40 checks; NotServable otherwise."""
    csv = raw_csv_path(asset)
    if not csv.exists():
        raise NotServable(f"{asset}: raw CSV {repo_relative(csv)} is missing")
    report = _report(asset)
    try:
        df = load_raw(asset)
        last = df["timestamp"].max() if len(df) else None
        expected_last = pd.Timestamp(report.get("last_timestamp"))
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise NotServable(f"{asset}: raw CSV {repo_relative(csv)} or its report is unreadable ({e})") from None
    if len(df) != report.get("rows"):
        raise NotServable(f"{asset}: CSV has {len(df)} rows but its validation report has {report.get('rows')}")
    if last != expected_last:
        raise NotServable(f"{asset}: CSV ends {last} but its validation report ends {expected_last}")
    return df
