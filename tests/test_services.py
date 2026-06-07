"""Tests for Qustodio services."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.qustodio import services
from custom_components.qustodio.const import CONF_ALLOW_WRITES, DOMAIN


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


def _fake_hass_with_profile(allow_writes=True, profile_id="11", profile_uid="uid-11"):
    """Build a hass mock whose device registry resolves a profile device."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    profile = MagicMock()
    profile.uid = profile_uid
    coordinator.data.profiles = {profile_id: profile}

    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.options = {CONF_ALLOW_WRITES: allow_writes}
    coordinator.entry = entry  # resolver reads coordinator.entry

    hass = MagicMock()
    hass.data = {DOMAIN: {"entry1": coordinator}}

    device = MagicMock()
    device.identifiers = {(DOMAIN, profile_id)}
    device.config_entries = {"entry1"}

    registry = MagicMock()
    registry.async_get.return_value = device
    return hass, registry, coordinator, entry


def test_resolve_target_returns_profile_context():
    """Test that _resolve_target returns the correct profile context."""
    hass, registry, coordinator, _ = _fake_hass_with_profile()
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        target = services._resolve_target(hass, "device-1")
    assert target.profile_uid == "uid-11"
    assert target.coordinator is coordinator
    assert target.api is coordinator.api
    assert target.profile_id == "11"


def test_resolve_target_child_device_raises():
    """Targeting a child-device HA device (not the profile) is rejected."""
    hass, registry, coordinator, _ = _fake_hass_with_profile(profile_id="11")
    device = registry.async_get.return_value
    device.identifiers = {(DOMAIN, "11_99")}  # child-device identifier, not a profile key
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError, match="child device"):
            services._resolve_target(hass, "device-1")


def test_resolve_target_read_only_raises():
    """Test that _resolve_target raises ServiceValidationError in read-only mode."""
    hass, registry, _, _ = _fake_hass_with_profile(allow_writes=False)
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError, match="read-only"):
            services._resolve_target(hass, "device-1")


def test_resolve_target_unknown_device_raises():
    """Test that _resolve_target raises ServiceValidationError for an unknown device."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    registry = MagicMock()
    registry.async_get.return_value = None
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError):
            services._resolve_target(hass, "missing")
