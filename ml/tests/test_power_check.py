"""Tests for ml.evaluation.power_check. All inputs are small HAND-MADE numbers, NOT market data."""

import pytest

from ml.evaluation.power_check import POWER_80_FACTOR, half_width, pct_of


def test_half_width_of_known_ci():
    assert half_width({"low": -0.02, "high": 0.04}) == pytest.approx(0.03)     # (0.04 - -0.02) / 2
    assert half_width({"low": 0.1, "high": 0.1}) == 0.0
    assert half_width({"low": -0.180508, "high": 0.248162}) == pytest.approx(0.214335)


def test_percent_of_mae():
    assert pct_of(0.003, 0.15) == pytest.approx(2.0)                           # 0.003 / 0.15 = 2%
    assert pct_of(0.15, 0.15) == pytest.approx(100.0)
    assert pct_of(half_width({"low": -0.01, "high": 0.01}), 0.2) == pytest.approx(5.0)


def test_power_factor():
    assert POWER_80_FACTOR == pytest.approx(2.80 / 1.96)
