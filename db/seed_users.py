"""
db/seed_users.py

Seeds one demo user for local development. Only when APP_ENV=dev (or test): the demo password
is public, so an account with it must never exist on a shared or deployed database.

Usage:
    APP_ENV=dev python db/seed_users.py

Demo credentials (development only):
    email:    demo@altinvest.com
    password: Demo1234!
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BACKEND_DIR)

from db.mongo_connection import get_db
from shared.app_env import app_env, is_dev

DEMO_EMAIL = "demo@altinvest.com"
DEMO_PASSWORD = "Demo1234!"


def seed():
    if not is_dev():
        print(f"Skipped demo user: APP_ENV={app_env()!r}; it is only created when APP_ENV=dev.")
        return
    from auth.security import hash_password
    DEMO_USER = {"email": DEMO_EMAIL, "name": "Demo User", "password_hash": hash_password(DEMO_PASSWORD)}
    db = get_db()
    db.users.update_one(
        {"email": DEMO_USER["email"]},
        {"$set": DEMO_USER},
        upsert=True,
    )
    print(f"Seeded demo user: {DEMO_EMAIL} (development only)")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()