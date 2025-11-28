"""Tests for Qustodio device tracker platform."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.qustodio.const import DOMAIN
from custom_components.qustodio.device_tracker import QustodioDeviceTracker, async_setup_entry


class TestQustodioDeviceTrackerSetup:
    """Tests for device tracker platform setup."""

    async def test_async_setup_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_coordinator: Mock,
    ) -> None:
        """Test device tracker platform setup from config entry."""
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should create one device tracker per device (2 devices)
        assert len(entities_added) == 2
        assert all(isinstance(entity, QustodioDeviceTracker) for entity in entities_added)

    async def test_async_setup_entry_gps_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_coordinator: Mock,
    ) -> None:
        """Test device tracker setup with GPS tracking disabled."""
        # Configure entry with GPS disabled
        mock_config_entry.options = {"enable_gps_tracking": False}
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        result = await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should not create any entities and return None
        assert result is None
        assert len(entities_added) == 0


class TestQustodioDeviceTracker:
    """Tests for QustodioDeviceTracker class."""

    def test_device_tracker_init(self, mock_coordinator: Mock) -> None:
        """Test device tracker initialization."""
        profile_data = {
            "id": "profile_1",
            "name": "Child One",
        }
        device_data = {
            "id": "device_1",
            "name": "iPhone 12",
        }

        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker._profile_id == "profile_1"
        assert tracker._profile_name == "Child One"
        assert tracker._device_id == "device_1"
        assert tracker._device_name == "iPhone 12"
        assert tracker.name == "Child One iPhone 12"
        assert tracker.unique_id == f"{DOMAIN}_tracker_profile_1_device_1"

    def test_latitude_with_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.latitude == 37.7749

    def test_latitude_without_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.latitude is None

    def test_latitude_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when device not in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Unknown Device"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.latitude is None

    def test_longitude_with_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.longitude == -122.4194

    def test_longitude_without_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.longitude is None

    def test_longitude_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when device not in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Unknown Device"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.longitude is None

    def test_location_accuracy_with_data(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.location_accuracy == 10

    def test_location_accuracy_without_data(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.location_accuracy == 0

    def test_location_accuracy_missing_field(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when accuracy field is missing."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Set accuracy to None in the device data
        mock_coordinator.data.devices["device_1"].location_accuracy = None

        assert tracker.location_accuracy == 0

    def test_source_type(self, mock_coordinator: Mock) -> None:
        """Test source type is always GPS."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.source_type == SourceType.GPS

    def test_extra_state_attributes_with_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        attributes = tracker.extra_state_attributes

        assert attributes is not None
        assert attributes["device_id"] == "device_1"
        assert attributes["device_name"] == "iPhone 12"
        assert attributes["device_type"] == "MOBILE"
        assert attributes["platform"] == "iOS"
        assert attributes["last_seen"] == "2025-11-23T10:30:00Z"
        assert attributes["is_online"] is True

    def test_extra_state_attributes_without_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.extra_state_attributes is None

    def test_extra_state_attributes_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when device not in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Unknown Device"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.extra_state_attributes is None

    def test_available_when_profile_exists(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when device exists in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.available is True

    def test_available_when_coordinator_has_no_data(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.available is False

    def test_available_when_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when device not in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Unknown Device"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        assert tracker.available is False

    def test_available_when_last_update_failed(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when last coordinator update failed."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Simulate failed update
        mock_coordinator.last_update_success = False

        assert tracker.available is False

    def test_device_tracker_with_missing_optional_fields(self, mock_coordinator: Mock) -> None:
        """Test device tracker handles missing optional fields gracefully."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # Set optional fields to None in the device data
        mock_coordinator.data.devices["device_1"].location_latitude = None
        mock_coordinator.data.devices["device_1"].location_longitude = None
        mock_coordinator.data.devices["device_1"].location_accuracy = None

        # Should handle missing fields gracefully
        assert tracker.latitude is None
        assert tracker.longitude is None
        assert tracker.location_accuracy == 0

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["device_name"] == "iPhone 12"
        assert attributes["last_seen"] == "2025-11-23T10:30:00Z"

    def test_device_tracker_offline_profile(self, mock_coordinator: Mock) -> None:
        """Test device tracker with offline device."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        device_data = {"id": "device_2", "name": "Android Phone"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # device_2 has no location
        assert tracker.latitude is None
        assert tracker.longitude is None
        assert tracker.location_accuracy == 0

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["device_name"] == "Android Phone"
        assert attributes["is_online"] is False
        assert attributes["last_seen"] == "2025-11-23T09:15:00Z"

    def test_device_tracker_online_with_location(self, mock_coordinator: Mock) -> None:
        """Test device tracker with online device and location data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone 12"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data, device_data)

        # device_1 is online with location
        assert tracker.latitude == 37.7749
        assert tracker.longitude == -122.4194
        assert tracker.location_accuracy == 10
        assert tracker.source_type == SourceType.GPS

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["is_online"] is True
        assert attributes["device_name"] == "iPhone 12"
        assert attributes["last_seen"] == "2025-11-23T10:30:00Z"
