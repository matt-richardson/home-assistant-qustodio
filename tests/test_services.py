"""Tests for Qustodio services."""

from datetime import datetime

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.qustodio import services


def test_build_extra_time_rrule():
    """Test that build_extra_time_rrule produces a single-occurrence DTSTART rrule."""
    now = datetime(2026, 6, 7, 11, 38, 19)
    assert services.build_extra_time_rrule(now) == "DTSTART:20260607T113819\nFREQ=DAILY;COUNT=1"


def test_build_pause_rrule_appends_until():
    """Test that build_pause_rrule appends an UNTIL timestamp offset by the given minutes."""
    now = datetime(2026, 6, 7, 11, 31, 8)
    rrule = services.build_pause_rrule(now, 15)
    assert rrule == "DTSTART:20260607T113108\nRRULE:FREQ=DAILY;COUNT=1;UNTIL=20260607T114608"


def test_build_routine_override_payload():
    """Test that build_routine_override_payload maps Sunday correctly to 'SU'."""
    now = datetime(2026, 6, 7, 11, 41, 0)  # 2026-06-07 is a Sunday
    payload = services.build_routine_override_payload(now, 15)
    assert payload == {
        "overrides": True,
        "weekdays": ["SU"],
        "start_time": "11:41",
        "duration_minutes": 15,
        "from_date": "2026-06-07",
        "to_date": "2026-06-07",
    }


def test_resolve_routine_uid_matches_name():
    """Test that resolve_routine_uid returns the uid for a matching routine name."""
    routines = [{"uid": "a", "name": "Bedtime"}, {"uid": "b", "name": "Games allowed"}]
    assert services.resolve_routine_uid(routines, "Games allowed") == "b"


def test_resolve_routine_uid_unknown_raises():
    """Test that resolve_routine_uid raises ServiceValidationError for an unknown name."""
    routines = [{"uid": "a", "name": "Bedtime"}]
    with pytest.raises(ServiceValidationError):
        services.resolve_routine_uid(routines, "Nope")
