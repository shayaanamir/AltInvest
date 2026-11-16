"""
Account deletion (AUTH-09) must reach every collection that holds a user's rows (audit G-14).

No database here: the test reads the source. Every write call (insert/update/replace/bulk) whose
arguments mention "user_id", and every index keyed on user_id, names a collection that must be in
db.queries._USER_OWNED_COLLECTIONS (or be handled separately: users, user_sessions).
A write of a prebuilt dict (insert_one(doc)) hides its fields from the scan; the index check covers
those collections, since every user-owned collection is queried, and so indexed, by user_id.
"""
import os
import re
from types import SimpleNamespace

from bson import ObjectId

from db import queries
from db.indexes import INDEXES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCANNED = ("backend", "db")
HANDLED_SEPARATELY = {"users", "user_sessions"}

_WRITE_CALL = re.compile(
    r"""(?:\bdb|get_db\(\))\s*(?:\.\s*(\w+)|\[\s*["'](\w+)["']\s*\])\s*\.\s*"""
    r"""(insert_one|insert_many|update_one|update_many|replace_one|find_one_and_update|bulk_write)\s*\("""
)


def _call_args(src: str, open_paren: int) -> str:
    depth = 0
    for i in range(open_paren, len(src)):
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
            if depth == 0:
                return src[open_paren:i]
    return src[open_paren:]


def _source_files():
    for top in SCANNED:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, top)):
            dirnames[:] = [d for d in dirnames if d not in ("tests", "__pycache__", "seed_data")]
            for name in filenames:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def _collections_written_with_user_id() -> dict:
    found = {}
    for path in _source_files():
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for m in _WRITE_CALL.finditer(src):
            if "user_id" in _call_args(src, m.end() - 1):
                found.setdefault(m.group(1) or m.group(2), set()).add(os.path.relpath(path, ROOT))
    return found


def test_scanner_sees_known_writers():
    found = _collections_written_with_user_id()
    # Sanity check that the regex works: these are written with user_id today.
    assert {"alert_triggers", "portfolio_transactions", "alerts", "notifications"} <= set(found)


def test_every_user_id_collection_is_deleted_with_the_account():
    owned = set(queries._USER_OWNED_COLLECTIONS) | HANDLED_SEPARATELY
    missing = {c: sorted(files) for c, files in _collections_written_with_user_id().items() if c not in owned}
    assert not missing, f"user_id rows written to collections that account deletion skips: {missing}"


def test_every_user_id_index_is_deleted_with_the_account():
    owned = set(queries._USER_OWNED_COLLECTIONS) | HANDLED_SEPARATELY
    keyed = {c for c, specs in INDEXES.items() for keys, _ in specs if any(k == "user_id" for k, _ in keys)}
    assert keyed <= owned, f"collections indexed on user_id that account deletion skips: {keyed - owned}"


def test_delete_user_account_touches_every_listed_collection(monkeypatch):
    calls = []

    class _Coll:
        def __init__(self, name):
            self.name = name

        def delete_many(self, query):
            calls.append((self.name, query))
            return SimpleNamespace(deleted_count=1)

        def delete_one(self, query):
            calls.append((self.name, query))
            return SimpleNamespace(deleted_count=1)

    class _Db:
        def __getattr__(self, name):
            return _Coll(name)

        def __getitem__(self, name):
            return _Coll(name)

    monkeypatch.setattr(queries, "get_db", lambda: _Db())
    monkeypatch.setattr(queries, "_sessions", lambda: _Coll("user_sessions"))
    uid = ObjectId()
    deleted = queries.delete_user_account(uid)

    touched = [name for name, _ in calls]
    assert touched[0] == "user_sessions" and touched[-1] == "users"
    assert set(queries._USER_OWNED_COLLECTIONS) <= set(touched)
    assert {"portfolio_transactions", "alert_triggers"} <= set(deleted)
