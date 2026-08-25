"""
Adds the project root AND the sentiment_engine directory to sys.path.

- Project root  → allows `from shared.x import y`, `from aai_engine.x import y`
- sentiment_engine dir → allows the engine's own bare imports to resolve
  (e.g. `from aggregator.sentiment_aggregator import run_pipeline`)

Import this at the very top of main.py before any other local imports.
"""
import sys
import os

# Project root = one level above this file (backend/../)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Sentiment engine dir — needed so the engine's internal bare imports resolve
SENTIMENT_ENGINE_DIR = os.path.join(PROJECT_ROOT, "sentiment_engine")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if SENTIMENT_ENGINE_DIR not in sys.path:
    sys.path.insert(0, SENTIMENT_ENGINE_DIR)
