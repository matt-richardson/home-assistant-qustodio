"""Services for the Qustodio integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .const import CONF_ALLOW_WRITES, DEFAULT_ALLOW_WRITES, DOMAIN

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
