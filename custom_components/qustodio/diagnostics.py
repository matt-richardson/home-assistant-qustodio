"""Diagnostics support for Qustodio integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Fields to redact from diagnostics output (sensitive data)
TO_REDACT = {
    "access_token",
    "username",
    "password",
    "email",
    "latitude",
    "longitude",
    "gps_latitude",
    "gps_longitude",
    "lastseen",
    "id",
    "uid",
    "device_id",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Collect entity information
    entity_reg = er.async_get(hass)
    entities_data = []
    for entity in er.async_entries_for_config_entry(entity_reg, entry.entry_id):
        entity_data = {
            "entity_id": entity.entity_id,
            "name": entity.name or entity.original_name,
            "platform": entity.platform,
            "disabled": entity.disabled,
            "disabled_by": entity.disabled_by.value if entity.disabled_by else None,
        }
        entities_data.append(entity_data)

    # Prepare diagnostics data
    diagnostics: dict[str, Any] = {
        "config_entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
            "version": entry.version,
            "minor_version": entry.minor_version,
            "source": entry.source,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update_time": (coordinator.last_update_time.isoformat() if coordinator.last_update_time else None),
            "update_interval_seconds": coordinator.update_interval.total_seconds(),
            "name": coordinator.name,
        },
        "entities": entities_data,
    }

    # Add profile data if available (redacted)
    if coordinator.last_update_success and coordinator.data:
        # Create a summary of profiles
        profiles_summary = []
        for _, profile_data in coordinator.data.items():
            profile_summary = {
                "profile_id": "**REDACTED**",  # Always redact IDs
                "name": profile_data.get("name", "Unknown"),
                "is_online": profile_data.get("is_online", False),
                "has_location": bool(profile_data.get("latitude")),
                "has_quota": bool(profile_data.get("quota")),
                "time_used_minutes": profile_data.get("time", 0),
                "quota_minutes": profile_data.get("quota", 0),
                "current_device": profile_data.get("current_device"),
                "unauthorized_remove": profile_data.get("unauthorized_remove", False),
            }
            profiles_summary.append(profile_summary)

        diagnostics["profiles"] = profiles_summary
        diagnostics["profile_count"] = len(coordinator.data)

        # Include full redacted data for debugging
        diagnostics["profile_data_full"] = async_redact_data(coordinator.data, TO_REDACT)
    else:
        diagnostics["profiles"] = []
        diagnostics["profile_count"] = 0
        diagnostics["profile_data_full"] = None

    # Include last error if update failed
    if not coordinator.last_update_success:
        if coordinator.last_exception:
            diagnostics["last_update_error"] = {
                "error": str(coordinator.last_exception),
                "error_type": type(coordinator.last_exception).__name__,
            }
        else:
            diagnostics["last_update_error"] = "Unknown error"

    # Include API client configuration
    if hasattr(coordinator, "api"):
        api = coordinator.api
        diagnostics["api_config"] = {
            "retry_config": (
                {
                    "max_retries": api._retry_config.max_retries,  # pylint: disable=protected-access
                    "initial_delay": api._retry_config.initial_delay,  # pylint: disable=protected-access
                    "max_delay": api._retry_config.max_delay,  # pylint: disable=protected-access
                    "exponential_base": api._retry_config.exponential_base,  # pylint: disable=protected-access
                    "timeout": api._retry_config.timeout,  # pylint: disable=protected-access
                }
                if hasattr(api, "_retry_config")
                else None
            ),
        }

    return diagnostics
