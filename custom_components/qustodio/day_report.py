"""Build a child's day report (screen time by hour and routine, apps, websites) from Qustodio data."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _schedule_applies(schedule: dict[str, Any], start_day: date) -> bool:
    """Return whether a routine schedule starts a window on ``start_day``."""
    if not schedule.get("enabled", True):
        return False
    if WEEKDAY_CODES[start_day.weekday()] not in schedule.get("weekdays", []):
        return False
    from_date = schedule.get("from_date")
    to_date = schedule.get("to_date")
    if from_date and start_day < date.fromisoformat(from_date):
        return False
    return not (to_date and start_day > date.fromisoformat(to_date))


def _window_for(schedule: dict[str, Any], start_day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Return the window a schedule starts on ``start_day``, using real elapsed time for its length."""
    start = datetime.combine(start_day, time.fromisoformat(schedule["start_time"]), tzinfo=tz)
    end = (start.astimezone(UTC) + timedelta(minutes=schedule.get("duration_minutes", 0))).astimezone(tz)
    return start, end


def routine_windows(schedules: list[dict[str, Any]], day: date, tz: ZoneInfo) -> list[tuple[datetime, datetime]]:
    """Return a routine's windows on a local day, clipped to that day.

    Includes windows starting that day and windows from the previous day that run
    past midnight into it.

    Args:
        schedules: The routine's schedules from the routine schedules endpoint.
        day: The local day.
        tz: The time zone the day is in.

    Returns:
        Sorted (start, end) pairs, tz-aware in ``tz``, within [day 00:00, next day 00:00).
    """
    day_start = datetime.combine(day, time.min, tzinfo=tz)
    day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    windows = []
    for schedule in schedules:
        for start_day in (day - timedelta(days=1), day):
            if not _schedule_applies(schedule, start_day):
                continue
            start, end = _window_for(schedule, start_day, tz)
            if end > day_start and start < day_end:
                windows.append((max(start, day_start), min(end, day_end)))
    return sorted(windows)
