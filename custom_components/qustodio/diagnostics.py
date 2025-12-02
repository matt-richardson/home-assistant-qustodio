"""Diagnostics support for Qustodio integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .models import CoordinatorData

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


def _build_app_usage_summary(coordinator_data: CoordinatorData) -> dict[str, Any]:
    """Build app usage summary for diagnostics.

    Args:
        coordinator_data: Coordinator data with app usage

    Returns:
        Dictionary with app usage summary by profile
    """
    if not coordinator_data.app_usage:
        return {}

    app_usage_summary = {}
    for profile_id, apps in coordinator_data.app_usage.items():
        # Find profile name for this profile_id
        profile_name = coordinator_data.profiles.get(profile_id, None)
        profile_key = profile_name.name if profile_name else f"profile_{profile_id}"

        app_usage_summary[profile_key] = {
            "total_apps": len(apps),
            "total_minutes": sum(app.minutes for app in apps),
            "questionable_apps": sum(1 for app in apps if app.questionable),
            "top_5_apps": [
                {
                    "name": app.name,
                    "minutes": app.minutes,
                    "platform": app.platform,
                    "questionable": app.questionable,
                }
                for app in apps[:5]  # Top 5 apps (already sorted by minutes)
            ],
        }
    return app_usage_summary


def _collect_entity_data(hass: HomeAssistant, entry: ConfigEntry) -> list[dict[str, Any]]:
    """Collect entity information for diagnostics.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        List of entity data dictionaries
    """
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
    return entities_data


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Collect entity information
    entities_data = _collect_entity_data(hass, entry)

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
            "last_update_time": coordinator.statistics["last_update_time"],
            "update_interval_seconds": coordinator.update_interval.total_seconds(),
            "name": coordinator.name,
        },
        "update_statistics": {
            "total_updates": coordinator.statistics["total_updates"],
            "successful_updates": coordinator.statistics["successful_updates"],
            "failed_updates": coordinator.statistics["failed_updates"],
            "success_rate": (
                round(
                    coordinator.statistics["successful_updates"] / coordinator.statistics["total_updates"] * 100,
                    2,
                )
                if coordinator.statistics["total_updates"] > 0
                else 0
            ),
            "consecutive_failures": coordinator.statistics["consecutive_failures"],
            "last_success_time": coordinator.statistics["last_success_time"],
            "last_failure_time": coordinator.statistics["last_failure_time"],
            "error_counts": coordinator.statistics["error_counts"],
        },
        "entities": entities_data,
    }

    # Add profile data if available (redacted)
    if coordinator.last_update_success and coordinator.data:
        if isinstance(coordinator.data, CoordinatorData):
            # Create a summary of profiles
            profiles_summary = []
            for _, profile_data in coordinator.data.profiles.items():
                raw = profile_data.raw_data
                profile_summary = {
                    "profile_id": "**REDACTED**",  # Always redact IDs
                    "name": profile_data.name,
                    "is_online": raw.get("is_online", False),
                    "has_location": bool(raw.get("latitude")),
                    "has_quota": bool(raw.get("quota")),
                    "time_used_minutes": raw.get("time", 0),
                    "quota_minutes": raw.get("quota", 0),
                    "current_device": raw.get("current_device"),
                    "unauthorized_remove": raw.get("unauthorized_remove", False),
                }
                profiles_summary.append(profile_summary)

            diagnostics["profiles"] = profiles_summary
            total_devices = len(coordinator.data.devices)
            diagnostics["profile_count"] = len(coordinator.data.profiles)
            diagnostics["device_count"] = total_devices

            # Add app usage information
            app_usage_summary = _build_app_usage_summary(coordinator.data)
            diagnostics["app_usage"] = app_usage_summary if app_usage_summary else None
            diagnostics["app_usage_cache_date"] = (
                coordinator._last_app_fetch_date.isoformat()  # pylint: disable=protected-access
                if coordinator._last_app_fetch_date  # pylint: disable=protected-access
                else None
            )

            # Add device statistics
            diagnostics["device_statistics"] = {
                "total": total_devices,
                "online": sum(
                    1
                    for device in coordinator.data.devices.values()
                    if any(user.is_online for user in device.users if user.is_online is not None)
                ),
                "with_location": sum(
                    1
                    for device in coordinator.data.devices.values()
                    if device.location_latitude is not None and device.location_longitude is not None
                ),
                "offline": total_devices
                - sum(
                    1
                    for device in coordinator.data.devices.values()
                    if any(user.is_online for user in device.users if user.is_online is not None)
                ),
            }

            # Convert dataclasses to flat dict for backward compatibility with tests
            # Flatten profile data at top level (not nested under "profiles")
            coordinator_data_dict = {
                profile_id: profile.raw_data for profile_id, profile in coordinator.data.profiles.items()
            }
            # Include full redacted data for debugging
            diagnostics["profile_data_full"] = async_redact_data(coordinator_data_dict, TO_REDACT)
    else:
        diagnostics["profiles"] = []
        diagnostics["profile_count"] = 0
        diagnostics["device_count"] = 0
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
                    "max_attempts": api._retry_config.max_attempts,  # pylint: disable=protected-access
                    "base_delay": api._retry_config.base_delay,  # pylint: disable=protected-access
                    "max_delay": api._retry_config.max_delay,  # pylint: disable=protected-access
                    "exponential_base": api._retry_config.exponential_base,  # pylint: disable=protected-access
                    "timeout": api._retry_config.timeout,  # pylint: disable=protected-access
                }
                if hasattr(api, "_retry_config")
                else None
            ),
        }

    return diagnostics
