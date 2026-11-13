"""Build a child's day report (screen time by hour and routine, apps, websites) from Qustodio data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .const import RULES_WEEKDAY_CODES, get_platform_name
from .screen_time import daily_quota, routine_counting_map, split_screen_time

WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
USAGE_TYPE_APP = 301
USAGE_TYPE_WEBSITE = 101
REMOVED_ROUTINE_NAME = "Removed routine"


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


@dataclass(frozen=True)
class DayContext:
    """Which child and which local day a report is for.

    Attributes:
        profile_id: Numeric profile id, as a string.
        profile_name: Profile display name.
        day: The local day the report covers.
        today: Today's local date (extra time is only reported for today).
        tz: The local time zone.
    """

    profile_id: str
    profile_name: str
    day: date
    today: date
    tz: ZoneInfo


@dataclass(frozen=True)
class DayInputs:
    """Raw Qustodio responses needed to build one day's report.

    Attributes:
        hourly: Entries from the summary_hourly endpoint for the day.
        routines: The profile's routines (including disabled ones).
        schedules: Routine uid -> that routine's schedules.
        rules: The profile's rules document (for the daily quota).
        usage: The domains-and-apps response for the day, or None if unavailable.
        extra_time_minutes: Extra time granted today (only meaningful for today).
    """

    hourly: list[dict[str, Any]]
    routines: list[dict[str, Any]]
    schedules: dict[str, list[dict[str, Any]]]
    rules: dict[str, Any]
    usage: dict[str, Any] | None
    extra_time_minutes: int | None


def _minutes(seconds: float) -> float:
    return round(seconds / 60, 1)


def _routine_seconds(hourly: list[dict[str, Any]]) -> dict[str, float]:
    """Total seconds per routine uid across the day."""
    totals: dict[str, float] = {}
    for hour in hourly:
        for entry in hour.get("routines_screen_time") or []:
            totals[entry["uid"]] = totals.get(entry["uid"], 0) + (entry.get("seconds") or 0)
    return totals


def _hours(hourly: list[dict[str, Any]], tz: ZoneInfo) -> list[dict[str, Any]]:
    """Non-empty hours in local time, in real time order, split into default and per-routine minutes."""
    hours = []
    for hour in hourly:
        if not hour.get("screen_time_seconds"):
            continue
        start = datetime.fromisoformat(hour["datetime"].replace("Z", "+00:00"))
        hours.append(
            (
                start,
                {
                    "start": start.astimezone(tz).isoformat(),
                    "default_minutes": _minutes(hour.get("default_rules_screen_time") or 0),
                    "routines": {
                        entry["uid"]: _minutes(entry.get("seconds") or 0)
                        for entry in hour.get("routines_screen_time") or []
                        if entry.get("seconds")
                    },
                },
            )
        )
    # Sort by the instant, not the local label: on the day clocks go back the same label repeats
    return [item for _, item in sorted(hours, key=lambda pair: pair[0])]


def _routines(inputs: DayInputs, day: date, tz: ZoneInfo) -> list[dict[str, Any]]:
    """Every routine with minutes or a shaded window that day, largest first."""
    seconds = _routine_seconds(inputs.hourly)
    counts = routine_counting_map(inputs.routines)
    known = {routine["uid"] for routine in inputs.routines if "uid" in routine}
    result = []
    for routine in inputs.routines:
        if (uid := routine.get("uid")) is None:
            continue
        active = routine.get("enabled", True) and not routine.get("paused", False)
        windows = routine_windows(inputs.schedules.get(uid, []), day, tz) if active else []
        if not windows and uid not in seconds:
            continue
        result.append(
            {
                "uid": uid,
                "name": routine.get("name", ""),
                "counts": counts.get(uid, True),
                "enabled": bool(routine.get("enabled", True)),
                "paused": bool(routine.get("paused", False)),
                "removed": False,
                "minutes": _minutes(seconds.get(uid, 0)),
                "windows": [{"start": start.isoformat(), "end": end.isoformat()} for start, end in windows],
            }
        )
    for uid in seconds.keys() - known:
        result.append(
            {
                "uid": uid,
                "name": REMOVED_ROUTINE_NAME,
                "counts": True,
                "enabled": False,
                "paused": False,
                "removed": True,
                "minutes": _minutes(seconds[uid]),
                "windows": [],
            }
        )
    return sorted(result, key=lambda item: item["minutes"], reverse=True)


def _usage_items(usage: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the domains-and-apps items into apps and websites, largest first, dropping zero minutes."""
    apps, websites = [], []
    for item in (usage or {}).get("items", []):
        minutes = float(item.get("minutes") or 0)
        if minutes <= 0:
            continue
        if item.get("type") == USAGE_TYPE_APP:
            apps.append(
                {
                    "name": item.get("app_name", "Unknown"),
                    "package": item.get("exe", ""),
                    "platform": get_platform_name(item.get("platform", -1)),
                    "minutes": minutes,
                    "thumbnail": item.get("thumbnail"),
                }
            )
        elif item.get("type") == USAGE_TYPE_WEBSITE:
            websites.append(
                {
                    "host": item.get("host", ""),
                    "minutes": minutes,
                    "pages": item.get("pages", 0),
                    "blocked_pages": item.get("blocked_pages", 0),
                }
            )
    return (
        sorted(apps, key=lambda item: item["minutes"], reverse=True),
        sorted(websites, key=lambda item: item["minutes"], reverse=True),
    )


def build_day_report(ctx: DayContext, inputs: DayInputs, partial: list[str]) -> dict[str, Any]:
    """Build a child's report for one local day.

    Args:
        ctx: Which profile and day, today's date and the local time zone.
        inputs: The raw Qustodio responses for the day.
        partial: Names of parts that couldn't be fetched (e.g. ["apps"]).

    Returns:
        The day report; see the PR 3 plan for its shape.
    """
    split = split_screen_time(inputs.hourly, routine_counting_map(inputs.routines))
    apps, websites = _usage_items(inputs.usage)
    report: dict[str, Any] = {
        "profile_id": ctx.profile_id,
        "profile_name": ctx.profile_name,
        "date": ctx.day.isoformat(),
        "is_today": ctx.day == ctx.today,
        "quota_minutes": daily_quota(
            inputs.rules.get("time_restrictions") or {}, RULES_WEEKDAY_CODES[ctx.day.weekday()]
        ),
        "extra_time_minutes": inputs.extra_time_minutes if ctx.day == ctx.today else None,
        "total_minutes": split.total_minutes,
        "counted_minutes": split.counted_minutes,
        "hours": _hours(inputs.hourly, ctx.tz),
        "routines": _routines(inputs, ctx.day, ctx.tz),
        # Every known routine, so the card can give each a colour that doesn't change from day to day
        "all_routines": [
            {"uid": routine["uid"], "name": routine.get("name", "")} for routine in inputs.routines if "uid" in routine
        ],
        "apps": apps,
        "websites": websites,
    }
    if partial:
        report["partial"] = partial
    return report
