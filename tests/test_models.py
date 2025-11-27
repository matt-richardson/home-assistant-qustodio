"""Tests for Qustodio models module."""

from __future__ import annotations

from custom_components.qustodio.models import DeviceData, ProfileData, UserStatus


class TestDeviceDataGetUserStatus:
    """Tests for DeviceData.get_user_status() method - covers lines 70-90 in models.py."""

    def test_get_user_status_with_int_profile_id(self) -> None:
        """Test get_user_status with integer profile ID."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=123,
                    is_online=True,
                    lastseen="2025-11-23T10:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T10:00:00Z",
        )

        # Test with int profile_id - line 76
        result = device.get_user_status(123)
        assert result is not None
        assert result.profile_id == 123
        assert result.is_online is True

    def test_get_user_status_with_string_profile_id(self) -> None:
        """Test get_user_status with string profile ID."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=456,
                    is_online=False,
                    lastseen="2025-11-23T09:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T09:00:00Z",
        )

        # Test with string profile_id (plain number) - line 81
        result = device.get_user_status("456")
        assert result is not None
        assert result.profile_id == 456
        assert result.is_online is False

    def test_get_user_status_with_profile_prefix(self) -> None:
        """Test get_user_status with 'profile_' prefix in string."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=789,
                    is_online=True,
                    lastseen="2025-11-23T10:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T10:00:00Z",
        )

        # Test with "profile_" prefix - line 79
        result = device.get_user_status("profile_789")
        assert result is not None
        assert result.profile_id == 789

    def test_get_user_status_with_invalid_type(self) -> None:
        """Test get_user_status with invalid type returns None."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=123,
                    is_online=True,
                    lastseen="2025-11-23T10:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T10:00:00Z",
        )

        # Test with invalid type (list) - line 83
        result = device.get_user_status([123])  # type: ignore[arg-type]
        assert result is None

        # Test with invalid type (dict) - line 83
        result = device.get_user_status({"id": 123})  # type: ignore[arg-type]
        assert result is None

    def test_get_user_status_with_malformed_string(self) -> None:
        """Test get_user_status with malformed string returns None."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=123,
                    is_online=True,
                    lastseen="2025-11-23T10:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T10:00:00Z",
        )

        # Test with non-numeric string - line 85 (ValueError)
        result = device.get_user_status("not_a_number")
        assert result is None

        # Test with malformed profile_ string - line 85 (IndexError)
        result = device.get_user_status("profile_")
        assert result is None

        # Test with profile_ but non-numeric - line 85 (ValueError)
        result = device.get_user_status("profile_abc")
        assert result is None

    def test_get_user_status_profile_not_found(self) -> None:
        """Test get_user_status returns None when profile not in users list."""
        device = DeviceData(
            id="device_1",
            uid="uid_1",
            name="iPhone",
            type="MOBILE",
            platform=4,
            version="1.0",
            enabled=1,
            location_latitude=37.0,
            location_longitude=-122.0,
            location_time="2025-11-23T10:00:00Z",
            location_accuracy=10.0,
            users=[
                UserStatus(
                    profile_id=123,
                    is_online=True,
                    lastseen="2025-11-23T10:00:00Z",
                    status={},
                )
            ],
            mdm={},
            alerts={},
            lastseen="2025-11-23T10:00:00Z",
        )

        # Test with profile ID not in users list - line 90
        result = device.get_user_status(999)
        assert result is None

        result = device.get_user_status("999")
        assert result is None


class TestProfileDataFromApiResponse:
    """Tests for ProfileData.from_api_response() factory method."""

    def test_from_api_response_with_all_fields(self) -> None:
        """Test creating ProfileData from complete API response."""
        api_data = {
            "id": 12345,
            "uid": "uid_12345",
            "name": "Test Child",
            "is_online": True,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "lastseen": "2025-11-23T10:00:00Z",
            "quota": 120,
            "time": 45.5,
            "device_count": 2,
            "device_ids": [111, 222],
            "current_device": "iPhone",
            "unauthorized_remove": True,
            "device_tampered": False,
        }

        profile = ProfileData.from_api_response(api_data)

        assert profile.id == "12345"
        assert profile.uid == "uid_12345"
        assert profile.name == "Test Child"
        assert profile.device_count == 2
        assert profile.device_ids == [111, 222]
        assert profile.raw_data == api_data
        # Check that raw_data contains all fields
        assert profile.raw_data["is_online"] is True
        assert profile.raw_data["latitude"] == 37.7749

    def test_from_api_response_with_missing_optional_fields(self) -> None:
        """Test creating ProfileData with only required fields."""
        api_data = {
            "id": 67890,
            "uid": "uid_67890",
            "name": "Minimal Child",
        }

        profile = ProfileData.from_api_response(api_data)

        assert profile.id == "67890"
        assert profile.uid == "uid_67890"
        assert profile.name == "Minimal Child"
        assert profile.device_count == 0  # Default
        assert profile.device_ids == []  # Default
        assert profile.raw_data == api_data
