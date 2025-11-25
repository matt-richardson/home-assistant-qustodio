"""Qustodio binary sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_profile_entities
from .const import ATTRIBUTION, DOMAIN
from .entity import QustodioBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qustodio binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create all binary sensor types for each profile
    entities = []
    for sensor_class in [
        QustodioBinarySensorIsOnline,
        QustodioBinarySensorHasQuotaRemaining,
        QustodioBinarySensorInternetPaused,
        QustodioBinarySensorProtectionDisabled,
        QustodioBinarySensorPanicButtonActive,
        QustodioBinarySensorNavigationLocked,
        QustodioBinarySensorUnauthorizedRemove,
        QustodioBinarySensorHasQuestionableEvents,
        QustodioBinarySensorLocationTrackingEnabled,
        QustodioBinarySensorBrowserLocked,
        QustodioBinarySensorVpnDisabled,
        QustodioBinarySensorComputerLocked,
    ]:
        entities.extend(setup_profile_entities(coordinator, entry, sensor_class))

    async_add_entities(entities)


class QustodioBinarySensor(QustodioBaseEntity, BinarySensorEntity):
    """Base class for Qustodio binary sensors."""

    _attr_attribution = ATTRIBUTION


# Phase 1: Most Useful Sensors


class QustodioBinarySensorIsOnline(QustodioBinarySensor):
    """Binary sensor for profile online status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Online"
        self._attr_unique_id = f"{DOMAIN}_is_online_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:wifi"

    @property
    def is_on(self) -> bool | None:
        """Return true if the profile is online."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("is_online", False)


class QustodioBinarySensorHasQuotaRemaining(QustodioBinarySensor):
    """Binary sensor for screen time quota remaining."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Has Quota Remaining"
        self._attr_unique_id = f"{DOMAIN}_has_quota_remaining_{self._profile_id}"
        self._attr_icon = "mdi:timer-check"

    @property
    def is_on(self) -> bool | None:
        """Return true if quota remains."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        quota = profile.get("quota", 0)
        time_used = profile.get("time", 0)
        return time_used < quota if quota and time_used is not None else None


class QustodioBinarySensorInternetPaused(QustodioBinarySensor):
    """Binary sensor for internet paused status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Internet Paused"
        self._attr_unique_id = f"{DOMAIN}_internet_paused_{self._profile_id}"
        self._attr_icon = "mdi:pause-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if internet is paused."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        pause_ends_at = profile.get("pause_internet_ends_at")
        return pause_ends_at is not None


class QustodioBinarySensorProtectionDisabled(QustodioBinarySensor):
    """Binary sensor for protection disabled status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Protection Disabled"
        self._attr_unique_id = f"{DOMAIN}_protection_disabled_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:shield-off"

    @property
    def is_on(self) -> bool | None:
        """Return true if protection is disabled."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("protection_disabled", False)


# Phase 2: Safety & Monitoring Sensors


class QustodioBinarySensorPanicButtonActive(QustodioBinarySensor):
    """Binary sensor for panic button status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Panic Button Active"
        self._attr_unique_id = f"{DOMAIN}_panic_button_active_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._attr_icon = "mdi:alert-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if panic button is active."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("panic_button_active", False)


class QustodioBinarySensorNavigationLocked(QustodioBinarySensor):
    """Binary sensor for navigation locked status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Navigation Locked"
        self._attr_unique_id = f"{DOMAIN}_navigation_locked_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.LOCK
        self._attr_icon = "mdi:web-cancel"

    @property
    def is_on(self) -> bool | None:
        """Return true if navigation is locked."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("navigation_locked", False)


class QustodioBinarySensorUnauthorizedRemove(QustodioBinarySensor):
    """Binary sensor for unauthorized app removal/tampering."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Tampering Detected"
        self._attr_unique_id = f"{DOMAIN}_unauthorized_remove_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:shield-alert"

    @property
    def is_on(self) -> bool | None:
        """Return true if tampering is detected."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("unauthorized_remove", False)


class QustodioBinarySensorHasQuestionableEvents(QustodioBinarySensor):
    """Binary sensor for questionable events detection."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Questionable Events"
        self._attr_unique_id = f"{DOMAIN}_has_questionable_events_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert"

    @property
    def is_on(self) -> bool | None:
        """Return true if there are questionable events."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        event_count = profile.get("questionable_events_count", 0)
        return event_count > 0


# Phase 3: Advanced Sensors


class QustodioBinarySensorLocationTrackingEnabled(QustodioBinarySensor):
    """Binary sensor for location tracking status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Location Tracking"
        self._attr_unique_id = f"{DOMAIN}_location_tracking_enabled_{self._profile_id}"
        self._attr_icon = "mdi:map-marker-check"

    @property
    def is_on(self) -> bool | None:
        """Return true if location tracking is enabled."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("location_tracking_enabled", False)


class QustodioBinarySensorBrowserLocked(QustodioBinarySensor):
    """Binary sensor for browser locked status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Browser Locked"
        self._attr_unique_id = f"{DOMAIN}_browser_locked_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.LOCK
        self._attr_icon = "mdi:web-box"

    @property
    def is_on(self) -> bool | None:
        """Return true if browser is locked."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("browser_locked", False)


class QustodioBinarySensorVpnDisabled(QustodioBinarySensor):
    """Binary sensor for VPN disabled status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} VPN Disabled"
        self._attr_unique_id = f"{DOMAIN}_vpn_disabled_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:vpn"

    @property
    def is_on(self) -> bool | None:
        """Return true if VPN is disabled."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("vpn_disabled", False)


class QustodioBinarySensorComputerLocked(QustodioBinarySensor):
    """Binary sensor for computer locked status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data)
        self._attr_name = f"{self._profile_name} Computer Locked"
        self._attr_unique_id = f"{DOMAIN}_computer_locked_{self._profile_id}"
        self._attr_device_class = BinarySensorDeviceClass.LOCK
        self._attr_icon = "mdi:laptop-off"

    @property
    def is_on(self) -> bool | None:
        """Return true if computer is locked."""
        if not self.available:
            return None
        profile = self.coordinator.data.get(self._profile_id, {})
        return profile.get("computer_locked", False)
