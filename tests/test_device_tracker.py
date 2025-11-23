"""Tests for Qustodio device tracker platform."""

from __future__ import annotations

from unittest.mock import Mock

from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.qustodio.const import ATTRIBUTION, DOMAIN
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

        # Should create one device tracker per profile
        assert len(entities_added) == 2
        assert all(isinstance(entity, QustodioDeviceTracker) for entity in entities_added)


class TestQustodioDeviceTracker:
    """Tests for QustodioDeviceTracker class."""

    def test_device_tracker_init(self, mock_coordinator: Mock) -> None:
        """Test device tracker initialization."""
        profile_data = {
            "id": "profile_1",
            "name": "Child One",
        }

        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker._profile_id == "profile_1"
        assert tracker._profile_name == "Child One"
        assert tracker.name == "Qustodio Child One"
        assert tracker.unique_id == f"{DOMAIN}_tracker_profile_1"

    def test_latitude_with_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.latitude == 37.7749

    def test_latitude_without_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.latitude is None

    def test_latitude_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test latitude when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.latitude is None

    def test_longitude_with_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.longitude == -122.4194

    def test_longitude_without_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.longitude is None

    def test_longitude_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test longitude when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.longitude is None

    def test_location_accuracy_with_data(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.location_accuracy == 10

    def test_location_accuracy_without_data(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.location_accuracy == 0

    def test_location_accuracy_missing_field(self, mock_coordinator: Mock) -> None:
        """Test location accuracy when accuracy field is missing."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Remove accuracy field
        del mock_coordinator.data["profile_1"]["accuracy"]

        assert tracker.location_accuracy == 0

    def test_source_type(self, mock_coordinator: Mock) -> None:
        """Test source type is always GPS."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.source_type == SourceType.GPS

    def test_extra_state_attributes_with_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        attributes = tracker.extra_state_attributes

        assert attributes is not None
        assert attributes["attribution"] == ATTRIBUTION
        assert attributes["last_seen"] == "2025-11-23T10:30:00Z"
        assert attributes["is_online"] is True
        assert attributes["current_device"] == "iPhone 12"

    def test_extra_state_attributes_without_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.extra_state_attributes is None

    def test_extra_state_attributes_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test extra state attributes when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.extra_state_attributes is None

    def test_available_when_profile_exists(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when profile exists in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.available is True

    def test_available_when_coordinator_has_no_data(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Clear coordinator data
        mock_coordinator.data = None

        assert tracker.available is False

    def test_available_when_profile_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when profile not in coordinator data."""
        profile_data = {"id": "profile_999", "name": "Unknown Profile"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        assert tracker.available is False

    def test_available_when_last_update_failed(self, mock_coordinator: Mock) -> None:
        """Test tracker availability when last coordinator update failed."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Simulate failed update
        mock_coordinator.last_update_success = False

        assert tracker.available is False

    def test_device_tracker_with_missing_optional_fields(self, mock_coordinator: Mock) -> None:
        """Test device tracker handles missing optional fields gracefully."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # Remove optional fields from coordinator data
        mock_coordinator.data["profile_1"] = {
            "id": "profile_1",
            "name": "Child One",
        }

        # Should handle missing fields gracefully
        assert tracker.latitude is None
        assert tracker.longitude is None
        assert tracker.location_accuracy == 0

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["last_seen"] is None
        assert attributes["is_online"] is None
        assert attributes["current_device"] is None

    def test_device_tracker_offline_profile(self, mock_coordinator: Mock) -> None:
        """Test device tracker with offline profile."""
        profile_data = {"id": "profile_2", "name": "Child Two"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # profile_2 is offline
        assert tracker.latitude is None
        assert tracker.longitude is None
        assert tracker.location_accuracy == 0

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["is_online"] is False
        assert attributes["current_device"] is None
        assert attributes["last_seen"] == "2025-11-23T09:15:00Z"

    def test_device_tracker_online_with_location(self, mock_coordinator: Mock) -> None:
        """Test device tracker with online profile and location data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        tracker = QustodioDeviceTracker(mock_coordinator, profile_data)

        # profile_1 is online with location
        assert tracker.latitude == 37.7749
        assert tracker.longitude == -122.4194
        assert tracker.location_accuracy == 10
        assert tracker.source_type == SourceType.GPS

        attributes = tracker.extra_state_attributes
        assert attributes is not None
        assert attributes["is_online"] is True
        assert attributes["current_device"] == "iPhone 12"
        assert attributes["last_seen"] == "2025-11-23T10:30:00Z"
        assert attributes["attribution"] == ATTRIBUTION
