"""The Qustodio integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .exceptions import QustodioAuthenticationError, QustodioConnectionError, QustodioException
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# Update every 5 minutes - parental control data doesn't need real-time updates
# This reduces API load, prevents rate limiting, and conserves battery on mobile devices
UPDATE_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Qustodio from a config entry."""
    username = entry.data["username"]
    password = entry.data["password"]

    api = QustodioApi(username, password)

    coordinator = QustodioDataUpdateCoordinator(hass, api)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Close the API session to prevent resource leaks
        await coordinator.api.close()

    return unload_ok


class QustodioDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: QustodioApi) -> None:
        """Initialize."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.get_data()
        except QustodioAuthenticationError as err:
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
            # Connection errors are usually temporary
            _LOGGER.warning("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except QustodioException as err:
            # Other Qustodio-specific errors
            _LOGGER.error("Qustodio API error: %s", err)
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            # Unexpected errors
            _LOGGER.exception("Unexpected error updating Qustodio data")
            raise UpdateFailed(f"Unexpected error: {err}") from err


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


def is_profile_available(coordinator: DataUpdateCoordinator, profile_id: str) -> bool:
    """Check if a profile is available in coordinator data.

    Args:
        coordinator: The data update coordinator
        profile_id: The profile ID to check

    Returns:
        True if profile data is available
    """
    return coordinator.last_update_success and coordinator.data is not None and profile_id in coordinator.data
