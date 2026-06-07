"""Services for the Qustodio integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALLOW_WRITES,
    DEFAULT_ALLOW_WRITES,
    DOMAIN,
    RESTRICTION_TYPE_EXTRA_TIME,
    RESTRICTION_TYPE_PAUSE_INTERNET,
)

_LOGGER = logging.getLogger(__name__)

# Qustodio weekday codes indexed by datetime.weekday() (Mon=0 .. Sun=6)
_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


@dataclass
class ResolvedTarget:
    """A targeted profile resolved to its runtime context."""

    coordinator: Any
    api: Any
    profile_id: str
    profile_uid: str


def _resolve_target(hass: HomeAssistant, device_id: str) -> ResolvedTarget:
    """Resolve a targeted device to a Qustodio profile context.

    Args:
        hass: Home Assistant instance.
        device_id: The device registry id from the service target.

    Returns:
        The resolved profile context (coordinator, api, ids).

    Raises:
        ServiceValidationError: Device is unknown, not a Qustodio profile,
            or its config entry is in read-only mode.

    """
    registry = dr.async_get(hass)
    device = registry.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} not found.")

    entries = hass.data.get(DOMAIN, {})
    entry_id = next((eid for eid in device.config_entries if eid in entries), None)
    if entry_id is None:
        raise ServiceValidationError("Target is not a Qustodio profile.")

    coordinator = entries[entry_id]
    entry = coordinator.entry

    profiles = getattr(coordinator.data, "profiles", {}) or {}
    profile_id = next(
        (value for (domain, value) in device.identifiers if domain == DOMAIN and value in profiles),
        None,
    )
    if profile_id is None:
        raise ServiceValidationError("Target a Qustodio profile device, not a child device.")

    if not entry.options.get(CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES):
        raise ServiceValidationError(
            "Qustodio is in read-only mode. Enable write actions in the integration options to use this service."
        )

    return ResolvedTarget(
        coordinator=coordinator,
        api=coordinator.api,
        profile_id=profile_id,
        profile_uid=profiles[profile_id].uid,
    )


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


# ---------------------------------------------------------------------------
# Service name constants
# ---------------------------------------------------------------------------

SERVICE_ADD_EXTRA_TIME = "add_extra_time"
SERVICE_PAUSE_INTERNET = "pause_internet"
SERVICE_RESUME_INTERNET = "resume_internet"
SERVICE_CANCEL_EXTRA_TIME = "cancel_extra_time"
SERVICE_ACTIVATE_ROUTINE = "activate_routine"

ATTR_MINUTES = "minutes"
ATTR_DURATION_MINUTES = "duration_minutes"
ATTR_ROUTINE = "routine"

# ---------------------------------------------------------------------------
# Voluptuous schemas
# ---------------------------------------------------------------------------

_MINUTES = vol.All(vol.Coerce(int), vol.Range(min=1, max=1440))
_TARGET = {vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}

SCHEMA_ADD_EXTRA_TIME = vol.Schema({**_TARGET, vol.Required(ATTR_MINUTES): _MINUTES})
SCHEMA_PAUSE_INTERNET = vol.Schema({**_TARGET, vol.Required(ATTR_MINUTES): _MINUTES})
SCHEMA_RESUME_INTERNET = vol.Schema(_TARGET)
SCHEMA_CANCEL_EXTRA_TIME = vol.Schema(_TARGET)
SCHEMA_ACTIVATE_ROUTINE = vol.Schema(
    {**_TARGET, vol.Required(ATTR_ROUTINE): cv.string, vol.Required(ATTR_DURATION_MINUTES): _MINUTES}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _targets(hass: HomeAssistant, call: ServiceCall) -> list[ResolvedTarget]:
    """Resolve every targeted device to a profile context.

    Args:
        hass: Home Assistant instance.
        call: The service call containing device_id list.

    Returns:
        List of resolved profile contexts.

    """
    return [_resolve_target(hass, device_id) for device_id in call.data[ATTR_DEVICE_ID]]


# ---------------------------------------------------------------------------
# Service handlers
# ---------------------------------------------------------------------------


async def _async_add_extra_time(hass: HomeAssistant, call: ServiceCall) -> None:
    """Grant a profile extra screen time today.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id and minutes fields.

    """
    minutes = call.data[ATTR_MINUTES]
    rrule = build_extra_time_rrule(dt_util.now())
    for target in _targets(hass, call):
        await target.api.create_calendar_restriction(
            target.profile_uid, RESTRICTION_TYPE_EXTRA_TIME, minutes * 60, rrule
        )
        await target.coordinator.async_request_refresh()


async def _async_pause_internet(hass: HomeAssistant, call: ServiceCall) -> None:
    """Pause a profile's internet for the given number of minutes.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id and minutes fields.

    """
    minutes = call.data[ATTR_MINUTES]
    rrule = build_pause_rrule(dt_util.now(), minutes)
    for target in _targets(hass, call):
        await target.api.create_calendar_restriction(target.profile_uid, RESTRICTION_TYPE_PAUSE_INTERNET, 0, rrule)
        await target.coordinator.async_request_refresh()


async def _async_cancel_restriction(hass: HomeAssistant, call: ServiceCall, kind: str, label: str) -> None:
    """Cancel the newest active restriction of the given kind for each target.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id field.
        kind: Restriction kind string (e.g. 'pause_internet', 'extra_time').
        label: Human-readable label used in error messages.

    Raises:
        ServiceValidationError: When no active restriction of the given kind exists.

    """
    for target in _targets(hass, call):
        active = await target.api.get_active_restriction(target.profile_uid, kind)
        if not active:
            raise ServiceValidationError(f"No active {label} to cancel for this profile.")
        await target.api.delete_calendar_restriction(target.profile_uid, active["uid"])
        await target.coordinator.async_request_refresh()


async def _async_resume_internet(hass: HomeAssistant, call: ServiceCall) -> None:
    """Cancel an active internet pause for a profile.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id field.

    """
    await _async_cancel_restriction(hass, call, "pause_internet", "internet pause")


async def _async_cancel_extra_time(hass: HomeAssistant, call: ServiceCall) -> None:
    """Cancel an active extra-time grant for a profile.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id field.

    """
    await _async_cancel_restriction(hass, call, "extra_time", "extra-time grant")


async def _async_activate_routine(hass: HomeAssistant, call: ServiceCall) -> None:
    """Activate a routine for a fixed duration via a schedule override.

    Args:
        hass: Home Assistant instance.
        call: Service call with device_id, routine, and duration_minutes fields.

    """
    name = call.data[ATTR_ROUTINE]
    duration = call.data[ATTR_DURATION_MINUTES]
    payload = build_routine_override_payload(dt_util.now(), duration)
    for target in _targets(hass, call):
        routines = await target.api.get_routines(target.profile_uid)
        routine_uid = resolve_routine_uid(routines, name)
        await target.api.create_routine_schedule(target.profile_uid, routine_uid, payload)
        await target.coordinator.async_request_refresh()


# ---------------------------------------------------------------------------
# Registration / teardown
# ---------------------------------------------------------------------------


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Qustodio services (idempotent across config entries).

    Args:
        hass: Home Assistant instance.

    """
    if hass.services.has_service(DOMAIN, SERVICE_ADD_EXTRA_TIME):
        return
    registrations = [
        (SERVICE_ADD_EXTRA_TIME, _async_add_extra_time, SCHEMA_ADD_EXTRA_TIME),
        (SERVICE_PAUSE_INTERNET, _async_pause_internet, SCHEMA_PAUSE_INTERNET),
        (SERVICE_RESUME_INTERNET, _async_resume_internet, SCHEMA_RESUME_INTERNET),
        (SERVICE_CANCEL_EXTRA_TIME, _async_cancel_extra_time, SCHEMA_CANCEL_EXTRA_TIME),
        (SERVICE_ACTIVATE_ROUTINE, _async_activate_routine, SCHEMA_ACTIVATE_ROUTINE),
    ]
    for name, handler, schema in registrations:
        hass.services.async_register(DOMAIN, name, partial(handler, hass), schema=schema)


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Qustodio services.

    Args:
        hass: Home Assistant instance.

    """
    for name in (
        SERVICE_ADD_EXTRA_TIME,
        SERVICE_PAUSE_INTERNET,
        SERVICE_RESUME_INTERNET,
        SERVICE_CANCEL_EXTRA_TIME,
        SERVICE_ACTIVATE_ROUTINE,
    ):
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)
