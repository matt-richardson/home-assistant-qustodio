"""The Qustodio integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .exceptions import QustodioAuthenticationError, QustodioConnectionError, QustodioException
from .models import CoordinatorData
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER, Platform.BINARY_SENSOR]

# Update every 5 minutes - parental control data doesn't need real-time updates
# This reduces API load, prevents rate limiting, and conserves battery on mobile devices
UPDATE_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Qustodio from a config entry."""
    username = entry.data["username"]
    password = entry.data["password"]

    api = QustodioApi(username, password)

    coordinator = QustodioDataUpdateCoordinator(hass, api, entry)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: QustodioDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Update the coordinator's update interval if it changed
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    new_interval = timedelta(minutes=update_interval)

    if coordinator.update_interval != new_interval:
        _LOGGER.info("Updating coordinator interval to %s minutes", update_interval)
        coordinator.update_interval = new_interval
        # Request a refresh with the new interval
        await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the API session to prevent resource leaks
        await coordinator.api.close()

    return unload_ok


class QustodioDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: QustodioApi, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry

        # Initialize statistics tracking
        self.statistics: dict[str, Any] = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "consecutive_failures": 0,
            "error_counts": {},  # Track errors by type
        }

        # Get update interval from options or use default
        update_interval_minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        update_interval = timedelta(minutes=update_interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data via library."""
        update_time = datetime.now(timezone.utc).isoformat()
        self.statistics["total_updates"] += 1
        self.statistics["last_update_time"] = update_time

        try:
            data = await self.api.get_data()

            # Update success statistics
            self.statistics["successful_updates"] += 1
            self.statistics["last_success_time"] = update_time
            self.statistics["consecutive_failures"] = 0

            return data
        except QustodioAuthenticationError as err:
            # Track failure statistics
            self._track_failure("QustodioAuthenticationError")

            # Authentication errors should trigger a reauth flow
            _LOGGER.error("Authentication failed: %s", err)
            # Get the config entry from hass data
            entry_id = None
            for entry_id_key, coordinator in self.hass.data.get(DOMAIN, {}).items():
                if coordinator == self:
                    entry_id = entry_id_key
                    break

            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if entry:
                    _LOGGER.info("Triggering reauthentication flow for entry %s", entry_id)
                    entry.async_start_reauth(self.hass)

            raise UpdateFailed(f"Authentication failed: {err}") from err
        except QustodioConnectionError as err:
            # Track failure statistics
            self._track_failure("QustodioConnectionError")

            # Connection errors are usually temporary
            _LOGGER.warning("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except QustodioException as err:
            # Track failure statistics
            self._track_failure("QustodioException")

            # Other Qustodio-specific errors
            _LOGGER.error("Qustodio API error: %s", err)
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            # Track failure statistics
            self._track_failure("UnexpectedError")

            # Unexpected errors
            _LOGGER.exception("Unexpected error updating Qustodio data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _track_failure(self, error_type: str) -> None:
        """Track update failure statistics.

        Args:
            error_type: The type of error that occurred
        """
        self.statistics["failed_updates"] += 1
        self.statistics["consecutive_failures"] += 1
        self.statistics["last_failure_time"] = datetime.now(timezone.utc).isoformat()

        # Track error counts by type
        if error_type not in self.statistics["error_counts"]:
            self.statistics["error_counts"][error_type] = 0
        self.statistics["error_counts"][error_type] += 1


def setup_profile_entities(
    coordinator: QustodioDataUpdateCoordinator,
    entry: ConfigEntry,
    entity_class: type,
) -> list:
    """Create entities for each profile in the config entry.

    Args:
        coordinator: The data update coordinator
        entry: The config entry
        entity_class: The entity class to instantiate

    Returns:
        List of entity instances
    """
    profiles = entry.data.get("profiles", {})
    return [entity_class(coordinator, profile_data) for profile_data in profiles.values()]


def setup_device_entities(
    coordinator: QustodioDataUpdateCoordinator,
    entry: ConfigEntry,
    entity_class: type,
) -> list:
    """Create device entities for each device-profile combination.

    Args:
        coordinator: The data update coordinator
        entry: The config entry
        entity_class: The entity class to instantiate

    Returns:
        List of entity instances
    """
    entities: list = []
    profiles = entry.data.get("profiles", {})

    # Get coordinator data to access devices
    if not isinstance(coordinator.data, CoordinatorData):
        _LOGGER.warning("Coordinator data not available for device entity setup")
        return entities

    _LOGGER.debug("Setting up device entities for %d profiles", len(profiles))

    for profile_data in profiles.values():
        profile_id = str(profile_data["id"])
        # Get devices for this profile
        devices = coordinator.data.get_profile_devices(profile_id)

        _LOGGER.debug("Profile %s (%s) has %d devices", profile_id, profile_data.get("name"), len(devices))

        for device in devices:
            # Create device dict for entity initialization
            device_dict = {
                "id": device.id,
                "name": device.name,
            }
            _LOGGER.debug(
                "Creating device entity for device %s (%s) under profile %s",
                device.id,
                device.name,
                profile_id,
            )
            entities.append(entity_class(coordinator, profile_data, device_dict))

    _LOGGER.debug("Created %d device entities", len(entities))
    return entities


def is_profile_available(coordinator: DataUpdateCoordinator, profile_id: str) -> bool:
    """Check if a profile is available in coordinator data.

    Args:
        coordinator: The data update coordinator
        profile_id: The profile ID to check

    Returns:
        True if profile data is available
    """
    if not coordinator.last_update_success or coordinator.data is None:
        return False
    if isinstance(coordinator.data, CoordinatorData):
        return profile_id in coordinator.data.profiles
    # Fallback for old dict-based data structure during migration
    return profile_id in coordinator.data
