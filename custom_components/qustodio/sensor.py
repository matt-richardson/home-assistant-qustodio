"""Qustodio sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_profile_entities
from .const import ATTRIBUTION, DOMAIN, ICON_IN_TIME, ICON_NO_TIME
from .entity import QustodioBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Qustodio sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = setup_profile_entities(coordinator, entry, QustodioSensor)
    async_add_entities(entities)


class QustodioSensor(QustodioBaseEntity, SensorEntity):
    """Qustodio sensor class."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_unique_id = f"{DOMAIN}_{self._profile_id}"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_suggested_display_precision = 1

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        data = self._get_profile_data()
        if data:
            profile_name = data.get("name", "Unknown")
            return f"Qustodio {profile_name}"
        return f"Qustodio {self._profile_id}"

    @property
    def attribution(self) -> str:
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        data = self._get_profile_data()
        return data.get("time") if data else None

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        data = self._get_profile_data()
        if data:
            time_used = data.get("time", 0)
            quota = data.get("quota", 0)

            if time_used < quota:
                return ICON_IN_TIME
        return ICON_NO_TIME

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        data = self._get_profile_data()
        if not data:
            return None

        time_used = data.get("time", 0)
        quota = data.get("quota", 0)

        # Calculate derived metrics
        quota_remaining = max(0, quota - time_used) if quota and time_used is not None else None
        percentage_used = round((time_used / quota) * 100, 1) if quota and time_used is not None and quota > 0 else None

        # Start with base attributes
        attributes = self._build_base_attributes(data)

        # Add sensor-specific attributes
        attributes.update(
            {
                "time_used_minutes": time_used,
                "quota_minutes": quota,
                "quota_remaining_minutes": quota_remaining,
                "percentage_used": percentage_used,
            }
        )

        return attributes
