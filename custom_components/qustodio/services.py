"""Services for the Qustodio integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.exceptions import ServiceValidationError

_LOGGER = logging.getLogger(__name__)

# Qustodio weekday codes indexed by datetime.weekday() (Mon=0 .. Sun=6)
_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _format_dt(value: datetime) -> str:
    """Format a datetime as Qustodio local wall-clock (YYYYMMDDTHHMMSS)."""
    return value.strftime("%Y%m%dT%H%M%S")


def build_extra_time_rrule(now: datetime) -> str:
    """Build the rrule for an extra-time grant (amount lives in `duration`).

    Args:
        now: The current local datetime used as DTSTART.

    Returns:
        An rrule string with DTSTART and a single-occurrence FREQ=DAILY rule.

    """
    return f"DTSTART:{_format_dt(now)}\nFREQ=DAILY;COUNT=1"


def build_pause_rrule(now: datetime, minutes: int) -> str:
    """Build the rrule for an internet pause ending `minutes` from now.

    Args:
        now: The current local datetime used as DTSTART.
        minutes: How many minutes the pause should last; sets UNTIL.

    Returns:
        An rrule string with DTSTART and RRULE including UNTIL timestamp.

    """
    until = now + timedelta(minutes=minutes)
    return f"DTSTART:{_format_dt(now)}\nRRULE:FREQ=DAILY;COUNT=1;UNTIL={_format_dt(until)}"


def build_routine_override_payload(now: datetime, duration_minutes: int) -> dict[str, Any]:
    """Build the schedule-override payload that activates a routine now.

    Args:
        now: The current local datetime; determines weekday and start time.
        duration_minutes: How long the override should be active.

    Returns:
        A dict ready to POST as the routine override body.

    """
    today = now.date().isoformat()
    return {
        "overrides": True,
        "weekdays": [_WEEKDAY_CODES[now.weekday()]],
        "start_time": now.strftime("%H:%M"),
        "duration_minutes": duration_minutes,
        "from_date": today,
        "to_date": today,
    }


def resolve_routine_uid(routines: list[dict[str, Any]], name: str) -> str:
    """Resolve a routine name to its uid, raising if not found.

    Args:
        routines: List of routine dicts, each with at least 'uid' and 'name'.
        name: The human-readable routine name to look up.

    Returns:
        The uid string for the matched routine.

    Raises:
        ServiceValidationError: When no routine with the given name exists.

    """
    for routine in routines:
        if routine.get("name") == name:
            return routine["uid"]
    available = ", ".join(sorted(r.get("name", "?") for r in routines)) or "(none)"
    raise ServiceValidationError(f"Routine '{name}' not found. Available routines: {available}")
