"""Tests for ml.signals.signal_logic.generate_signal (Phase 5b, D7, D33, D34).

All probabilities below are small HAND-MADE numbers, NOT model output or market data.
"""

import inspect
import itertools
import subprocess
import sys
from pathlib import Path

import pytest

from ml import config
from ml.labels.labels import DIRECTION_CLASSES
from ml.signals import signal_logic
from ml.signals.signal_logic import generate_signal

PROBS = {"DOWN": 0.2, "FLAT": 0.3, "UP": 0.5}


def test_stdlib_signal_not_shadowed():
    import signal
    assert hasattr(signal, "SIGINT")
    assert "ml" not in Path(signal.__file__).parts                  # the stdlib module, not ml/signals
    assert Path(signal_logic.__file__).parent.name == "signals"


ML_DIR = Path(__file__).resolve().parents[1]


def test_nothing_in_ml_shadows_a_stdlib_module():
    """Audit N-10: running from inside ml/ puts ml/ first on sys.path, so a package there named like a stdlib module
    (ml/signal did) replaced it and pytest died with "cannot import name 'Signals'"."""
    names = {p.stem if p.is_file() else p.name for p in ML_DIR.iterdir()
             if (p.is_dir() and (p / "__init__.py").exists()) or p.suffix == ".py"}
    assert not names & set(sys.stdlib_module_names)


def test_stdlib_signal_resolves_from_inside_ml():
    out = subprocess.run([sys.executable, "-c", "import signal; print(signal.Signals.SIGINT.name, signal.__file__)"],
                         cwd=ML_DIR, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("SIGINT ") and str(ML_DIR) not in out.stdout


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
        generate_signal("dai")
    with pytest.raises(KeyError):
        generate_signal("dai", PROBS, serve=True)
    with pytest.raises(ValueError):
        generate_signal("eth", {"UP": 0.7, "DOWN": 0.3}, serve=True)
