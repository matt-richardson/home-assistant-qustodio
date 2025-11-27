"""Base entity for Qustodio integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import is_profile_available
from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .models import CoordinatorData, DeviceData, ProfileData, UserStatus


class QustodioBaseEntity(CoordinatorEntity):
    """Base class for Qustodio entities."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the base entity.

        Args:
            coordinator: The data update coordinator
            profile_data: Profile data from config entry
        """
        super().__init__(coordinator)
        self._profile_id = str(profile_data["id"])
        self._profile_name = profile_data.get("name", str(profile_data["id"]))

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity.

        All entities for the same profile share the same device.
        """
        # Try to get current profile name from coordinator data
        profile_name = self._profile_name
        profile_data = self._get_profile_data()
        if profile_data:
            profile_name = profile_data.name

        return DeviceInfo(
            identifiers={(DOMAIN, self._profile_id)},
            name=profile_name,
            manufacturer=MANUFACTURER,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entity is available if:
        - Last coordinator update was successful
        - Coordinator has data
        - Profile exists in coordinator data
        """
        return is_profile_available(self.coordinator, self._profile_id)

    def _get_profile_data(self) -> ProfileData | None:
        """Get profile data from coordinator.

        Returns:
            ProfileData if available, None otherwise
        """
        if isinstance(self.coordinator.data, CoordinatorData) and self._profile_id in self.coordinator.data.profiles:
            return self.coordinator.data.profiles[self._profile_id]
        return None

    def _build_base_attributes(self, data: ProfileData) -> dict[str, Any]:
        """Build base attributes common to all entity types.

        Args:
            data: Profile data from coordinator

        Returns:
            Dictionary of common attributes
        """
        # Access raw_data for backward compatibility with existing fields
        raw = data.raw_data
        return {
            "attribution": ATTRIBUTION,
            "profile_id": self._profile_id,
            "profile_uid": data.uid,
            "is_online": raw.get("is_online"),
            "current_device": raw.get("current_device"),
            "unauthorized_remove": raw.get("unauthorized_remove"),
            "device_tampered": raw.get("device_tampered"),
        }


class QustodioDeviceEntity(CoordinatorEntity):
    """Base class for Qustodio device-specific entities."""

    def __init__(
        self,
        coordinator: Any,
        profile_data: dict[str, Any],
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the device entity.

        Args:
            coordinator: The data update coordinator
            profile_data: Profile data from config entry
            device_data: Device data from config entry
        """
        super().__init__(coordinator)
        self._profile_id = str(profile_data["id"])
        self._profile_name = profile_data.get("name", str(profile_data["id"]))
        self._device_id = str(device_data["id"])
        self._device_name = device_data.get("name", str(device_data["id"]))

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity.

        Device entities are linked to both the profile and the specific device.
        """
        # Try to get current device name from coordinator data
        device_name = self._device_name
        device_data = self._get_device_data()
        if device_data:
            device_name = device_data.name

        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._profile_id}_{self._device_id}")},
            name=f"{self._profile_name} {device_name}",
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, self._profile_id),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entity is available if:
        - Last coordinator update was successful
        - Coordinator has data
        - Device exists in coordinator data
        """
        if not self.coordinator.last_update_success:
            return False
        if not isinstance(self.coordinator.data, CoordinatorData):
            return False
        return self._device_id in self.coordinator.data.devices

    def _get_device_data(self) -> DeviceData | None:
        """Get device data from coordinator.

        Returns:
            DeviceData if available, None otherwise
        """
        if isinstance(self.coordinator.data, CoordinatorData) and self._device_id in self.coordinator.data.devices:
            return self.coordinator.data.devices[self._device_id]
        return None

    def _get_user_status(self) -> UserStatus | None:
        """Get user status for this profile on this device.

        Returns:
            UserStatus if available, None otherwise
        """
        device_data = self._get_device_data()
        if device_data:
            return device_data.get_user_status(self._profile_id)
        return None
