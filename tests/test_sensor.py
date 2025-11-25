"""Tests for Qustodio sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass
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

        # Should create one sensor per profile
        assert len(entities_added) == 2
        assert all(isinstance(entity, QustodioSensor) for entity in entities_added)


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

    def test_name_with_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.name == "Qustodio Child One"

    def test_name_without_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert sensor.name == "Qustodio profile_1"

    def test_name_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test sensor name when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.name == "Qustodio profile_999"

    def test_attribution(self, mock_coordinator: Mock) -> None:
        """Test sensor attribution."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        assert sensor.attribution == ATTRIBUTION

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
        mock_coordinator.data["profile_1"]["time"] = 120
        mock_coordinator.data["profile_1"]["quota"] = 120

        # At boundary, should not be "in time" (uses < not <=)
        assert sensor.icon == ICON_NO_TIME

    def test_extra_state_attributes_with_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        attributes = sensor.extra_state_attributes

        assert attributes is not None
        assert attributes["attribution"] == ATTRIBUTION
        assert attributes["time"] == 120
        assert attributes["current_device"] == "iPhone 12"
        assert attributes["is_online"] is True
        assert attributes["quota"] == 300
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
        mock_coordinator.data["profile_1"] = {
            "id": "profile_1",
            "name": "Child One",
        }

        # Should handle missing fields gracefully
        assert sensor.native_value is None
        assert sensor.icon == ICON_NO_TIME

        attributes = sensor.extra_state_attributes
        assert attributes is not None
        assert attributes["time"] is None
        assert attributes["current_device"] is None
        assert attributes["is_online"] is None
        assert attributes["quota"] is None

    def test_sensor_offline_profile(self, mock_coordinator: Mock) -> None:
        """Test sensor with offline profile."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        sensor = QustodioSensor(mock_coordinator, profile_data)

        # profile_2 is offline
        assert sensor.native_value == 70.2

        attributes = sensor.extra_state_attributes
        assert attributes is not None
        assert attributes["is_online"] is False
        assert attributes["current_device"] is None
        assert attributes["time"] == 70.2
        assert attributes["quota"] == 60
        assert attributes["unauthorized_remove"] is False
        assert attributes["device_tampered"] is None
