"""Tests for the day report builder."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from custom_components.qustodio.day_report import routine_windows

TZ = ZoneInfo("Australia/Sydney")


def _at(day: str, hhmm: str) -> datetime:
    """Local wall-clock time in Sydney."""
    return datetime.fromisoformat(f"{day}T{hhmm}").replace(tzinfo=TZ)


def _schedule(**overrides: Any) -> dict[str, Any]:
    base = {
        "weekdays": ["TU"],
        "start_time": "08:40:00",
        "duration_minutes": 395,
        "from_date": "2025-12-19",
        "to_date": None,
        "overrides": False,
        "enabled": True,
    }
    return base | overrides


class TestRoutineWindows:
    """Tests for routine_windows()."""

    def test_window_single_day(self) -> None:
        """A weekday schedule gives one window on matching days and none on others."""
        assert routine_windows([_schedule()], date(2026, 11, 10), TZ) == [
            (_at("2026-11-10", "08:40"), _at("2026-11-10", "15:15"))
        ]
        assert routine_windows([_schedule()], date(2026, 11, 11), TZ) == []

    def test_window_crossing_midnight(self) -> None:
        """A window running past midnight shows on both days, clipped to each."""
        night = _schedule(weekdays=["TU", "WE"], start_time="20:00:00", duration_minutes=720)
        assert routine_windows([night], date(2026, 11, 11), TZ) == [
            (_at("2026-11-11", "00:00"), _at("2026-11-11", "08:00")),
            (_at("2026-11-11", "20:00"), _at("2026-11-12", "00:00")),
        ]

    def test_override_only_on_its_date(self) -> None:
        """A one-off override applies only on its own date."""
        override = _schedule(
            start_time="17:36:00", duration_minutes=15, from_date="2026-11-10", to_date="2026-11-10", overrides=True
        )
        assert routine_windows([override], date(2026, 11, 10), TZ) == [
            (_at("2026-11-10", "17:36"), _at("2026-11-10", "17:51"))
        ]
        assert routine_windows([override], date(2026, 11, 17), TZ) == []

    def test_schedule_before_from_date_ignored(self) -> None:
        """A schedule doesn't apply before its from_date."""
        assert routine_windows([_schedule(from_date="2026-11-11")], date(2026, 11, 10), TZ) == []

    def test_disabled_schedule_ignored(self) -> None:
        """Disabled schedules give no windows."""
        assert routine_windows([_schedule(enabled=False)], date(2026, 11, 10), TZ) == []

    def test_dst_day_uses_local_times(self) -> None:
        """On the daylight-saving change day, the end is start + real elapsed time."""
        early = _schedule(weekdays=["SU"], start_time="01:00:00", duration_minutes=240)
        [(start, end)] = routine_windows([early], date(2026, 10, 4), TZ)
        assert start.isoformat() == "2026-10-04T01:00:00+10:00"
        assert end.isoformat() == "2026-10-04T06:00:00+11:00"
