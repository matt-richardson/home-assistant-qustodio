"""Tests for Qustodio screen time counting."""

from __future__ import annotations

from typing import Any

from custom_components.qustodio.screen_time import (
    ScreenTimeSplit,
    has_routine_time,
    routine_counting_map,
    split_screen_time,
)

SCHOOL_HOUR: dict[str, Any] = {
    "screen_time_seconds": 3000,
    "default_rules_screen_time": 1200,
    "routines_screen_time": [{"uid": "school", "seconds": 1800}],
}


class TestSplitScreenTime:
    """Tests for split_screen_time()."""

    def test_no_routines_counted_equals_total(self) -> None:
        """Hours without routine time (and without the default key) count in full."""
        hourly = [{"screen_time_seconds": 1800}, {"screen_time_seconds": 900}]
        assert split_screen_time(hourly, {}) == ScreenTimeSplit(45.0, 45.0)

    def test_non_counting_routine_excluded(self) -> None:
        """Time in a routine that doesn't count is left out of the counted total."""
        assert split_screen_time([SCHOOL_HOUR], {"school": False}) == ScreenTimeSplit(50.0, 20.0)

    def test_counting_routine_included(self) -> None:
        """Time in a routine that counts stays in the counted total."""
        assert split_screen_time([SCHOOL_HOUR], {"school": True}) == ScreenTimeSplit(50.0, 50.0)

    def test_unknown_routine_uid_counts(self) -> None:
        """A routine missing from the routines list (e.g. deleted) is counted."""
        assert split_screen_time([SCHOOL_HOUR], {}) == ScreenTimeSplit(50.0, 50.0)

    def test_mixed_routines(self) -> None:
        """Only the non-counting routine's seconds are subtracted."""
        hourly = [
            {
                "screen_time_seconds": 1800,
                "routines_screen_time": [{"uid": "a", "seconds": 600}, {"uid": "b", "seconds": 900}],
            }
        ]
        assert split_screen_time(hourly, {"a": False, "b": True}) == ScreenTimeSplit(30.0, 20.0)


class TestRoutineCountingMap:
    """Tests for routine_counting_map()."""

    def test_routine_counting_map_defaults_true(self) -> None:
        """Missing policy or flag defaults to counting."""
        routines = [
            {"uid": "a", "policy": {"counts_towards_daily_time_quota": False}},
            {"uid": "b", "policy": {}},
            {"uid": "c"},
        ]
        assert routine_counting_map(routines) == {"a": False, "b": True, "c": True}

    def test_routine_counting_map_ignores_paused_and_disabled(self) -> None:
        """Enabled/paused state doesn't change whether a routine's time counts."""
        routines = [
            {"uid": "h", "enabled": False, "paused": True, "policy": {"counts_towards_daily_time_quota": True}},
        ]
        assert routine_counting_map(routines) == {"h": True}


class TestHasRoutineTime:
    """Tests for has_routine_time()."""

    def test_has_routine_time(self) -> None:
        """Only a routine entry with seconds > 0 counts as routine time."""
        assert has_routine_time([]) is False
        assert has_routine_time([{"screen_time_seconds": 60, "routines_screen_time": []}]) is False
        assert has_routine_time([{"routines_screen_time": [{"uid": "a", "seconds": 0}]}]) is False
        assert has_routine_time([{"routines_screen_time": [{"uid": "a", "seconds": 60}]}]) is True
