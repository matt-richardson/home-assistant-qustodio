"""Tests for the day report builder."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from custom_components.qustodio.day_report import DayContext, DayInputs, build_day_report, routine_windows

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


def _hour(utc: str, default: int, **routines: int) -> dict[str, Any]:
    return {
        "datetime": utc,
        "default_rules_screen_time": default,
        "routines_screen_time": [{"uid": uid, "seconds": sec} for uid, sec in routines.items()],
        "screen_time_seconds": default + sum(routines.values()),
    }


def _routine(uid: str, name: str, counts: bool, *, enabled: bool = True, paused: bool = False) -> dict[str, Any]:
    return {
        "uid": uid,
        "name": name,
        "enabled": enabled,
        "paused": paused,
        "policy": {"counts_towards_daily_time_quota": counts},
    }


def _inputs(**overrides: Any) -> DayInputs:
    """Tue 2026-11-10 as seen live: default 65.5, School 31.2, Homework 13.5, After school 48.0 minutes."""
    base: dict[str, Any] = {
        "hourly": [
            _hour("2026-11-09T21:00:00Z", 1200),
            _hour("2026-11-10T03:00:00Z", 0, school=1020),
            _hour("2026-11-10T04:00:00Z", 1500, school=852),
            _hour("2026-11-10T05:00:00Z", 0, homework=810, after=1500),
            _hour("2026-11-10T06:00:00Z", 1230, after=1380),
            _hour("2026-11-10T07:00:00Z", 0),
        ],
        "routines": [
            _routine("school", "Term Time - School", False),
            _routine("homework", "Homework", False),
            _routine("after", "Term Time - After school", True),
            _routine("night", "Night", False),
            _routine("holidays", "Holidays", True, paused=True),
        ],
        "schedules": {
            "school": [_schedule()],
            "night": [_schedule(weekdays=["MO", "TU"], start_time="20:00:00", duration_minutes=720)],
            "holidays": [_schedule()],
        },
        "rules": {"time_restrictions": {"quotas": {"mon": 90, "tue": 120}}},
        "usage": {
            "items": [
                {
                    "type": 301,
                    "app_name": "Reddit",
                    "exe": "com.reddit",
                    "minutes": 17,
                    "platform": 4,
                    "thumbnail": "r",
                },
                {"type": 301, "app_name": "eBay", "exe": "com.ebay", "minutes": 35, "platform": 4, "thumbnail": "e"},
                {"type": 301, "app_name": "Idle", "exe": "x", "minutes": 0, "platform": 0},
                {"type": 101, "host": "youtube.com", "minutes": 21, "pages": 76, "blocked_pages": 76},
                {"type": 101, "host": "google.com", "minutes": 0, "pages": 1, "blocked_pages": 0},
            ]
        },
        "extra_time_minutes": 15,
    }
    return DayInputs(**(base | overrides))


def _report(day: date = date(2026, 11, 10), today: date = date(2026, 11, 12), **overrides: Any) -> dict[str, Any]:
    partial = overrides.pop("partial", [])
    return build_day_report(DayContext("11282538", "Jacob", day, today, TZ), _inputs(**overrides), partial)


class TestBuildDayReport:
    """Tests for build_day_report()."""

    def test_report_totals(self) -> None:
        """Totals match the live day: 158.2 total, 113.5 counted."""
        report = _report()
        assert report["total_minutes"] == 158.2
        assert report["counted_minutes"] == 113.5
        assert (report["profile_id"], report["profile_name"], report["date"]) == ("11282538", "Jacob", "2026-11-10")

    def test_report_routines_sorted_with_counts_and_windows(self) -> None:
        """Routines with minutes come first, largest first, with their counting flag and windows."""
        routines = _report()["routines"]
        assert [(r["name"], r["minutes"], r["counts"]) for r in routines[:3]] == [
            ("Term Time - After school", 48.0, True),
            ("Term Time - School", 31.2, False),
            ("Homework", 13.5, False),
        ]
        school = routines[1]
        assert school["windows"] == [{"start": "2026-11-10T08:40:00+11:00", "end": "2026-11-10T15:15:00+11:00"}]
        assert school["removed"] is False

    def test_report_routine_with_window_but_no_minutes_listed(self) -> None:
        """A routine with a window that day but no minutes is listed with 0 minutes."""
        night = next(r for r in _report()["routines"] if r["name"] == "Night")
        assert night["minutes"] == 0.0
        assert night["windows"] == [
            {"start": "2026-11-10T00:00:00+11:00", "end": "2026-11-10T08:00:00+11:00"},
            {"start": "2026-11-10T20:00:00+11:00", "end": "2026-11-11T00:00:00+11:00"},
        ]

    def test_report_removed_routine(self) -> None:
        """Minutes under a uid that no longer exists appear as a removed routine that counts."""
        hourly = [_hour("2026-11-10T03:00:00Z", 0, gone=600)]
        [removed] = _report(hourly=hourly, schedules={})["routines"][:1]
        assert removed == {
            "uid": "gone",
            "name": "Removed routine",
            "counts": True,
            "enabled": False,
            "paused": False,
            "removed": True,
            "minutes": 10.0,
            "windows": [],
        }

    def test_report_paused_routine_listed_without_window(self) -> None:
        """A paused routine with minutes is listed without windows; one with no minutes isn't listed."""
        names = [r["name"] for r in _report()["routines"]]
        assert "Holidays" not in names
        hourly = [_hour("2026-11-10T03:00:00Z", 0, holidays=300)]
        holidays = next(r for r in _report(hourly=hourly)["routines"] if r["name"] == "Holidays")
        assert (holidays["minutes"], holidays["windows"], holidays["paused"]) == (5.0, [], True)

    def test_report_hours_local_and_nonzero_only(self) -> None:
        """Hours are in local time, split by routine, and empty hours are dropped."""
        hours = _report()["hours"]
        assert [h["start"] for h in hours] == [
            "2026-11-10T08:00:00+11:00",
            "2026-11-10T14:00:00+11:00",
            "2026-11-10T15:00:00+11:00",
            "2026-11-10T16:00:00+11:00",
            "2026-11-10T17:00:00+11:00",
        ]
        assert hours[2] == {"start": "2026-11-10T15:00:00+11:00", "default_minutes": 25.0, "routines": {"school": 14.2}}

    def test_report_apps_and_websites_split(self) -> None:
        """Apps and websites are separated, sorted by minutes, and zero-minute items dropped."""
        report = _report()
        assert report["apps"] == [
            {"name": "eBay", "package": "com.ebay", "platform": "iOS", "minutes": 35.0, "thumbnail": "e"},
            {"name": "Reddit", "package": "com.reddit", "platform": "iOS", "minutes": 17.0, "thumbnail": "r"},
        ]
        assert report["websites"] == [{"host": "youtube.com", "minutes": 21.0, "pages": 76, "blocked_pages": 76}]

    def test_report_no_usage(self) -> None:
        """Missing usage data gives empty apps and websites."""
        report = _report(usage=None)
        assert (report["apps"], report["websites"]) == ([], [])

    def test_report_quota_from_rules_weekday(self) -> None:
        """The quota is the rules' quota for that weekday."""
        assert _report()["quota_minutes"] == 120
        assert _report(day=date(2026, 11, 9))["quota_minutes"] == 90
        assert _report(rules={})["quota_minutes"] == 0

    def test_report_extra_time_today_only(self) -> None:
        """Extra time is only reported for today."""
        past = _report()
        assert (past["extra_time_minutes"], past["is_today"]) == (None, False)
        today = _report(day=date(2026, 11, 12))
        assert (today["extra_time_minutes"], today["is_today"]) == (15, True)

    def test_report_partial_flag(self) -> None:
        """A partial report says which parts are missing; a full one has no partial key."""
        assert _report(partial=["apps"])["partial"] == ["apps"]
        assert "partial" not in _report()


def test_routine_without_uid_ignored() -> None:
    """A malformed routine entry without a uid is skipped."""
    routines = [{"name": "No uid"}, _routine("after", "Term Time - After school", True)]
    assert [r["name"] for r in _report(routines=routines)["routines"]][:1] == ["Term Time - After school"]
