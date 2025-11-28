"""Tests for Qustodio entity module."""

from __future__ import annotations

from unittest.mock import Mock

from custom_components.qustodio.entity import QustodioBaseEntity, QustodioDeviceEntity
from custom_components.qustodio.models import UserStatus


class TestQustodioBaseEntityProfileIdConversion:
    """Tests for QustodioBaseEntity profile ID string conversion - covers line 26 in entity.py."""

    def test_profile_id_converted_to_string_from_int(self, mock_coordinator: Mock) -> None:
        """Test that integer profile IDs are converted to strings."""
        profile_data = {
            "id": 12345,  # Integer ID
            "name": "Test Child",
        }

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        # Profile ID should be converted to string - line 26
        assert isinstance(entity._profile_id, str)
        assert entity._profile_id == "12345"
        assert entity._profile_name == "Test Child"

    def test_profile_id_remains_string(self, mock_coordinator: Mock) -> None:
        """Test that string profile IDs remain strings."""
        profile_data = {
            "id": "profile_1",  # String ID
            "name": "Test Child",
        }

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        # Profile ID should remain string - line 26
        assert isinstance(entity._profile_id, str)
        assert entity._profile_id == "profile_1"

    def test_profile_name_fallback(self, mock_coordinator: Mock) -> None:
        """Test that profile name falls back to string ID when missing."""
        profile_data = {
            "id": 67890,
        }

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        # Should fall back to string version of ID - line 27
        assert entity._profile_id == "67890"
        assert entity._profile_name == "67890"


class TestQustodioDeviceEntityProfileIdConversion:
    """Tests for QustodioDeviceEntity profile ID string conversion - covers line 107 in entity.py."""

    def test_device_entity_profile_id_converted_to_string(self, mock_coordinator: Mock) -> None:
        """Test that device entity converts integer profile IDs to strings."""
        profile_data = {
            "id": 11282538,  # Integer ID from production bug fix
            "name": "Test Child",
        }
        device_data = {
            "id": 11408126,
            "name": "iPhone",
        }

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Profile ID should be converted to string - line 107
        assert isinstance(entity._profile_id, str)
        assert entity._profile_id == "11282538"
        assert entity._profile_name == "Test Child"

        # Device ID should also be converted to string - line 109
        assert isinstance(entity._device_id, str)
        assert entity._device_id == "11408126"
        assert entity._device_name == "iPhone"

    def test_device_entity_with_string_ids(self, mock_coordinator: Mock) -> None:
        """Test device entity with string IDs."""
        profile_data = {
            "id": "profile_1",
            "name": "Child One",
        }
        device_data = {
            "id": "device_1",
            "name": "Android",
        }

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        assert entity._profile_id == "profile_1"
        assert entity._device_id == "device_1"


class TestQustodioDeviceEntityDeviceInfo:
    """Tests for QustodioDeviceEntity device_info updates - covers lines 119-124 in entity.py."""

    def test_device_info_updates_device_name_from_coordinator(self, mock_coordinator: Mock) -> None:
        """Test that device_info uses updated device name from coordinator when available."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "Old Device Name"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Mock coordinator has updated device name
        mock_coordinator.data.devices["device_1"].name = "Updated Device Name"

        device_info = entity.device_info

        # Should use updated name from coordinator - lines 119-124
        assert "Updated Device Name" in device_info["name"]
        assert device_info["name"] == "Child One Updated Device Name"

    def test_device_info_falls_back_to_cached_name(self, mock_coordinator: Mock) -> None:
        """Test that device_info falls back to cached name when device not in coordinator."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Cached Device Name"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        device_info = entity.device_info

        # Should use cached name when device not found - lines 119-120
        assert "Cached Device Name" in device_info["name"]
        assert device_info["name"] == "Child One Cached Device Name"

    def test_device_info_with_no_coordinator_data(self, mock_coordinator: Mock) -> None:
        """Test device_info when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "Device Name"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        device_info = entity.device_info

        # Should fall back to cached name - lines 119-120
        assert "Device Name" in device_info["name"]


class TestQustodioDeviceEntityGetUserStatus:
    """Tests for QustodioDeviceEntity._get_user_status() - covers line 165 in entity.py."""

    def test_get_user_status_returns_none_when_device_missing(self, mock_coordinator: Mock) -> None:
        """Test _get_user_status returns None when device not in coordinator data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_999", "name": "Missing Device"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Device doesn't exist in coordinator
        result = entity._get_user_status()

        # Should return None - line 165
        assert result is None

    def test_get_user_status_returns_none_when_no_coordinator_data(self, mock_coordinator: Mock) -> None:
        """Test _get_user_status returns None when coordinator has no data."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Clear coordinator data
        mock_coordinator.data = None

        result = entity._get_user_status()

        # Should return None - line 165
        assert result is None

    def test_get_user_status_returns_user_status(self, mock_coordinator: Mock) -> None:
        """Test _get_user_status returns UserStatus when device exists."""
        profile_data = {"id": "profile_1", "name": "Child One"}
        device_data = {"id": "device_1", "name": "iPhone"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Device exists in coordinator with user status
        result = entity._get_user_status()

        # Should return UserStatus object - lines 162-164
        assert result is not None
        assert isinstance(result, UserStatus)
        assert result.is_online is True


class TestQustodioBaseEntityDeviceInfo:
    """Tests for QustodioBaseEntity device_info profile name updates."""

    def test_device_info_updates_profile_name_from_coordinator(self, mock_coordinator: Mock) -> None:
        """Test that device_info uses updated profile name from coordinator when available."""
        profile_data = {"id": "profile_1", "name": "Old Profile Name"}

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        # Coordinator should have updated name
        device_info = entity.device_info

        # Should use name from coordinator (Child One) not cached name - lines 35-39
        assert device_info["name"] == "Child One"

    def test_device_info_falls_back_to_cached_profile_name(self, mock_coordinator: Mock) -> None:
        """Test that device_info falls back to cached name when profile not in coordinator."""
        profile_data = {"id": "profile_999", "name": "Cached Profile Name"}

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        device_info = entity.device_info

        # Should use cached name when profile not found - lines 36-37
        assert device_info["name"] == "Cached Profile Name"

    def test_device_info_has_profile_model_and_model_id(self, mock_coordinator: Mock) -> None:
        """Test that profile device_info has correct model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}

        entity = QustodioBaseEntity(mock_coordinator, profile_data)

        device_info = entity.device_info

        # Should have "Profile" as model and "profile" as model_id - lines 45-46
        assert device_info["model"] == "Profile"
        assert device_info["model_id"] == "profile"


