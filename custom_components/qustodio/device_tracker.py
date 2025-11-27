"""Qustodio device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_device_entities
from .const import CONF_ENABLE_GPS_TRACKING, DEFAULT_ENABLE_GPS_TRACKING, DOMAIN
from .entity import QustodioDeviceEntity

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
    entities = setup_device_entities(coordinator, entry, QustodioDeviceTracker)
    async_add_entities(entities)


class QustodioDeviceTracker(QustodioDeviceEntity, TrackerEntity):
    """Qustodio device tracker class for individual devices."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name}"
        self._attr_unique_id = f"{DOMAIN}_tracker_{self._profile_id}_{self._device_id}"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        device = self._get_device_data()
        return device.location_latitude if device else None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        device = self._get_device_data()
        return device.location_longitude if device else None

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        device = self._get_device_data()
        if device and device.location_accuracy is not None:
            return int(device.location_accuracy)
        return 0

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        device = self._get_device_data()
        if not device:
            return None

        user_status = self._get_user_status()

        attributes = {
            "device_id": self._device_id,
            "device_name": device.name,
            "device_type": device.type,
            "platform": self._get_platform_name(device.platform),
            "version": device.version,
            "enabled": device.enabled == 1,
            "last_seen": device.lastseen,
            "location_time": device.location_time,
            "location_accuracy_meters": device.location_accuracy,
        }

        if user_status:
            attributes.update(
                {
                    "profile_id": self._profile_id,
                    "is_online": user_status.is_online,
                }
            )

        return attributes

    def _get_platform_name(self, platform: int) -> str:
        """Convert platform code to name."""
        platform_map = {
            0: "Windows",
            1: "macOS",
            3: "Android",
            4: "iOS",
            5: "Kindle",
        }
        return platform_map.get(platform, f"Unknown ({platform})")
