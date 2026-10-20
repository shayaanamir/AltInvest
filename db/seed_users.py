"""
db/seed_users.py

Seeds one demo user so AUTH-01 (Login) can be tested end-to-end before
AUTH-02 (Signup) exists.

Usage:
    python db/seed_users.py

Demo credentials:
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
from auth.security import hash_password

DEMO_USER = {
    "email": "demo@altinvest.com",
    "name": "Demo User",
    "password_hash": hash_password("Demo1234!"),
}


def seed():
    db = get_db()
    db.users.update_one(
        {"email": DEMO_USER["email"]},
        {"$set": DEMO_USER},
        upsert=True,
    )
    print(f"Seeded demo user: {DEMO_USER['email']} / Demo1234!")


if __name__ == "__main__":
    seed()