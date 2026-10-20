"""
backend/utils/http_errors.py

Errors that leave the API must not carry internals. Database exceptions can contain hostnames,
connection strings or query details, so the full exception goes to the server log and the
client gets a fixed, safe message.
"""
import logging
import re

from fastapi import HTTPException

log = logging.getLogger("api")

DB_UNAVAILABLE_MESSAGE = "Unable to reach the database right now."

_CREDENTIALS = re.compile(r"(//)[^/@\s:]+:[^/@\s]+@")


def redact(exc: Exception) -> str:
    """Exception text for the server log with any user:password@ in a URI masked."""
    return _CREDENTIALS.sub(r"\1***:***@", str(exc))


def db_unavailable(exc: Exception) -> HTTPException:
    """503 for a failed database call. Use as: raise db_unavailable(exc)."""
    log.error("Database unavailable: %s: %s", type(exc).__name__, redact(exc))
    return HTTPException(status_code=503, detail=DB_UNAVAILABLE_MESSAGE)


ENGINE_UNAVAILABLE_MESSAGE = "Sentiment analysis isn't available right now."
INTERNAL_ERROR_MESSAGE = "Something went wrong on our side. Please try again."


class EngineUnavailable(RuntimeError):
    """The sentiment engine can't be imported/used. main.py turns this into a 503."""


def require_object_id(value: str, what: str) -> str:
    """
    422 for a path id that isn't a valid ObjectId, checked before any database call, so that a
    database failure can never be reported as "invalid id". Returns the id unchanged.
    """
    from bson import ObjectId
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=422, detail=f"Invalid {what} id.")
    return value
