"""Tests for Qustodio services."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError
from icalendar import Calendar

from custom_components.qustodio import services
from custom_components.qustodio.const import CONF_ALLOW_WRITES, DOMAIN


def _assert_valid_rrule(rrule: str) -> Calendar:
    """Validate a DTSTART/RRULE block against RFC 5545 and return the parsed VEVENT.

    The block is wrapped in a minimal VEVENT so icalendar parses it the same way a
    real calendar client would. icalendar silently drops a recurrence line that
    lacks the ``RRULE:`` property prefix (exactly the bug fixed in #18), so asserting
    that the RRULE component is present and carries a FREQ is what gives this teeth.
    """
    ical = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//qustodio-tests//EN\r\n"
        "BEGIN:VEVENT\r\nUID:test\r\n" + rrule.replace("\n", "\r\n") + "\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    event = Calendar.from_ical(ical).walk("VEVENT")[0]
    assert event.get("DTSTART") is not None, "rrule is missing a DTSTART"
    recur = event.get("RRULE")
    assert recur is not None, "rrule has no RRULE component (is the 'RRULE:' prefix present?)"
    assert recur.get("FREQ"), "RRULE is missing FREQ"
    return event


def test_build_extra_time_rrule():
    """Test that build_extra_time_rrule produces a single-occurrence DTSTART rrule."""
    now = datetime(2026, 6, 7, 11, 38, 19)
    assert services.build_extra_time_rrule(now) == "DTSTART:20260607T113819\nRRULE:FREQ=DAILY;COUNT=1"


def test_build_pause_rrule_appends_until():
    """Test that build_pause_rrule appends an UNTIL timestamp offset by the given minutes."""
    now = datetime(2026, 6, 7, 11, 31, 8)
    rrule = services.build_pause_rrule(now, 15)
    assert rrule == "DTSTART:20260607T113108\nRRULE:FREQ=DAILY;COUNT=1;UNTIL=20260607T114608"


def test_extra_time_rrule_is_valid_rfc5545():
    """The extra-time rrule must parse as RFC 5545 with a real RRULE component."""
    event = _assert_valid_rrule(services.build_extra_time_rrule(datetime(2026, 6, 7, 11, 38, 19)))
    assert event.get("RRULE").get("COUNT") == [1]


def test_pause_rrule_is_valid_rfc5545():
    """The pause rrule must parse as RFC 5545 and carry an UNTIL bound."""
    event = _assert_valid_rrule(services.build_pause_rrule(datetime(2026, 6, 7, 11, 31, 8), 15))
    assert event.get("RRULE").get("UNTIL")


def test_rrule_validator_rejects_missing_rrule_prefix():
    """Guard the validator itself: the pre-#18 form (no 'RRULE:' prefix) must fail."""
    buggy = "DTSTART:20260607T113819\nFREQ=DAILY;COUNT=1"
    with pytest.raises(AssertionError):
        _assert_valid_rrule(buggy)


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


def _resolved(api=None, quota=300, time_used=0):
    """Build a ResolvedTarget with mocked coordinator and optional api.

    Defaults to a profile that is well within quota (no overage), so existing
    duration assertions are unaffected unless a test overrides quota/time_used.
    """
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    profile = MagicMock()
    profile.raw_data = {"quota": quota, "time": time_used}
    coordinator.data.profiles = {"11": profile}
    return services.ResolvedTarget(
        coordinator=coordinator,
        api=api or AsyncMock(),
        profile_id="11",
        profile_uid="uid-11",
    )


@pytest.mark.asyncio
async def test_add_extra_time_creates_restriction_when_none_active():
    """Test that _async_add_extra_time creates a new restriction when none is active today."""
    target = _resolved()
    target.api.get_active_restriction.return_value = None
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
    target.api.update_calendar_restriction.assert_not_awaited()
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_extra_time_stacks_onto_active_restriction():
    """Test that _async_add_extra_time adds to an already-active restriction's duration.

    Must use create_calendar_restriction (POST), never update_calendar_restriction
    (PUT) - PUT zeros extra time and cancels all stacked grants instead of combining.
    """
    target = _resolved()
    target.api.get_active_restriction.return_value = {"uid": "r1", "duration": 3600}
    hass = MagicMock()
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_add_extra_time(hass, call)
    target.api.create_calendar_restriction.assert_awaited_once()
    args = target.api.create_calendar_restriction.await_args.args
    assert args[0] == "uid-11"
    assert args[1] == 2
    assert args[2] == 4500
    target.api.update_calendar_restriction.assert_not_awaited()
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_extra_time_covers_overage_left_by_a_cancelled_grant():
    """Test that a new grant still covers screen time already used beyond quota.

    Scenario: quota=30, an earlier 30-minute extra-time grant was fully used
    (time=60), then cancel_extra_time zeroed the server's record of that grant
    (so get_active_restriction now returns None). A fresh 60-minute grant
    should still result in 60 minutes of *usable* remaining time, not have the
    already-used overage eat into it a second time.
    """
    target = _resolved(quota=30, time_used=60)
    target.api.get_active_restriction.return_value = None
    hass = MagicMock()
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "minutes": 60}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_add_extra_time(hass, call)
    target.api.create_calendar_restriction.assert_awaited_once()
    args = target.api.create_calendar_restriction.await_args.args
    assert args[0] == "uid-11"
    assert args[1] == 2
    # 60 new minutes + 30 minutes overage (60 used - 30 quota) = 90 minutes
    assert args[2] == 90 * 60
    target.api.update_calendar_restriction.assert_not_awaited()


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
async def test_cancel_extra_time_sets_duration_zero():
    """cancel_extra_time PUTs the extra-time restriction to duration 0."""
    api = AsyncMock()
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"]}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_cancel_extra_time(MagicMock(), call)
    api.update_calendar_restriction.assert_awaited_once()
    p_uid, rtype, duration, _rrule = api.update_calendar_restriction.await_args.args
    assert p_uid == "uid-11"
    assert rtype == 2
    assert duration == 0
    target.coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_routine_resolves_name_and_creates_schedule():
    """Test that _async_activate_routine resolves routine name and calls create_routine_schedule."""
    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-9", "name": "Games allowed"}]
    api.get_active_routine_uid.return_value = None
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


