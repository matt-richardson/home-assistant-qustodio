"""The Qustodio integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import QustodioDataUpdateCoordinator
from .models import CoordinatorData
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER, Platform.BINARY_SENSOR]


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
