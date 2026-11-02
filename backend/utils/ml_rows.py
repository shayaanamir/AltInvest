"""
Shared handling of the rows the ML pull stores (`predictions`, `risk_scores`).

Staleness (ml/docs/PLAN_NEXT.md C3): when the newest stored row is more than 36 h old, the
backend appends "data stale" to `note`. ML adds its own note when ITS data is over 48 h old
(measured from the last bar); this one measures how old the backend's copy is. Both are kept.
"""
from datetime import datetime, timezone

STALE_AFTER_HOURS = 36


def as_utc(ts) -> datetime | None:
    """Mongo returns naive UTC datetimes (the client is not tz_aware)."""
    if not isinstance(ts, datetime):
        return None
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)


def iso(ts) -> str:
    dt = as_utc(ts)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else (ts or "")


def with_stale_note(note: str | None, ts, now: datetime | None = None) -> str | None:
    """`note`, plus a backend stale note when the row's timestamp is more than 36 h old."""
    dt = as_utc(ts)
    if dt is None:
        return note
    age_h = ((now or datetime.now(timezone.utc)) - dt).total_seconds() / 3600
    if age_h <= STALE_AFTER_HOURS:
        return note
    stale = (f"data stale: the newest stored row is {age_h:.0f} h old "
             f"(last pull {dt.strftime('%Y-%m-%dT%H:%M:%SZ')}, backend limit {STALE_AFTER_HOURS} h).")
    return f"{note} {stale}" if note else stale
