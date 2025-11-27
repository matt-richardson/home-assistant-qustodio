"""Qustodio binary sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import setup_device_entities, setup_profile_entities
from .const import ATTRIBUTION, DOMAIN
from .entity import QustodioBaseEntity, QustodioDeviceEntity

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

    # Create device-level binary sensors
    for device_sensor_class in [
        QustodioDeviceBinarySensorOnline,
        QustodioDeviceBinarySensorTampered,
        QustodioDeviceBinarySensorProtectionDisabled,
        QustodioDeviceBinarySensorVpnEnabled,
        QustodioDeviceBinarySensorBrowserLocked,
        QustodioDeviceBinarySensorPanicButton,
    ]:
        entities.extend(setup_device_entities(coordinator, entry, device_sensor_class))

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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("is_online", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            raw = profile.raw_data
            quota = raw.get("quota", 0)
            time_used = raw.get("time", 0)
            return time_used < quota if quota and time_used is not None else None
        return None


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
        profile = self._get_profile_data()
        if profile:
            pause_ends_at = profile.raw_data.get("pause_internet_ends_at")
            return pause_ends_at is not None
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("protection_disabled", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("panic_button_active", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("navigation_locked", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("unauthorized_remove", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            event_count = profile.raw_data.get("questionable_events_count", 0)
            return event_count > 0
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("location_tracking_enabled", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("browser_locked", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("vpn_disabled", False)
        return None


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
        profile = self._get_profile_data()
        if profile:
            return profile.raw_data.get("computer_locked", False)
        return None


# Device-Level Binary Sensors


class QustodioDeviceBinarySensor(QustodioDeviceEntity, BinarySensorEntity):
    """Base class for Qustodio device binary sensors."""

    _attr_attribution = ATTRIBUTION


class QustodioDeviceBinarySensorOnline(QustodioDeviceBinarySensor):
    """Binary sensor for device online status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} Online"
        self._attr_unique_id = f"{DOMAIN}_device_online_{self._profile_id}_{self._device_id}"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:wifi"

    @property
    def is_on(self) -> bool | None:
        """Return true if the device is online."""
        if not self.available:
            return None
        user_status = self._get_user_status()
        if user_status:
            return user_status.is_online
        return None


class QustodioDeviceBinarySensorTampered(QustodioDeviceBinarySensor):
    """Binary sensor for device tamper detection."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} Tampered"
        self._attr_unique_id = f"{DOMAIN}_device_tampered_{self._profile_id}_{self._device_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:shield-alert"

    @property
    def is_on(self) -> bool | None:
        """Return true if tampering is detected."""
        if not self.available:
            return None
        device = self._get_device_data()
        if device:
            # Check both MDM and alerts for unauthorized removal
            mdm_tampered = device.mdm.get("unauthorized_remove", False)
            alert_tampered = device.alerts.get("unauthorized_remove", False)
            return mdm_tampered or alert_tampered
        return None


class QustodioDeviceBinarySensorProtectionDisabled(QustodioDeviceBinarySensor):
    """Binary sensor for device protection disabled status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} Protection Disabled"
        self._attr_unique_id = f"{DOMAIN}_device_protection_disabled_{self._profile_id}_{self._device_id}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:shield-off"

    @property
    def is_on(self) -> bool | None:
        """Return true if protection is disabled."""
        if not self.available:
            return None
        user_status = self._get_user_status()
        if user_status:
            disable_protection = user_status.status.get("disable_protection", {})
            return disable_protection.get("status", False)
        return None


class QustodioDeviceBinarySensorVpnEnabled(QustodioDeviceBinarySensor):
    """Binary sensor for device VPN status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} VPN Enabled"
        self._attr_unique_id = f"{DOMAIN}_device_vpn_enabled_{self._profile_id}_{self._device_id}"
        self._attr_icon = "mdi:vpn"

    @property
    def is_on(self) -> bool | None:
        """Return true if VPN is enabled."""
        if not self.available:
            return None
        user_status = self._get_user_status()
        if user_status:
            vpn_disable = user_status.status.get("vpn_disable", {})
            # Note: API returns vpn_disable, so we invert it
            return not vpn_disable.get("status", False)
        return None


class QustodioDeviceBinarySensorBrowserLocked(QustodioDeviceBinarySensor):
    """Binary sensor for device browser locked status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} Browser Locked"
        self._attr_unique_id = f"{DOMAIN}_device_browser_locked_{self._profile_id}_{self._device_id}"
        self._attr_device_class = BinarySensorDeviceClass.LOCK
        self._attr_icon = "mdi:web-box"

    @property
    def is_on(self) -> bool | None:
        """Return true if browser is locked."""
        if not self.available:
            return None
        user_status = self._get_user_status()
        if user_status:
            browser_lock = user_status.status.get("browser_lock", {})
            return browser_lock.get("status", False)
        return None


class QustodioDeviceBinarySensorPanicButton(QustodioDeviceBinarySensor):
    """Binary sensor for device panic button status."""

    def __init__(self, coordinator: Any, profile_data: dict[str, Any], device_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, profile_data, device_data)
        self._attr_name = f"{self._profile_name} {self._device_name} Panic Button"
        self._attr_unique_id = f"{DOMAIN}_device_panic_button_{self._profile_id}_{self._device_id}"
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._attr_icon = "mdi:alert-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if panic button is active."""
        if not self.available:
            return None
        user_status = self._get_user_status()
        if user_status:
            panic_button = user_status.status.get("panic_button", {})
            return panic_button.get("status", False)
        return None
