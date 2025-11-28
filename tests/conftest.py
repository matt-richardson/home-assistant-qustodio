"""Shared fixtures for Qustodio tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.qustodio.const import DOMAIN
from custom_components.qustodio.models import CoordinatorData, DeviceData, ProfileData, UserStatus


@pytest.fixture
def mock_config_entry() -> Mock:
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.version = 1
    entry.minor_version = 1
    entry.domain = DOMAIN
    entry.title = "Qustodio (test@example.com)"
    entry.data = {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test_password",
        "profiles": {
            "profile_1": {
                "id": "profile_1",
                "uid": "uid_1",
                "name": "Child One",
            },
            "profile_2": {
                "id": "profile_2",
                "uid": "uid_2",
                "name": "Child Two",
            },
        },
    }
    entry.source = "user"
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test@example.com"
    entry.options = {}
    entry.discovery_keys = {}
    entry.subentries_data = []
    return entry


@pytest.fixture
def mock_profile_data() -> dict[str, Any]:
    """Create mock profile data."""
    return {
        "profile_1": {
            "id": "profile_1",
            "uid": "uid_1",
            "name": "Child One",
            "is_online": True,
            "unauthorized_remove": False,
            "device_tampered": None,
            "current_device": "iPhone 12",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10,
            "lastseen": "2025-11-23T10:30:00Z",
            "quota": 120,
            "time": 45.5,
        },
        "profile_2": {
            "id": "profile_2",
            "uid": "uid_2",
            "name": "Child Two",
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
        },
    }


@pytest.fixture
def mock_api_login_response() -> dict[str, Any]:
    """Create mock API login response."""
    return {
        "access_token": "test_access_token_12345",
        "expires_in": 3600,
        "token_type": "bearer",
        "refresh_token": "test_refresh_token_12345",
    }


@pytest.fixture
def mock_api_account_response() -> dict[str, Any]:
    """Create mock API account response."""
    return {
        "id": "account_123",
        "uid": "account_uid_456",
        "email": "test@example.com",
        "name": "Test Account",
    }


@pytest.fixture
def mock_api_profiles_response() -> list[dict[str, Any]]:
    """Create mock API profiles response."""
    return [
        {
            "id": "profile_1",
            "uid": "uid_1",
            "name": "Child One",
            "device_ids": ["device_1"],
            "status": {
                "is_online": True,
                "lastseen": "2025-11-23T10:30:00Z",
                "location": {
                    "device": "device_1",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "accuracy": 10,
                },
            },
        },
        {
            "id": "profile_2",
            "uid": "uid_2",
            "name": "Child Two",
            "device_ids": ["device_2"],
            "status": {
                "is_online": False,
                "lastseen": "2025-11-23T09:15:00Z",
                "location": {},
            },
        },
    ]


@pytest.fixture
def mock_api_devices_response() -> list[dict[str, Any]]:
    """Create mock API devices response."""
    return [
        {
            "id": "device_1",
            "name": "iPhone 12",
            "platform": "ios",
            "alerts": {
                "unauthorized_remove": False,
            },
        },
        {
            "id": "device_2",
            "name": "Android Phone",
            "platform": "android",
            "alerts": {
                "unauthorized_remove": False,
            },
        },
    ]


@pytest.fixture
def mock_api_rules_response() -> dict[str, Any]:
    """Create mock API rules response."""
    return {
        "time_restrictions": {
            "quotas": {
                "mon": 120,
                "tue": 120,
                "wed": 120,
                "thu": 120,
                "fri": 120,
                "sat": 180,
                "sun": 180,
            },
        },
    }


@pytest.fixture
def mock_api_hourly_summary_response() -> list[dict[str, Any]]:
    """Create mock API hourly summary response."""
    return [
        {"hour": 9, "screen_time_seconds": 1800},
        {"hour": 10, "screen_time_seconds": 900},
    ]


@pytest.fixture
def mock_qustodio_api() -> AsyncMock:
    """Create a mock QustodioApi instance."""
    api = AsyncMock()
    api.login = AsyncMock(return_value="LOGIN_RESULT_OK")
    api.get_data = AsyncMock(
        return_value={
            "profile_1": {
                "id": "profile_1",
                "uid": "uid_1",
                "name": "Child One",
                "is_online": True,
                "unauthorized_remove": False,
                "device_tampered": None,
                "current_device": "iPhone 12",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "accuracy": 10,
                "lastseen": "2025-11-23T10:30:00Z",
                "quota": 120,
                "time": 45.5,
            },
        }
    )
    return api


@pytest.fixture
def mock_coordinator(mock_qustodio_api: AsyncMock, hass: HomeAssistant) -> Mock:
    """Create a mock DataUpdateCoordinator."""
    coordinator = Mock()
    coordinator.hass = hass
    coordinator.api = mock_qustodio_api

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
        "protection_disabled": True,
        "panic_button_active": True,
        "navigation_locked": True,
        "questionable_events_count": 3,
        "location_tracking_enabled": True,
        "browser_locked": True,
        "vpn_disabled": True,
        "computer_locked": True,
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
        "protection_disabled": False,
        "panic_button_active": False,
        "navigation_locked": False,
        "questionable_events_count": 0,
        "location_tracking_enabled": False,
        "browser_locked": False,
        "vpn_disabled": False,
        "computer_locked": False,
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
    coordinator.data = CoordinatorData(
        profiles={
            "profile_1": ProfileData.from_api_response(profile1_raw),
            "profile_2": ProfileData.from_api_response(profile2_raw),
        },
        devices={
            "device_1": device1,
            "device_2": device2,
        },
    )

    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()

    # Add statistics tracking
    coordinator.statistics = {
        "total_updates": 10,
        "successful_updates": 9,
        "failed_updates": 1,
        "last_update_time": "2025-11-28T12:00:00+00:00",
        "last_success_time": "2025-11-28T12:00:00+00:00",
        "last_failure_time": "2025-11-28T11:00:00+00:00",
        "consecutive_failures": 0,
        "error_counts": {"QustodioConnectionError": 1},
    }

    return coordinator


@pytest.fixture
def hass() -> HomeAssistant:
    """Create a Home Assistant instance for testing."""
    hass_instance = Mock(spec=HomeAssistant)
    hass_instance.data = {}
    hass_instance.config_entries = Mock()
    hass_instance.config_entries.async_forward_entry_setups = AsyncMock()
    hass_instance.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass_instance.config_entries.flow = Mock()
    hass_instance.config_entries.flow.async_init = AsyncMock()
    return hass_instance


@pytest.fixture
def mock_aiohttp_session() -> Mock:
    """Create a mock aiohttp ClientSession."""
    session = Mock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_aiohttp_response() -> Mock:
    """Create a mock aiohttp ClientResponse."""
    response = Mock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    response.status = 200
    response.json = AsyncMock()
    response.text = AsyncMock(return_value="")
    return response
