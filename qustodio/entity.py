"""Base entity for Qustodio integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import is_profile_available
from .const import DOMAIN, MANUFACTURER


class QustodioBaseEntity(CoordinatorEntity):
    """Base class for Qustodio entities."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the base entity.

        Args:
            coordinator: The data update coordinator
            profile_data: Profile data from config entry
        """
        super().__init__(coordinator)
        self._profile_id = profile_data["id"]
        self._profile_name = profile_data.get("name", str(profile_data["id"]))

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity.

        All entities for the same profile share the same device.
        """
        # Try to get current profile name from coordinator data
        profile_name = self._profile_name
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            profile_name = self.coordinator.data[self._profile_id].get("name", self._profile_name)

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

    def _get_profile_data(self) -> dict[str, Any] | None:
        """Get profile data from coordinator.

        Returns:
            Profile data dict if available, None otherwise
        """
        if self.coordinator.data and self._profile_id in self.coordinator.data:
            return self.coordinator.data[self._profile_id]
        return None
