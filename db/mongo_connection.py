"""
db/mongo_connection.py

The one MongoDB client the backend, the schedulers and the db/ scripts share.

- Settings come from the environment. The repo-root `.env` is loaded as a fallback for host-side
  scripts; it never overrides a variable that is already set (docker-compose sets them).
- The client is timezone-aware: every datetime read back is UTC-aware, so it can be compared with
  datetime.now(timezone.utc). (A naive client returned naive datetimes, and freshness checks that
  required tzinfo silently never matched; audit G-29.)
- Timeouts are bounded, so a request or a scheduler tick fails within seconds when the database is
  down, instead of hanging on pymongo's 30-second server-selection default (audit G-26).
"""
import os

from dotenv import load_dotenv
from pymongo import MongoClient

_ROOT_ENV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(_ROOT_ENV, override=False)

# Milliseconds. Server selection covers "is any server reachable"; socket covers one slow operation.
SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "3000"))
CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "3000"))
SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "20000"))

_client = None


class MongoConfigError(RuntimeError):
    """MONGO_URI or MONGO_DB_NAME is missing."""


def client_options() -> dict:
    return {
        "tz_aware": True,
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
        "connectTimeoutMS": CONNECT_TIMEOUT_MS,
        "socketTimeoutMS": SOCKET_TIMEOUT_MS,
    }


def db_name() -> str:
    """The application database. MONGO_DB is accepted as an older alias (the sentiment engine's name)."""
    name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGO_DB")
    if not name:
        raise MongoConfigError("MONGO_DB_NAME is not set.")
    return name


def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI")
        if not uri:
            raise MongoConfigError("MONGO_URI is not set.")
        _client = MongoClient(uri, **client_options())
    return _client


def get_db():
    return get_client()[db_name()]


def ping(timeout_ms: int = 2000) -> None:
    """Raises if the database doesn't answer a ping within `timeout_ms`."""
    get_client().admin.command("ping", maxTimeMS=timeout_ms)
