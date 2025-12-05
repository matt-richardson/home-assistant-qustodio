"""Tests for Qustodio sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant

from custom_components.qustodio.const import ATTRIBUTION, DOMAIN, ICON_IN_TIME, ICON_NO_TIME, MANUFACTURER
from custom_components.qustodio.sensor import QustodioSensor, async_setup_entry


class TestQustodioSensorSetup:
    """Tests for sensor platform setup."""

    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_coordinator: Mock,
    ) -> None:
        """Test sensor platform setup from config entry."""
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create one screen time sensor per profile (2) + one MDM type sensor per device (2) = 4
        assert len(entities_added) == 4
        # First 2 should be profile sensors, next 2 should be device sensors
        assert sum(1 for entity in entities_added if isinstance(entity, QustodioSensor)) == 2


class TestQustodioSensor:
    """Tests for QustodioSensor class."""

    def test_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test sensor initialization."""
        profile_data = {
            "id": "profile_1",
            "name": "Child One",
        }

        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor._profile_id == "profile_1"
        assert sensor.unique_id == f"{DOMAIN}_profile_1"
        assert sensor.device_class == SensorDeviceClass.DURATION
        assert sensor.native_unit_of_measurement == UnitOfTime.MINUTES
        assert sensor.suggested_display_precision == 1
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING

    def test_name_with_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.name == "Child One"

    def test_name_without_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.name == "profile_1"

    def test_name_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.name == "profile_999"

    def test_attribution(self, mock_coordinator: Mock) -> None:
        """Test sensor attribution."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.attribution == ATTRIBUTION

    def test_state_class(self, mock_coordinator: Mock) -> None:
        """Test sensor has TOTAL_INCREASING state class for long-term statistics."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # State class should be TOTAL_INCREASING since screen time:
        # - Is a cumulative daily total
        # - Only increases during the day
        # - Resets to 0 at midnight (daily cycle)
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING

    def test_device_info_with_data(self, mock_coordinator: Mock) -> None:
        """Test device info when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, "profile_1")}
        assert device_info["name"] == "Child One"
        assert device_info["manufacturer"] == MANUFACTURER

    def test_device_info_without_data(self, mock_coordinator: Mock) -> None:
        """Test device info when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, "profile_1")}
        # Base entity now uses profile name from init as fallback
        assert device_info["name"] == "Child One"
        assert device_info["manufacturer"] == MANUFACTURER

    def test_native_value_with_data(self, mock_coordinator: Mock) -> None:
        """Test native value when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.native_value == 120

    def test_native_value_without_data(self, mock_coordinator: Mock) -> None:
        """Test native value when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.native_value is None

    def test_native_value_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test native value when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.native_value is None

    def test_icon_within_quota(self, mock_coordinator: Mock) -> None:
        """Test icon when time used is within quota."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # profile_1 has time=120 and quota=300, so within quota
        assert sensor.icon == ICON_IN_TIME

    def test_icon_over_quota(self, mock_coordinator: Mock) -> None:
        """Test icon when time used exceeds quota."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # profile_2 has time=70.2 and quota=60, so over quota
        assert sensor.icon == ICON_NO_TIME

    def test_icon_without_data(self, mock_coordinator: Mock) -> None:
        """Test icon when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.icon == ICON_NO_TIME

    def test_icon_at_quota_boundary(self, mock_coordinator: Mock) -> None:
        """Test icon when time used equals quota."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Modify data to have time equal to quota
        mock_coordinator.data.profiles["profile_1"].raw_data["time"] = 120
        mock_coordinator.data.profiles["profile_1"].raw_data["quota"] = 120

        # At boundary, should not be "in time" (uses < not <=)
        assert sensor.icon == ICON_NO_TIME

    def test_extra_state_attributes_with_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes

        assert attributes is not None
        assert attributes["attribution"] == ATTRIBUTION
        assert attributes["profile_id"] == "profile_1"
        assert attributes["profile_uid"] == "uid_1"
        assert attributes["time_used_minutes"] == 120
        assert attributes["quota_minutes"] == 300
        assert attributes["quota_remaining_minutes"] == 180
        assert attributes["percentage_used"] == 40.0
        assert attributes["current_device"] == "iPhone 12"
        assert attributes["is_online"] is True
        assert attributes["unauthorized_remove"] is True
        assert attributes["device_tampered"] is None

    def test_extra_state_attributes_without_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.extra_state_attributes is None

    def test_extra_state_attributes_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.extra_state_attributes is None

    def test_available_when_profile_exists(self, mock_coordinator: Mock) -> None:
        """Test sensor availability when profile exists in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.available is True

    def test_available_when_coordinator_has_no_data(self, mock_coordinator: Mock) -> None:
        """Test sensor availability when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.available is False

    def test_available_when_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test sensor availability when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.available is False

    def test_available_when_last_update_failed(self, mock_coordinator: Mock) -> None:
        """Test sensor availability when last coordinator update failed."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Simulate failed update
        mock_coordinator.last_update_success = False

        assert sensor.available is False

    def test_sensor_with_missing_optional_fields(self, mock_coordinator: Mock) -> None:
        """Test sensor handles missing optional fields gracefully."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Remove optional fields from coordinator data
        mock_coordinator.data.profiles["profile_1"].raw_data = {
            "id": "profile_1",
            "uid": "uid_1",
            "name": "Child One",
            "device_count": 1,
            "device_ids": ["device_1"],
        }

        # Should handle missing fields gracefully
        assert sensor.native_value is None
        assert sensor.icon == ICON_NO_TIME

        attributes = sensor.extra_state_attributes
        assert attributes is not None
        assert attributes["time_used_minutes"] == 0
        assert attributes["quota_minutes"] == 0
        assert attributes["quota_remaining_minutes"] is None
        assert attributes["percentage_used"] is None
        assert attributes["current_device"] is None
        assert attributes["is_online"] is None

    def test_sensor_offline_profile(self, mock_coordinator: Mock) -> None:
        """Test sensor with offline profile."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # profile_2 is offline
        assert sensor.native_value == 70.2

        attributes = sensor.extra_state_attributes
        assert attributes is not None
        assert attributes["profile_id"] == "profile_2"
        assert attributes["profile_uid"] == "uid_2"
        assert attributes["time_used_minutes"] == 70.2
        assert attributes["quota_minutes"] == 60
        assert attributes["quota_remaining_minutes"] == 0
        assert attributes["percentage_used"] == 117.0
        assert attributes["is_online"] is False
        assert attributes["current_device"] is None
        assert attributes["unauthorized_remove"] is False
        assert attributes["device_tampered"] is None

    def test_device_list_attributes(self, mock_coordinator: Mock) -> None:
        """Test device list is correctly populated in attributes."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # Check device list exists and has correct structure
        assert "devices" in attributes
        device_list = attributes["devices"]
        assert isinstance(device_list, list)
        assert len(device_list) == 1

        # Verify device information structure
        device = device_list[0]
        assert "name" in device
        assert "id" in device
        assert "type" in device
        assert "platform" in device
        assert "online" in device
        assert "last_seen" in device
        assert "is_current" in device

        # Verify specific device values
        assert device["name"] == "iPhone 12"
        assert device["id"] == "device_1"
        assert device["type"] == "MOBILE"
        assert device["platform"] == "iOS"
        assert device["online"] is True

    def test_current_device_attributes(self, mock_coordinator: Mock) -> None:
        """Test current device information when current_device is set."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # Verify current device attributes
        assert "current_device_name" in attributes
        assert "current_device_id" in attributes
        assert "current_device_type" in attributes
        assert "current_device_platform" in attributes

        assert attributes["current_device_name"] == "iPhone 12"
        assert attributes["current_device_id"] == "device_1"
        assert attributes["current_device_type"] == "MOBILE"
        assert attributes["current_device_platform"] == "iOS"

    def test_device_list_without_current_device(self, mock_coordinator: Mock) -> None:
        """Test device list when profile has no current device."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Remove current_device from profile data
        mock_coordinator.data.profiles["profile_1"].raw_data.pop("current_device")

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # Device list should still exist
        assert "devices" in attributes
        device_list = attributes["devices"]
        assert len(device_list) == 1

        # is_current should be False for all devices
        assert device_list[0]["is_current"] is False

        # Current device attributes should not exist
        assert "current_device_name" not in attributes
        assert "current_device_id" not in attributes
        assert "current_device_type" not in attributes
        assert "current_device_platform" not in attributes

    def test_device_count_attribute(self, mock_coordinator: Mock) -> None:
        """Test device_count matches actual device list length."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # Verify device_count exists and matches device list
        assert "device_count" in attributes
        assert "devices" in attributes
        assert attributes["device_count"] == len(attributes["devices"])
        assert attributes["device_count"] == 1

    def test_is_current_flag(self, mock_coordinator: Mock) -> None:
        """Test is_current flag correctly identifies active device."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        device_list = attributes["devices"]
        assert len(device_list) == 1

        # The device should be marked as current
        assert device_list[0]["is_current"] is True
        assert device_list[0]["id"] == "device_1"

        # Verify this matches the current_device_id
        assert attributes["current_device_id"] == "device_1"

    def test_app_usage_attributes_with_data(self, mock_coordinator: Mock) -> None:
        """Test app usage attributes are included when data is available."""
        from custom_components.qustodio.models import AppUsage

        # Add app usage data to coordinator
        mock_coordinator.data.app_usage = {
            "profile_1": [
                AppUsage(
                    name="YouTube",
                    package="com.google.youtube",
                    minutes=45.5,
                    platform=3,
                    thumbnail="https://example.com/youtube.jpg",
                    questionable=True,
                ),
                AppUsage(
                    name="Minecraft", package="com.mojang.minecraft", minutes=30.0, platform=3, questionable=False
                ),
                AppUsage(name="WhatsApp", package="com.whatsapp", minutes=15.2, platform=3, questionable=False),
            ]
        }

        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # Verify apps list
        assert "apps" in attributes
        assert len(attributes["apps"]) == 3
        assert attributes["apps"][0]["name"] == "YouTube"
        assert attributes["apps"][0]["minutes"] == 45.5
        assert attributes["apps"][0]["package"] == "com.google.youtube"
        assert attributes["apps"][0]["platform"] == "Android"
        assert attributes["apps"][0]["thumbnail"] == "https://example.com/youtube.jpg"
        assert attributes["apps"][0]["questionable"] is True

        # Verify aggregated stats
        assert attributes["total_apps_used"] == 3
        assert attributes["top_app"] == "YouTube"
        assert attributes["top_app_minutes"] == 45.5
        assert attributes["questionable_apps"] == 1

    def test_app_usage_attributes_no_data(self, mock_coordinator: Mock) -> None:
        """Test app usage attributes when no app usage data is available."""
        # No app usage data
        mock_coordinator.data.app_usage = None

        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # App usage attributes should not be present
        assert "apps" not in attributes
        assert "total_apps_used" not in attributes
        assert "top_app" not in attributes
        assert "top_app_minutes" not in attributes
        assert "questionable_apps" not in attributes

    def test_app_usage_attributes_empty_list(self, mock_coordinator: Mock) -> None:
        """Test app usage attributes when profile has empty app list."""
        # Empty app usage for this profile
        mock_coordinator.data.app_usage = {"profile_1": []}

        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        # App usage attributes should not be present for empty list
        assert "apps" not in attributes
        assert "total_apps_used" not in attributes

    def test_app_usage_attributes_without_questionable(self, mock_coordinator: Mock) -> None:
        """Test app usage attributes when no apps are questionable."""
        from custom_components.qustodio.models import AppUsage

        mock_coordinator.data.app_usage = {
            "profile_1": [
                AppUsage(name="Duolingo", package="com.duolingo", minutes=20.0, platform=4, questionable=False),
                AppUsage(name="Khan Academy", package="org.khanacademy", minutes=15.0, platform=4, questionable=False),
            ]
        }

        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes
        assert attributes is not None

        assert attributes["questionable_apps"] == 0
        assert attributes["total_apps_used"] == 2

    def test_extra_state_attributes_with_invalid_coordinator_data(self, mock_coordinator: Mock) -> None:
        """Test extra_state_attributes when coordinator.data is not CoordinatorData."""
        # Set coordinator.data to something that's not a CoordinatorData instance
        mock_coordinator.data = "invalid_data"

        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Should return None when data is invalid
        attributes = sensor.extra_state_attributes
        assert attributes is None


