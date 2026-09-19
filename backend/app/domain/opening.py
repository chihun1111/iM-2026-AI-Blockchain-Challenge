from __future__ import annotations

from datetime import datetime


def time_bucket(visit_at: datetime) -> str | None:
    hour = visit_at.hour
    if 11 <= hour < 14:
        return "lunch"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "dinner"
    return None


def day_group(visit_at: datetime) -> str:
    return "weekday" if visit_at.weekday() < 5 else "weekend"


def opening_status(place: dict, visit_at: datetime) -> str:
    weekday = visit_at.weekday()
    for exception in place.get("opening_exceptions", []):
        if exception.get("date") == visit_at.date().isoformat():
            if exception.get("closed"):
                return "closed"
            intervals = exception.get("intervals", [])
            return "open" if _within(intervals, visit_at.strftime("%H:%M")) else "closed"
    entries = [x for x in place.get("opening_weekly", []) if x.get("weekday") == weekday]
    if not entries:
        return "unknown"
    return "open" if _within(entries[0].get("intervals", []), visit_at.strftime("%H:%M")) else "closed"


def _within(intervals: list, value: str) -> bool:
    return any(start <= value < end for start, end in intervals)
