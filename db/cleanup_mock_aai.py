"""
db/cleanup_mock_aai.py

One-off: removes AAI scores that were cached from the old mock prediction fallback
(model_version "mock-v1"), so they stop showing up as real scores in Discover, Compare and the
dashboard. Re-running is harmless.

Run: python db/cleanup_mock_aai.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.mongo_connection import get_db


def main():
    result = get_db().aai_scores.delete_many({"model_version": "mock-v1"})
    print(f"[cleanup] removed {result.deleted_count} mock AAI score(s)")


if __name__ == "__main__":
    main()
