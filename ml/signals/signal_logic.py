"""The ONE generate_signal() (docs/ARCHITECTURE.md, AGENTS rule 6). The API and the backtest both import it.

Serving rule (D33): no direction model is served, so the API gets signal UNCERTAIN and confidence null.
serve=True exists only for the backtest reference row (D34, evidence only): argmax of the direction
probabilities, UP -> BUY, DOWN -> SELL, FLAT -> HOLD, ties -> UNCERTAIN. Confidence is always null
(no measured confidence exists, D33). Never STRONG_* (D7). No price inputs.
"""

from collections.abc import Mapping

from ml import config
from ml.labels.labels import DIRECTION_CLASSES

CLASS_TO_SIGNAL = {"UP": "BUY", "DOWN": "SELL", "FLAT": "HOLD"}       # D34 reference rule
NOTE_NOT_SERVED = ("Direction is not served (D33): no demonstrated up/down skill; signal UNCERTAIN, "
                   "confidence null.")
NOTE_NO_PROBS = "No direction probabilities available; signal UNCERTAIN, confidence null (D33)."
NOTE_REFERENCE = ("Backtest reference row only (D34), never served: argmax of direction probabilities; "
                  "confidence null (D33).")
NOTE_TIE = "Backtest reference row only (D34): tied top probabilities; signal UNCERTAIN, confidence null (D33)."


def generate_signal(asset: str, direction_probs: Mapping[str, float] | None = None,
                    serve: bool | None = None) -> dict:
    """{"signal", "confidence", "note"} for one asset. direction_probs maps each DIRECTION_CLASSES class to P."""
    if serve is None:
        serve = config.DIRECTION_SERVED[asset]
    elif asset not in config.DIRECTION_SERVED:
        raise KeyError(asset)
    if not serve:
        return {"signal": "UNCERTAIN", "confidence": None, "note": NOTE_NOT_SERVED}
    if direction_probs is None:
        return {"signal": "UNCERTAIN", "confidence": None, "note": NOTE_NO_PROBS}
    if set(direction_probs) != set(DIRECTION_CLASSES):
        raise ValueError(f"direction_probs must have exactly the classes {DIRECTION_CLASSES}")
    top = max(direction_probs.values())
    winners = [c for c in DIRECTION_CLASSES if direction_probs[c] == top]
    if len(winners) != 1:
        return {"signal": "UNCERTAIN", "confidence": None, "note": NOTE_TIE}
    signal = CLASS_TO_SIGNAL[winners[0]]
    assert signal in config.SIGNALS
    return {"signal": signal, "confidence": None, "note": NOTE_REFERENCE}
