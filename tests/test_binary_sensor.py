"""Tests for Qustodio binary sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.qustodio.binary_sensor import (
    QustodioBinarySensorBrowserLocked,
    QustodioBinarySensorComputerLocked,
    QustodioBinarySensorHasQuestionableEvents,
    QustodioBinarySensorHasQuotaRemaining,
    QustodioBinarySensorInternetPaused,
    QustodioBinarySensorIsOnline,
    QustodioBinarySensorLocationTrackingEnabled,
    QustodioBinarySensorNavigationLocked,
    QustodioBinarySensorPanicButtonActive,
    QustodioBinarySensorProtectionDisabled,
    QustodioBinarySensorUnauthorizedRemove,
    QustodioBinarySensorVpnDisabled,
    async_setup_entry,
)
from custom_components.qustodio.const import ATTRIBUTION, DOMAIN, MANUFACTURER


class TestQustodioBinarySensorSetup:
    """Tests for binary sensor platform setup."""

    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_coordinator: Mock,
    ) -> None:
        """Test binary sensor platform setup from config entry."""
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create 12 profile binary sensors (12 × 2 profiles = 24)
        # + 6 device binary sensors (6 × 2 devices = 12) = 36 total
        assert len(entities_added) == 36
        assert all(hasattr(entity, "is_on") for entity in entities_added)


class TestQustodioBinarySensorIsOnline:
    """Tests for IsOnline binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorIsOnline(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_is_online_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
        assert sensor.icon == "mdi:wifi"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when profile is online."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorIsOnline(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when profile is offline."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorIsOnline(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when data is unavailable."""
        profile_data = {"id": "profile_999", "name": "Unknown"}
        sensor = QustodioBinarySensorIsOnline(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorHasQuotaRemaining:
    """Tests for HasQuotaRemaining binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_has_quota_remaining_profile_1"
        assert sensor.icon == "mdi:timer-check"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when quota remains."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data)

        # profile_1 has quota=300, time=120, so has quota remaining
        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when quota is exceeded."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data)

        # Mock data where time exceeds quota
        mock_coordinator.data.profiles["profile_1"].raw_data["time"] = 350
        assert sensor.is_on is False

    def test_is_on_none_when_no_quota(self, mock_coordinator: Mock) -> None:
        """Test sensor when quota is not set."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data)

        # Mock data with no quota
        mock_coordinator.data.profiles["profile_1"].raw_data["quota"] = None
        assert sensor.is_on is None

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorInternetPaused:
    """Tests for InternetPaused binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorInternetPaused(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_internet_paused_profile_1"
        assert sensor.icon == "mdi:pause-circle"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when internet is paused."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorInternetPaused(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when internet is not paused."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorInternetPaused(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorInternetPaused(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorProtectionDisabled:
    """Tests for ProtectionDisabled binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_protection_disabled_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
        assert sensor.icon == "mdi:shield-off"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when protection is disabled."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when protection is enabled."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorPanicButtonActive:
    """Tests for PanicButtonActive binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_panic_button_active_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.SAFETY
        assert sensor.icon == "mdi:alert-circle"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when panic button is active."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when panic button is not active."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorNavigationLocked:
    """Tests for NavigationLocked binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_navigation_locked_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.LOCK
        assert sensor.icon == "mdi:web-cancel"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when navigation is locked."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when navigation is not locked."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorUnauthorizedRemove:
    """Tests for UnauthorizedRemove binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_unauthorized_remove_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
        assert sensor.icon == "mdi:shield-alert"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when tampering is detected."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when no tampering is detected."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorHasQuestionableEvents:
    """Tests for HasQuestionableEvents binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_has_questionable_events_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
        assert sensor.icon == "mdi:alert"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when questionable events exist."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when no questionable events exist."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorLocationTrackingEnabled:
    """Tests for LocationTrackingEnabled binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_location_tracking_enabled_profile_1"
        assert sensor.icon == "mdi:map-marker-check"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when location tracking is enabled."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when location tracking is disabled."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorBrowserLocked:
    """Tests for BrowserLocked binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_browser_locked_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.LOCK
        assert sensor.icon == "mdi:web-box"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when browser is locked."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when browser is not locked."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorVpnDisabled:
    """Tests for VpnDisabled binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_vpn_disabled_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
        assert sensor.icon == "mdi:vpn"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when VPN is disabled."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when VPN is enabled."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorComputerLocked:
    """Tests for ComputerLocked binary sensor."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorComputerLocked(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_computer_locked_profile_1"
        assert sensor.device_class == BinarySensorDeviceClass.LOCK
        assert sensor.icon == "mdi:laptop-off"

    def test_is_on_true(self, mock_coordinator: Mock) -> None:
        """Test sensor when computer is locked."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorComputerLocked(mock_coordinator, profile_data)

        assert sensor.is_on is True

    def test_is_on_false(self, mock_coordinator: Mock) -> None:
        """Test sensor when computer is not locked."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioBinarySensorComputerLocked(mock_coordinator, profile_data)

        assert sensor.is_on is False

    def test_is_on_unavailable(self, mock_coordinator: Mock) -> None:
        """Test sensor when coordinator update failed."""
        mock_coordinator.last_update_success = False
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorComputerLocked(mock_coordinator, profile_data)

        assert sensor.is_on is None


class TestQustodioBinarySensorAttribution:
    """Tests for binary sensor attribution."""

    def test_attribution(self, mock_coordinator: Mock) -> None:
        """Test that all binary sensors have attribution."""
        profile_data = {"id": "profile_1", "name": "Child One"}

        sensors = [
            QustodioBinarySensorIsOnline(mock_coordinator, profile_data),
            QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data),
            QustodioBinarySensorInternetPaused(mock_coordinator, profile_data),
            QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data),
            QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data),
            QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data),
            QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data),
            QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data),
            QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data),
            QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data),
            QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data),
            QustodioBinarySensorComputerLocked(mock_coordinator, profile_data),
        ]

        for sensor in sensors:
            assert sensor.attribution == ATTRIBUTION


class TestQustodioBinarySensorNoneReturns:
    """Test that all binary sensors return None when profile data unavailable."""

    def test_all_sensors_return_none_when_profile_not_found(self, mock_coordinator: Mock) -> None:
        """Test all sensors return None when profile doesn't exist in coordinator."""
        # Use a profile ID that doesn't exist in the coordinator
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}

        sensors = [
            QustodioBinarySensorIsOnline(mock_coordinator, profile_data),
            QustodioBinarySensorHasQuotaRemaining(mock_coordinator, profile_data),
            QustodioBinarySensorInternetPaused(mock_coordinator, profile_data),
            QustodioBinarySensorProtectionDisabled(mock_coordinator, profile_data),
            QustodioBinarySensorPanicButtonActive(mock_coordinator, profile_data),
            QustodioBinarySensorNavigationLocked(mock_coordinator, profile_data),
            QustodioBinarySensorUnauthorizedRemove(mock_coordinator, profile_data),
            QustodioBinarySensorHasQuestionableEvents(mock_coordinator, profile_data),
            QustodioBinarySensorLocationTrackingEnabled(mock_coordinator, profile_data),
            QustodioBinarySensorBrowserLocked(mock_coordinator, profile_data),
            QustodioBinarySensorVpnDisabled(mock_coordinator, profile_data),
            QustodioBinarySensorComputerLocked(mock_coordinator, profile_data),
        ]

        # All sensors should return None when profile data is unavailable
        for sensor in sensors:
            assert sensor.is_on is None

    def test_device_sensors_return_none_when_not_available(self, mock_coordinator: Mock) -> None:
        """Test device-level sensors return None when not available."""
        from custom_components.qustodio.binary_sensor import (
            QustodioDeviceBinarySensorBrowserLocked,
            QustodioDeviceBinarySensorOnline,
            QustodioDeviceBinarySensorPanicButton,
            QustodioDeviceBinarySensorProtectionDisabled,
            QustodioDeviceBinarySensorTampered,
            QustodioDeviceBinarySensorVpnEnabled,
        )

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}

        sensors = [
            QustodioDeviceBinarySensorOnline(mock_coordinator, profile_data, device_data),
            QustodioDeviceBinarySensorTampered(mock_coordinator, profile_data, device_data),
            QustodioDeviceBinarySensorProtectionDisabled(mock_coordinator, profile_data, device_data),
            QustodioDeviceBinarySensorVpnEnabled(mock_coordinator, profile_data, device_data),
            QustodioDeviceBinarySensorBrowserLocked(mock_coordinator, profile_data, device_data),
            QustodioDeviceBinarySensorPanicButton(mock_coordinator, profile_data, device_data),
        ]

        # Set coordinator as unavailable
        mock_coordinator.last_update_success = False

        # All device sensors should return None when not available
        for sensor in sensors:
            assert sensor.is_on is None


class TestQustodioBinarySensorDeviceInfo:
    """Tests for binary sensor device info."""

    def test_device_info(self, mock_coordinator: Mock) -> None:
        """Test that all binary sensors have correct device info."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioBinarySensorIsOnline(mock_coordinator, profile_data)

        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, "profile_1")}
        assert device_info["name"] == "Child One"
        assert device_info["manufacturer"] == MANUFACTURER
