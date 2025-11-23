"""Qustodio device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qustodio device tracker based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    profiles = entry.data.get("profiles", {})

    entities = []
    for profile_id, profile_data in profiles.items():
        entities.append(QustodioDeviceTracker(coordinator, profile_data))

    async_add_entities(entities)


class QustodioDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Qustodio device tracker class."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._profile_id = profile_data["id"]
        self._profile_name = profile_data["name"]

        self._attr_name = f"Qustodio {self._profile_name}"
        self._attr_unique_id = f"{DOMAIN}_tracker_{self._profile_id}"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            return self.coordinator.data[self._profile_id].get("latitude")
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            return self.coordinator.data[self._profile_id].get("longitude")
        return None

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            return self.coordinator.data[self._profile_id].get("accuracy", 0)
        return 0

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            data = self.coordinator.data[self._profile_id]
            return {
                "attribution": ATTRIBUTION,
                "last_seen": data.get("lastseen"),
                "is_online": data.get("is_online"),
                "current_device": data.get("current_device"),
            }
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._profile_id in self.coordinator.data
        )
