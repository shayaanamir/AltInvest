"""Unit tests for ml.data.validate and ml.data.fetch.closed_bars.

All fixtures below are small HAND-MADE numbers, NOT market data. No network calls.
"""

import numpy as np
import pandas as pd
import pytest

from ml.data import validate as v
from ml.data.fetch import closed_bars


def _bars(days, closes):
    """Hand-made daily bars (not market data). `days` are offsets from 2020-01-01."""
    ts = pd.to_datetime("2020-01-01", utc=True) + pd.to_timedelta(days, unit="D")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"asset": "test", "timestamp": ts, "open": c, "high": c + 1,
                         "low": c - 1, "close": c, "volume": 1.0})


def test_missing_days_listed():
    df = _bars([0, 1, 3, 6], [10, 11, 12, 13])
    assert v.missing_days(df["timestamp"]) == [
        "2020-01-03T00:00:00Z", "2020-01-05T00:00:00Z", "2020-01-06T00:00:00Z"]


def test_no_missing_days():
    df = _bars([0, 1, 2], [10, 11, 12])
    assert v.missing_days(df["timestamp"]) == []


def test_duplicates_found():
    df = _bars([0, 1, 1, 2], [10, 11, 11, 12])
    assert v.duplicate_timestamps(df["timestamp"]) == ["2020-01-02T00:00:00Z"]


def test_log_returns_skip_gaps():
    # day 2 is missing: the day1 -> day3 move must NOT become a return
    df = _bars([0, 1, 3, 4], [100, 110, 50, 55])
    r = v.daily_log_returns(df)
    assert r.tolist() == pytest.approx([np.log(110 / 100), np.log(55 / 50)])


def test_excess_kurtosis_matches_formula():
    r = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, -1.0, 0.0])
    n, m = len(r), r - r.mean()
    m2, m4 = (m ** 2).mean(), (m ** 4).mean()
    g2 = m4 / m2 ** 2 - 3
    expected = (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 + 6)
    assert v.excess_kurtosis(r) == pytest.approx(expected)
    assert v.excess_kurtosis(r) > 1          # spiky fixture -> heavy-tailed


def test_abs_autocorr_sign():
    clustered = pd.Series([0.1, -0.1, 0.1, 0.01, -0.01, 0.01, 0.1, -0.1, 0.1, 0.01, -0.01, 0.01])
    alternating = pd.Series([0.1, -0.01, 0.1, -0.01, 0.1, -0.01, 0.1, -0.01])
    assert v.abs_return_autocorr(clustered) > 0
    assert v.abs_return_autocorr(alternating) < 0


def test_non_positive_and_ohlc_checks():
    df = _bars([0, 1, 2], [10, 0, 12])
    assert v.non_positive_rows(df) == 1
    df.loc[2, "high"] = 5                    # high below close
    assert v.ohlc_inconsistent_rows(df) == 1


@pytest.mark.filterwarnings("ignore::RuntimeWarning")   # autocorr of 2 values is undefined (expected)
def test_validate_report_fields_and_checks():
    df = _bars([0, 1, 2, 4], [10, 11, 10, 12])
    rep = v.validate(df)
    assert rep["rows"] == 4
    assert rep["first_timestamp"] == "2020-01-01T00:00:00Z"
    assert rep["last_timestamp"] == "2020-01-05T00:00:00Z"
    assert rep["expected_days"] == 5
    assert rep["missing_days"] == ["2020-01-04T00:00:00Z"]
    assert rep["close_min"] == 10 and rep["close_max"] == 12
    assert rep["n_returns"] == 2
    # 2 returns: lag-1 autocorr is undefined -> null in the report, and the check fails
    assert rep["abs_return_lag1_autocorr"] is None
    assert rep["checks"]["abs_return_lag1_autocorr_gt_0"] is False
    assert set(rep["checks"]) == {"excess_kurtosis_gt_1", "abs_return_lag1_autocorr_gt_0",
                                  "no_non_positive_prices", "no_duplicates", "ohlc_consistent"}
    assert rep["passed"] == all(rep["checks"].values())


def test_closed_bars_drops_unclosed_bar():
    # hand-made kline rows (not market data): [open_time, o, h, l, c, v, close_time]
    day_ms = 86_400_000
    klines = [[0, "1", "2", "0.5", "1.5", "10", day_ms - 1],
              [day_ms, "1.5", "2", "1", "1.8", "12", 2 * day_ms - 1]]
    rows = closed_bars(klines, "btc", now_ms=day_ms + 5)   # second bar still open
    assert rows == [["btc", "1970-01-01T00:00:00Z", "1", "2", "0.5", "1.5", "10"]]
