"""
backend/utils/serialization.py

Small shared helper: Mongo docs often carry datetime objects that need to
become ISO strings before they cross the Pydantic/JSON boundary. Centralised
here since routes/portfolio.py, routes/watchlists.py, routes/alerts.py, and
routes/notifications.py all need the same conversion.
"""

_DATETIME_FIELDS = (
    "created_at", "added_at", "updated_at", "date_added",
    "last_triggered_at", "timestamp",
)


def serialize_dates(doc: dict) -> dict:
    out = dict(doc)
    for field in _DATETIME_FIELDS:
        v = out.get(field)
        if hasattr(v, "strftime"):
            out[field] = v.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out