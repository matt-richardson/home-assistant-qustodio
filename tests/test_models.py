"""Tests for Qustodio models module."""

from __future__ import annotations

from custom_components.qustodio.models import AppUsage, CoordinatorData, DeviceData, ProfileData, UserStatus


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


class TestAppUsage:
    """Tests for AppUsage model."""

    def test_from_api_response_with_all_fields(self) -> None:
        """Test AppUsage.from_api_response with all fields present."""
        api_data = {
            "app_name": "Clash Royale",
            "exe": "com.supercell.scroll",
            "minutes": 11.5,
            "platform": 4,
            "thumbnail": "https://static.qustodio.com/app/icon.jpg",
            "questionable": False,
        }

        app = AppUsage.from_api_response(api_data)

        assert app.name == "Clash Royale"
        assert app.package == "com.supercell.scroll"
        assert app.minutes == 11.5
        assert app.platform == 4
        assert app.thumbnail == "https://static.qustodio.com/app/icon.jpg"
        assert app.questionable is False

    def test_from_api_response_with_missing_optional_fields(self) -> None:
        """Test AppUsage.from_api_response with missing optional fields."""
        api_data = {
            "app_name": "Unknown App",
            "exe": "com.example.app",
            "minutes": 5.0,
            "platform": 1,
        }

        app = AppUsage.from_api_response(api_data)

        assert app.name == "Unknown App"
        assert app.package == "com.example.app"
        assert app.minutes == 5.0
        assert app.platform == 1
        assert app.thumbnail is None  # Default
        assert app.questionable is False  # Default

    def test_from_api_response_with_defaults(self) -> None:
        """Test AppUsage.from_api_response uses defaults for missing required fields."""
        api_data = {}

        app = AppUsage.from_api_response(api_data)

        assert app.name == "Unknown"  # Default
        assert app.package == ""  # Default
        assert app.minutes == 0.0  # Default
        assert app.platform == 0  # Default
        assert app.thumbnail is None
        assert app.questionable is False

    def test_from_api_response_with_questionable_app(self) -> None:
        """Test AppUsage.from_api_response with questionable flag."""
        api_data = {
            "app_name": "Questionable App",
            "exe": "com.questionable.app",
            "minutes": 30.0,
            "platform": 1,
            "questionable": True,
        }

        app = AppUsage.from_api_response(api_data)

        assert app.questionable is True


class TestCoordinatorDataGetAppUsage:
    """Tests for CoordinatorData.get_app_usage() method."""

    def test_get_app_usage_with_data(self) -> None:
        """Test get_app_usage returns app list when data exists."""
        profile_data = ProfileData(
            id="123",
            uid="uid_123",
            name="Test Profile",
            device_count=0,
            device_ids=[],
            raw_data={},
        )

        app1 = AppUsage(name="App1", package="com.app1", minutes=10.0, platform=1)
        app2 = AppUsage(name="App2", package="com.app2", minutes=5.0, platform=4)

        data = CoordinatorData(
            profiles={"123": profile_data},
            devices={},
            app_usage={"123": [app1, app2]},
        )

        apps = data.get_app_usage("123")

        assert len(apps) == 2
        assert apps[0] == app1
        assert apps[1] == app2

    def test_get_app_usage_with_no_app_usage_data(self) -> None:
        """Test get_app_usage returns empty list when app_usage is None."""
        profile_data = ProfileData(
            id="123",
            uid="uid_123",
            name="Test Profile",
            device_count=0,
            device_ids=[],
            raw_data={},
        )

        data = CoordinatorData(
            profiles={"123": profile_data},
            devices={},
            app_usage=None,
        )

        apps = data.get_app_usage("123")

        assert apps == []

    def test_get_app_usage_with_nonexistent_profile(self) -> None:
        """Test get_app_usage returns empty list for non-existent profile."""
        profile_data = ProfileData(
            id="123",
            uid="uid_123",
            name="Test Profile",
            device_count=0,
            device_ids=[],
            raw_data={},
        )

        app1 = AppUsage(name="App1", package="com.app1", minutes=10.0, platform=1)

        data = CoordinatorData(
            profiles={"123": profile_data},
            devices={},
            app_usage={"123": [app1]},
        )

        apps = data.get_app_usage("999")  # Non-existent profile

        assert apps == []

    def test_get_app_usage_with_empty_app_list(self) -> None:
        """Test get_app_usage returns empty list when profile has no apps."""
        profile_data = ProfileData(
            id="123",
            uid="uid_123",
            name="Test Profile",
            device_count=0,
            device_ids=[],
            raw_data={},
        )

        data = CoordinatorData(
            profiles={"123": profile_data},
            devices={},
            app_usage={"123": []},  # Empty list
        )

        apps = data.get_app_usage("123")

        assert apps == []

    def test_get_profile_devices_profile_not_found(self) -> None:
        """Test get_profile_devices returns empty list when profile not found."""
        profile_data = ProfileData(
            id="123",
            uid="uid123",
            name="Test Profile",
            device_count=1,
            device_ids=[1],
            raw_data={},
        )

        data = CoordinatorData(
            profiles={"123": profile_data},
            devices={},
        )

        # Request devices for non-existent profile
        devices = data.get_profile_devices("nonexistent_profile")

        assert devices == []
