"""Tests for Qustodio services."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# Task 7 tests: service handlers and registration
# ---------------------------------------------------------------------------


def _resolved(api=None):
    """Build a ResolvedTarget with mocked coordinator and optional api."""
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    return services.ResolvedTarget(
        coordinator=coordinator,
        api=api or AsyncMock(),
        profile_id="11",
        profile_uid="uid-11",
    )


@pytest.mark.asyncio
async def test_add_extra_time_creates_restriction_and_refreshes():
    """Test that _async_add_extra_time calls create_calendar_restriction and refreshes."""
    target = _resolved()
    hass = MagicMock()
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_add_extra_time(hass, call)
    target.api.create_calendar_restriction.assert_awaited_once()
    args = target.api.create_calendar_restriction.await_args.args
    assert args[0] == "uid-11"
    assert args[1] == 2
    assert args[2] == 900
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_pause_internet_creates_pause_restriction():
    """Test that _async_pause_internet calls create_calendar_restriction with type 3."""
    target = _resolved()
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "minutes": 20}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_pause_internet(MagicMock(), call)
    args = target.api.create_calendar_restriction.await_args.args
    assert args[0] == "uid-11"
    assert args[1] == 3
    assert args[2] == 0
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_internet_deletes_active_pause():
    """Test that _async_resume_internet looks up and deletes an active pause restriction."""
    api = AsyncMock()
    api.get_active_restriction.return_value = {"uid": "pause-1"}
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_resume_internet(MagicMock(), call)
    api.get_active_restriction.assert_awaited_once_with("uid-11", "pause_internet")
    api.delete_calendar_restriction.assert_awaited_once_with("uid-11", "pause-1")


@pytest.mark.asyncio
async def test_resume_internet_no_active_raises():
    """Test that _async_resume_internet raises ServiceValidationError when no active pause."""
    api = AsyncMock()
    api.get_active_restriction.return_value = None
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        with pytest.raises(ServiceValidationError):
            await services._async_resume_internet(MagicMock(), call)


@pytest.mark.asyncio
async def test_cancel_extra_time_deletes_active_extra_time():
    """Test that _async_cancel_extra_time looks up and deletes an active extra-time grant."""
    api = AsyncMock()
    api.get_active_restriction.return_value = {"uid": "et-1"}
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_cancel_extra_time(MagicMock(), call)
    api.get_active_restriction.assert_awaited_once_with("uid-11", "extra_time")
    api.delete_calendar_restriction.assert_awaited_once_with("uid-11", "et-1")


@pytest.mark.asyncio
async def test_activate_routine_resolves_name_and_creates_schedule():
    """Test that _async_activate_routine resolves routine name and calls create_routine_schedule."""
    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-9", "name": "Games allowed"}]
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "routine": "Games allowed", "duration_minutes": 30}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_activate_routine(MagicMock(), call)
    api.create_routine_schedule.assert_awaited_once()
    p_uid, r_uid, payload = api.create_routine_schedule.await_args.args
    assert (p_uid, r_uid) == ("uid-11", "rou-9")
    assert payload["duration_minutes"] == 30
    target.coordinator.async_request_refresh.assert_awaited_once()


def test_async_setup_services_registers_all():
    """Test that async_setup_services registers all five expected service names."""
    hass = MagicMock()
    hass.services.has_service.return_value = False
    services.async_setup_services(hass)
    registered = {c.args[1] for c in hass.services.async_register.call_args_list}
    assert registered == {
        "add_extra_time",
        "pause_internet",
        "resume_internet",
        "cancel_extra_time",
        "activate_routine",
    }


def test_resolve_target_non_qustodio_entry_raises():
    """A device whose config entries aren't Qustodio coordinators is rejected."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}  # no coordinators registered
    device = MagicMock()
    device.identifiers = {(DOMAIN, "11")}
    device.config_entries = {"some_other_entry"}
    registry = MagicMock()
    registry.async_get.return_value = device
    with patch("custom_components.qustodio.services.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError):
            services._resolve_target(hass, "device-1")


def test_async_setup_services_idempotent_when_already_registered():
    """Test that async_setup_services returns early when services are already registered."""
    hass = MagicMock()
    hass.services.has_service.return_value = True
    services.async_setup_services(hass)
    hass.services.async_register.assert_not_called()


def test_async_unload_services_removes_registered():
    """Test that async_unload_services removes all five expected service names."""
    hass = MagicMock()
    hass.services.has_service.return_value = True
    services.async_unload_services(hass)
    removed = {c.args[1] for c in hass.services.async_remove.call_args_list}
    assert removed == {
        "add_extra_time",
        "pause_internet",
        "resume_internet",
        "cancel_extra_time",
        "activate_routine",
    }
