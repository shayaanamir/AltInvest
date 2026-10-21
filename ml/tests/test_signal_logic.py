"""Tests for ml.signal.signal_logic.generate_signal (Phase 5b, D7, D33, D34).

All probabilities below are small HAND-MADE numbers, NOT model output or market data.
"""

import inspect
import itertools
from pathlib import Path

import pytest

from ml import config
from ml.labels.labels import DIRECTION_CLASSES
from ml.signal import signal_logic
from ml.signal.signal_logic import generate_signal

PROBS = {"DOWN": 0.2, "FLAT": 0.3, "UP": 0.5}


def test_stdlib_signal_not_shadowed():
    import signal
    assert hasattr(signal, "SIGINT")
    assert "ml" not in Path(signal.__file__).parts                  # the stdlib module, not ml/signal
    assert Path(signal_logic.__file__).parent.name == "signal"


@pytest.mark.parametrize("asset", config.ASSETS)
def test_default_is_uncertain_with_null_confidence(asset):
    assert config.DIRECTION_SERVED[asset] is False                    # D33
    for probs in (None, PROBS):
        out = generate_signal(asset, probs)
        assert out["signal"] == "UNCERTAIN" and out["confidence"] is None
        assert "D33" in out["note"]


@pytest.mark.parametrize("winner,expected", [("UP", "BUY"), ("DOWN", "SELL"), ("FLAT", "HOLD")])
def test_argmax_mapping_when_serving(winner, expected):
    probs = {c: (0.6 if c == winner else 0.2) for c in DIRECTION_CLASSES}
    out = generate_signal("eth", probs, serve=True)
    assert out == {"signal": expected, "confidence": None, "note": signal_logic.NOTE_REFERENCE}


def test_ties_and_missing_probs_give_uncertain():
    tie = generate_signal("btc", {"DOWN": 0.4, "FLAT": 0.2, "UP": 0.4}, serve=True)
    assert tie["signal"] == "UNCERTAIN" and tie["confidence"] is None
    three_way = generate_signal("btc", {c: 1 / 3 for c in DIRECTION_CLASSES}, serve=True)
    assert three_way["signal"] == "UNCERTAIN"
    assert generate_signal("btc", None, serve=True)["signal"] == "UNCERTAIN"


def test_never_strong_and_only_declared_signals():
    grid = [0.0, 0.1, 1 / 3, 0.5, 0.9]
    seen = set()
    for d, f, u in itertools.product(grid, repeat=3):
        for serve in (None, True, False):
            out = generate_signal("sol", {"DOWN": d, "FLAT": f, "UP": u}, serve=serve)
            seen.add(out["signal"])
            assert out["confidence"] is None
    assert seen <= set(config.SIGNALS) and not any(s.startswith("STRONG") for s in seen)
    assert not any(s.startswith("STRONG") for s in config.SIGNALS)


def test_signature_has_no_price_input():
    params = list(inspect.signature(generate_signal).parameters)
    assert params == ["asset", "direction_probs", "serve"]
    assert not any("price" in p for p in params)


def test_bad_inputs_raise():
    with pytest.raises(KeyError):
        generate_signal("doge")
    with pytest.raises(KeyError):
        generate_signal("doge", PROBS, serve=True)
    with pytest.raises(ValueError):
        generate_signal("eth", {"UP": 0.7, "DOWN": 0.3}, serve=True)