@pytest.mark.asyncio
async def test_activate_routine_unknown_name_on_one_target_writes_nothing():
    """A routine name missing on one target must prevent writes on all targets."""
    api_a = AsyncMock()
    api_a.get_routines.return_value = [{"uid": "rou-9", "name": "Games allowed"}]
    api_b = AsyncMock()
    api_b.get_routines.return_value = [{"uid": "rou-1", "name": "Bedtime"}]  # no "Games allowed"
    target_a = _resolved(api=api_a)
    target_b = _resolved(api=api_b)
    call = MagicMock()
    call.data = {"device_id": ["device-a", "device-b"], "routine": "Games allowed", "duration_minutes": 30}
    with patch(
        "custom_components.qustodio.services._resolve_target",
        side_effect=[target_a, target_b],
    ):
        with pytest.raises(ServiceValidationError):
            await services._async_activate_routine(MagicMock(), call)
    # Name resolution happens for all targets before any write, so nothing is written.
    api_a.create_routine_schedule.assert_not_awaited()
    api_b.create_routine_schedule.assert_not_awaited()


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


@pytest.mark.asyncio
async def test_activate_routine_clears_existing_override_first():
    """Test that _async_activate_routine deletes an existing override before creating a new one."""
    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-new", "name": "Games allowed"}]
    api.get_active_routine_uid.return_value = "rou-active"
    api.get_routine_schedules.return_value = [
        {"uid": "regular", "overrides": False},
        {"uid": "ov-1", "overrides": True},
    ]
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "routine": "Games allowed", "duration_minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_activate_routine(MagicMock(), call)
    # Only the override (not the regular schedule) is deleted, on the active routine.
    api.delete_routine_schedule.assert_awaited_once_with("uid-11", "rou-active", "ov-1")
    api.create_routine_schedule.assert_awaited_once()
    p_uid, r_uid, _payload = api.create_routine_schedule.await_args.args
    assert (p_uid, r_uid) == ("uid-11", "rou-new")


@pytest.mark.asyncio
async def test_activate_routine_no_existing_override_skips_delete():
    """Test that _async_activate_routine skips deletion when no active routine is set."""
    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-new", "name": "Games allowed"}]
    api.get_active_routine_uid.return_value = None
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "routine": "Games allowed", "duration_minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        await services._async_activate_routine(MagicMock(), call)
    api.get_routine_schedules.assert_not_awaited()
    api.delete_routine_schedule.assert_not_awaited()
    api.create_routine_schedule.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_routine_maps_409_to_validation_error():
    """Test that a 409 from create_routine_schedule is surfaced as ServiceValidationError."""
    from custom_components.qustodio.exceptions import QustodioAPIError

    api = AsyncMock()
    api.get_routines.return_value = [{"uid": "rou-new", "name": "Games allowed"}]
    api.get_active_routine_uid.return_value = None
    api.create_routine_schedule.side_effect = QustodioAPIError("conflict", status_code=409)
    target = _resolved(api=api)
    call = MagicMock()
    call.data = {"device_id": ["device-1"], "routine": "Games allowed", "duration_minutes": 15}
    with patch("custom_components.qustodio.services._resolve_target", return_value=target):
        with pytest.raises(ServiceValidationError):
            await services._async_activate_routine(MagicMock(), call)
