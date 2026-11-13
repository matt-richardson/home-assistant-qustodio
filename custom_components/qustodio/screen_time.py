"""Screen time counting: split a day's usage into total and counted-toward-the-limit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScreenTimeSplit:
    """A day's screen time, in minutes.

    Attributes:
        total_minutes: All screen time, including routines that don't count.
        counted_minutes: Screen time that counts toward the daily limit.
    """

    total_minutes: float
    counted_minutes: float


def routine_counting_map(routines: list[dict[str, Any]]) -> dict[str, bool]:
    """Map each routine uid to whether its time counts toward the daily limit.

    Args:
        routines: Routine dicts from the routines endpoint.

    Returns:
        uid -> ``policy.counts_towards_daily_time_quota``, defaulting to True when
        the policy or the flag is missing.
    """
    return {
        routine["uid"]: bool((routine.get("policy") or {}).get("counts_towards_daily_time_quota", True))
        for routine in routines
        if "uid" in routine
    }


def _routine_entries(hourly: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten every hour's routine time entries into one list."""
    return [entry for hour in hourly for entry in hour.get("routines_screen_time") or []]


def has_routine_time(hourly: list[dict[str, Any]]) -> bool:
    """Return whether any hour has time recorded under a routine.

    Args:
        hourly: Hourly entries from the summary_hourly endpoint.

    Returns:
        True if any routine entry has more than zero seconds.
    """
    return any(entry.get("seconds", 0) > 0 for entry in _routine_entries(hourly))


def split_screen_time(hourly: list[dict[str, Any]], counts: dict[str, bool]) -> ScreenTimeSplit:
    """Split a day's hourly screen time into total and counted minutes.

    Counted time is the total minus time in routines that don't count toward the
    limit. Routines missing from ``counts`` are treated as counting.

    Args:
        hourly: Hourly entries from the summary_hourly endpoint.
        counts: Routine uid -> whether its time counts (see routine_counting_map).

    Returns:
        The total and counted minutes, each rounded to one decimal place.
    """
    total_seconds = sum(hour.get("screen_time_seconds", 0) for hour in hourly)
    non_counting_seconds = sum(
        entry.get("seconds", 0) for entry in _routine_entries(hourly) if not counts.get(entry.get("uid", ""), True)
    )
    return ScreenTimeSplit(
        total_minutes=round(total_seconds / 60, 1),
        counted_minutes=round((total_seconds - non_counting_seconds) / 60, 1),
    )


WEEKEND_DAY_CODES = {"sat", "sun"}


def daily_quota(time_restrictions: dict[str, Any], day_code: str) -> int | None:
    """Return the daily screen time quota for a weekday, or None when there's no limit.

    A quota applies when one is set for that weekday and the weekday (Mon-Fri) or
    weekend (Sat-Sun) quota is switched on (``is_weekdays_quota`` /
    ``is_weekend_quota``); missing switches count as on. A quota of 0 means no
    screen time is allowed, which is different from no limit.

    Args:
        time_restrictions: The ``time_restrictions`` section of the profile rules.
        day_code: The rules' weekday code (``mon`` ... ``sun``; Thursday is ``thr``).

    Returns:
        The quota in minutes, or None for no limit.
    """
    switch = "is_weekend_quota" if day_code in WEEKEND_DAY_CODES else "is_weekdays_quota"
    if not time_restrictions.get(switch, True):
        return None
    return (time_restrictions.get("quotas") or {}).get(day_code)
