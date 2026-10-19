"""
backend/utils/http_errors.py

Errors that leave the API must not carry internals. Database exceptions can contain hostnames,
connection strings or query details, so the full exception goes to the server log and the
client gets a fixed, safe message.
"""
import logging

from fastapi import HTTPException

log = logging.getLogger("api")

DB_UNAVAILABLE_MESSAGE = "Unable to reach the database right now."


def db_unavailable(exc: Exception) -> HTTPException:
    """503 for a failed database call. Use as: raise db_unavailable(exc)."""
    log.error("Database unavailable: %s: %s", type(exc).__name__, exc)
    return HTTPException(status_code=503, detail=DB_UNAVAILABLE_MESSAGE)
