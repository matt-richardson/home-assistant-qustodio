"""Qustodio sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_device_entities, setup_profile_entities
from .const import ATTRIBUTION, DOMAIN, ICON_IN_TIME, ICON_NO_TIME, get_platform_name
from .entity import QustodioBaseEntity, QustodioDeviceEntity
from .models import CoordinatorData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Qustodio sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Profile-level sensors
    entities = setup_profile_entities(coordinator, entry, QustodioSensor)
    _LOGGER.debug("Setting up %d profile screen time sensors", len(entities))

    # Device-level sensors
    device_entities = setup_device_entities(coordinator, entry, QustodioDeviceMdmTypeSensor)
    _LOGGER.debug("Setting up %d device MDM type sensors", len(device_entities))
    entities.extend(device_entities)

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
            return data.name
        return self._profile_id

    @property
    def attribution(self) -> str:
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        data = self._get_profile_data()
        if data:
            return data.raw_data.get("time")
        return None

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        data = self._get_profile_data()
        if data:
            raw = data.raw_data
            time_used = raw.get("time", 0)
            quota = raw.get("quota", 0)

            if time_used < quota:
                return ICON_IN_TIME
        return ICON_NO_TIME

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        data = self._get_profile_data()
        if not data:
            return None

        raw = data.raw_data
        time_used = raw.get("time", 0)
        quota = raw.get("quota", 0)

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

        # Add device list with status
        if not isinstance(self.coordinator.data, CoordinatorData):
            return attributes

        devices = self.coordinator.data.get_profile_devices(self._profile_id)
        device_list = []
        current_device_name = raw.get("current_device")

        # Find current device by name (API returns device name, not ID)
        current_device_obj = None
        if current_device_name:
            for device in devices:
                if device.name == current_device_name:
                    current_device_obj = device
                    break

        for device in devices:
            user_status = device.get_user_status(self._profile_id)
            device_info = {
                "name": device.name,
                "id": device.id,
                "type": device.type,
                "platform": get_platform_name(device.platform),
                "online": user_status.is_online if user_status else None,
                "last_seen": device.lastseen,
                "is_current": device == current_device_obj if current_device_obj else False,
            }
            device_list.append(device_info)

        attributes["devices"] = device_list
        attributes["device_count"] = len(device_list)

        # Add current device details if available
        if current_device_obj:
            attributes["current_device_name"] = current_device_obj.name
            attributes["current_device_id"] = current_device_obj.id
            attributes["current_device_type"] = current_device_obj.type
            attributes["current_device_platform"] = get_platform_name(current_device_obj.platform)

        return attributes


class QustodioDeviceMdmTypeSensor(QustodioDeviceEntity, SensorEntity):
    """Sensor for device MDM type."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} MDM Type"
        self._attr_unique_id = f"{DOMAIN}_device_mdm_type_{self._profile_id}_{self._device_id}"
        self._attr_icon = "mdi:shield-account"

    @property
    def native_value(self) -> str | None:
        """Return the MDM type."""
        device = self._get_device_data()
        if device and device.mdm:
            mdm_type = device.mdm.get("type")
            if mdm_type is not None:
                # Map MDM type codes to human-readable names
                mdm_type_map = {
                    0: "None",
                    1: "DEP",  # Device Enrollment Program
                    2: "MDM",  # Mobile Device Management
                    3: "Supervised",
                }
                return mdm_type_map.get(mdm_type, f"Unknown ({mdm_type})")
        return None
