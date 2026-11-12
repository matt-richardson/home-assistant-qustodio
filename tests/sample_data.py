"""Sample Qustodio data shared by mocked and real Home Assistant tests."""

from __future__ import annotations

from custom_components.qustodio.models import CoordinatorData, DeviceData, ProfileData, UserStatus


def build_coordinator_data() -> CoordinatorData:
    """Build the sample Qustodio data (2 profiles, 2 devices) shared by mocked and real-HA tests."""
    # Create ProfileData objects
    profile1_raw = {
        "id": "profile_1",
        "uid": "uid_1",
        "name": "Child One",
        "device_count": 1,
        "device_ids": ["device_1"],
        "is_online": True,
        "unauthorized_remove": True,
        "device_tampered": None,
        "current_device": "iPhone 12",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "accuracy": 10,
        "lastseen": "2025-11-23T10:30:00Z",
        "quota": 300,
        "time": 120,
        "pause_internet_ends_at": "2025-11-23T12:00:00Z",
        "panic_button_enabled": True,
        "is_lock_navigation": True,
        "questionable_events_count": 3,
        "location_tracking_enabled": True,
        "is_lock_computer": True,
    }

    profile2_raw = {
        "id": "profile_2",
        "uid": "uid_2",
        "name": "Child Two",
        "device_count": 1,
        "device_ids": ["device_2"],
        "is_online": False,
        "unauthorized_remove": False,
        "device_tampered": None,
        "current_device": None,
        "latitude": None,
        "longitude": None,
        "accuracy": 0,
        "lastseen": "2025-11-23T09:15:00Z",
        "quota": 60,
        "time": 70.2,
        "pause_internet_ends_at": None,
        "panic_button_enabled": False,
        "is_lock_navigation": False,
        "questionable_events_count": 0,
        "location_tracking_enabled": False,
        "is_lock_computer": False,
    }

    # Create DeviceData objects
    device1 = DeviceData(
        id="device_1",
        uid="uid_device_1",
        name="iPhone 12",
        type="MOBILE",
        platform=4,  # iOS
        version="182.14.0",
        enabled=1,
        location_latitude=37.7749,
        location_longitude=-122.4194,
        location_time="2025-11-23T10:30:00Z",
        location_accuracy=10.0,
        users=[
            UserStatus(
                profile_id=int("profile_1".split("_")[1]),
                is_online=True,
                lastseen="2025-11-23T10:30:00Z",
                status={
                    "vpn_disable": {"status": False},
                    "browser_lock": {"status": False},
                    "panic_button": {"status": False},
                    "disable_protection": {"status": False, "time": None},
                },
            )
        ],
        mdm={"unauthorized_remove": False},
        alerts={"unauthorized_remove": False},
        lastseen="2025-11-23T10:30:00Z",
    )

    device2 = DeviceData(
        id="device_2",
        uid="uid_device_2",
        name="Android Phone",
        type="MOBILE",
        platform=3,  # Android
        version="182.14.0",
        enabled=1,
        location_latitude=None,
        location_longitude=None,
        location_time=None,
        location_accuracy=None,
        users=[
            UserStatus(
                profile_id=int("profile_2".split("_")[1]),
                is_online=False,
                lastseen="2025-11-23T09:15:00Z",
                status={},
            )
        ],
        mdm={},
        alerts={},
        lastseen="2025-11-23T09:15:00Z",
    )

    # Create CoordinatorData
    return CoordinatorData(
        profiles={
            "profile_1": ProfileData.from_api_response(profile1_raw),
            "profile_2": ProfileData.from_api_response(profile2_raw),
        },
        devices={
            "device_1": device1,
            "device_2": device2,
        },
    )
