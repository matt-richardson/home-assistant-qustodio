"""Qustodio device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_profile_entities
from .const import CONF_ENABLE_GPS_TRACKING, DEFAULT_ENABLE_GPS_TRACKING, DOMAIN
from .entity import QustodioBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qustodio device tracker based on a config entry."""
    # Check if GPS tracking is enabled
    gps_enabled = entry.options.get(CONF_ENABLE_GPS_TRACKING, DEFAULT_ENABLE_GPS_TRACKING)

    if not gps_enabled:
        _LOGGER.info("GPS tracking is disabled for this integration")
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = setup_profile_entities(coordinator, entry, QustodioDeviceTracker)
    async_add_entities(entities)


class QustodioDeviceTracker(QustodioBaseEntity, TrackerEntity):
    """Qustodio device tracker class."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, profile_data)
        self._attr_name = self._profile_name
        self._attr_unique_id = f"{DOMAIN}_tracker_{self._profile_id}"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        data = self._get_profile_data()
        return data.get("latitude") if data else None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        data = self._get_profile_data()
        return data.get("longitude") if data else None

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        data = self._get_profile_data()
        return data.get("accuracy", 0) if data else 0

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        data = self._get_profile_data()
        if not data:
            return None

        # Start with base attributes
        attributes = self._build_base_attributes(data)

        # Add device tracker-specific attributes
        attributes.update(
            {
                "last_seen": data.get("lastseen"),
                "location_accuracy_meters": data.get("accuracy", 0),
            }
        )

        return attributes
