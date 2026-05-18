"""
Adds the project root to sys.path so that `shared` and `aai_engine`
can be imported from anywhere, regardless of which directory uvicorn
is launched from.

Import this at the very top of main.py before any other local imports.
"""
import sys
import os

# Project root = one level above this file (backend/../)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