class TestQustodioDeviceEntityDeviceInfoPlatforms:
    """Tests for QustodioDeviceEntity device_info platform-based model names and model_id."""

    def test_device_info_android_device(self, mock_coordinator: Mock) -> None:
        """Test device_info for Android device has correct model and model_id."""
        profile_data = {"id": "profile_2", "name": "Test Child"}
        device_data = {"id": "device_2", "name": "Android Phone"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # device_2 in mock has platform 3 (Android)
        device_info = entity.device_info

        # Should have "Android Device" as model and "phone" as model_id - lines 127-143
        assert device_info["model"] == "Android Device"
        assert device_info["model_id"] == "phone"
        assert "Android Phone" in device_info["name"]

    def test_device_info_ios_device(self, mock_coordinator: Mock) -> None:
        """Test device_info for iOS device has correct model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_1", "name": "iPhone 12"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # device_1 in mock has platform 4 (iOS)
        device_info = entity.device_info

        # Should have "iOS Device" as model and "phone" as model_id
        assert device_info["model"] == "iOS Device"
        assert device_info["model_id"] == "phone"
        assert "iPhone 12" in device_info["name"]

    def test_device_info_windows_device(self, mock_coordinator: Mock) -> None:
        """Test device_info for Windows device has correct model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_1", "name": "Desktop"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Mock device has platform 0 (Windows)
        mock_coordinator.data.devices["device_1"].platform = 0

        device_info = entity.device_info

        # Should have "Windows Device" as model and "computer" as model_id
        assert device_info["model"] == "Windows Device"
        assert device_info["model_id"] == "computer"

    def test_device_info_macos_device(self, mock_coordinator: Mock) -> None:
        """Test device_info for macOS device has correct model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_1", "name": "MacBook"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Mock device has platform 1 (macOS)
        mock_coordinator.data.devices["device_1"].platform = 1

        device_info = entity.device_info

        # Should have "macOS Device" as model and "computer" as model_id
        assert device_info["model"] == "macOS Device"
        assert device_info["model_id"] == "computer"

    def test_device_info_kindle_device(self, mock_coordinator: Mock) -> None:
        """Test device_info for Kindle device has correct model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_1", "name": "Kindle"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Mock device has platform 5 (Kindle)
        mock_coordinator.data.devices["device_1"].platform = 5

        device_info = entity.device_info

        # Should have "Kindle Device" as model and "tablet" as model_id
        assert device_info["model"] == "Kindle Device"
        assert device_info["model_id"] == "tablet"

    def test_device_info_unknown_platform(self, mock_coordinator: Mock) -> None:
        """Test device_info for unknown platform has fallback model and model_id."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_1", "name": "Unknown Device"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        # Mock device has unknown platform
        mock_coordinator.data.devices["device_1"].platform = 99

        device_info = entity.device_info

        # Should have "Unknown (99) Device" as model and "device" as fallback model_id
        assert device_info["model"] == "Unknown (99) Device"
        assert device_info["model_id"] == "device"

    def test_device_info_no_device_data(self, mock_coordinator: Mock) -> None:
        """Test device_info when device data is not available from coordinator."""
        profile_data = {"id": "profile_1", "name": "Test Child"}
        device_data = {"id": "device_999", "name": "Cached Device"}

        entity = QustodioDeviceEntity(mock_coordinator, profile_data, device_data)

        device_info = entity.device_info

        # Should fall back to "Unknown Device" and "device" model_id - lines 122-123
        assert device_info["model"] == "Unknown Device"
        assert device_info["model_id"] == "device"
        assert "Cached Device" in device_info["name"]
