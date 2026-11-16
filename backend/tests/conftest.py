"""Run from backend/: python -m pytest tests -q   (puts backend/ and the repo root on sys.path)."""
import os
import sys

# Tests run without a real JWT_SECRET; dev/test mode allows the built-in one (shared/app_env.py).
os.environ.setdefault("APP_ENV", "test")

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import path_setup  # noqa: E402,F401  (adds the repo root)
