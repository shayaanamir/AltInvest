"""Run from sentiment_engine/: python -m pytest tests -q   (puts sentiment_engine/ on sys.path, like the backend does)."""
import os
import sys

ENGINE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)