class TestQustodioDeviceMdmTypeSensor:
    """Test QustodioDeviceMdmTypeSensor class."""

    def test_mdm_type_sensor_init(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor initialization."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)

        assert sensor._attr_name == "Child One iPhone MDM Type"
        assert sensor._attr_unique_id == "qustodio_device_mdm_type_profile_1_device_1"
        assert sensor._attr_icon == "mdi:shield-account"

    def test_mdm_type_none(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when type is 0 (None)."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        # Set MDM type to 0
        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {"type": 0}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value == "None"

    def test_mdm_type_dep(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when type is 1 (DEP)."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {"type": 1}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value == "DEP"

    def test_mdm_type_mdm(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when type is 2 (MDM)."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {"type": 2}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value == "MDM"

    def test_mdm_type_supervised(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when type is 3 (Supervised)."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {"type": 3}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value == "Supervised"

    def test_mdm_type_unknown(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when type is unknown."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {"type": 99}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value == "Unknown (99)"

    def test_mdm_type_no_mdm_data(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when device has no MDM data."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        device_data_dict = mock_coordinator.data.devices["device_1"]
        device_data_dict.mdm = {}

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value is None

    def test_mdm_type_device_not_found(self, mock_coordinator: Mock) -> None:
        """Test MDM type sensor when device is not found."""
        from custom_components.qustodio.sensor import QustodioDeviceMdmTypeSensor

        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "nonexistent_device", "name": "iPhone"}

        sensor = QustodioDeviceMdmTypeSensor(mock_coordinator, profile_data, device_data)
        assert sensor.native_value is None
