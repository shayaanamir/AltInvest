"""
start.py — Start the backend with the correct working directory.

Usage (from project root OR from backend/ directory):
    python backend/start.py
    python start.py          (if CWD is already backend/)

This avoids the uvicorn --reload StatReload child-process CWD bug on Windows.
Use --no-reload for production, --reload for development if needed.
"""

import os
import sys

# Ensure CWD is always the backend directory, regardless of where this is invoked from
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND_DIR)

# Also make sure backend/ is on sys.path so `import main` resolves
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[BACKEND_DIR],   # tells StatReload where to watch
        app_dir=BACKEND_DIR,         # sets CWD for the worker process
    )
