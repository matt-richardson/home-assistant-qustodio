"""Shared fixtures for Qustodio tests."""

from __future__ import annotations

import inspect
from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.qustodio.const import DOMAIN

from .sample_data import build_coordinator_data


def create_config_entry_with_version_compat(**kwargs):
    """Create a ConfigEntry with version-compatible parameters.

    Home Assistant versions have different required/optional parameters:
    - 2025.x: requires 'subentries_data', has 'discovery_keys'
    - Older: doesn't have 'subentries_data' or 'discovery_keys'

    This helper detects which parameters are supported and adjusts accordingly.

    Args:
        **kwargs: Parameters to pass to ConfigEntry constructor

    Returns:
        ConfigEntry instance with version-compatible parameters
    """
    # Check if ConfigEntry.__init__ accepts parameters
    sig = inspect.signature(ConfigEntry.__init__)
    params = sig.parameters

    # Handle subentries_data (required in 2025.x, doesn't exist in older)
    if "subentries_data" in params:
        # HA 2025.x and newer - subentries_data is required
        if "subentries_data" not in kwargs:
            kwargs["subentries_data"] = {}
    else:
        # Older HA versions - subentries_data doesn't exist
        kwargs.pop("subentries_data", None)

    # Handle discovery_keys (exists in newer versions, not in older)
    if "discovery_keys" not in params:
        # Older HA versions don't have discovery_keys parameter
        kwargs.pop("discovery_keys", None)

    return ConfigEntry(**kwargs)


@pytest.fixture
def mock_config_entry() -> Mock:
    """Create a mock config entry.

    Note: This returns a Mock for backward compatibility with existing tests.
    For new tests that need a real ConfigEntry, use create_config_entry_with_version_compat().
    """
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
    # Modern HA (2025.12+) reads entry.update_listeners in
    # async_update_reload_and_abort; an empty list is a safe no-op on all versions.
    entry.update_listeners = []
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
                "questionable_events": {"count": 3, "start_date": None, "end_date": None},
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
                "questionable_events": {"count": 0, "start_date": None, "end_date": None},
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
                "thr": 120,
                "fri": 120,
                "sat": 180,
                "sun": 180,
            },
            "is_lock_computer": True,
            "is_lock_navigation": True,
            "pause_internet": {"ends_at": None},
            "time_ranges": {
                "mon": 12583167,
                "tue": 12583039,
                "wed": 12583039,
                "thr": 12583039,
                "fri": 12583039,
                "sat": 12583039,
                "sun": 12583167,
            },
        },
        "location": {"enabled": True, "location_update_frequency": 3600},
        "panic": {"mode": 1},
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
def mock_coordinator(mock_qustodio_api: AsyncMock, mock_hass: HomeAssistant) -> Mock:
    """Create a mock DataUpdateCoordinator."""
    coordinator = Mock()
    coordinator.hass = mock_hass
    coordinator.api = mock_qustodio_api
    coordinator.entry = Mock(entry_id="test_entry_id")

    coordinator.data = build_coordinator_data()

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
def mock_hass() -> HomeAssistant:
    """Create a Home Assistant instance for testing.

    Note: This returns a Mock for fast unit tests.
    For integration tests that need a real HA instance, use hass_instance fixture.

    Modern Home Assistant (2025.12+, used on Python >=3.13) calls
    ``frame.report_usage`` during ``DataUpdateCoordinator.__init__`` (the
    "pass the config entry explicitly" deprecation), which raises
    "Frame helper not set up" against a bare Mock hass. Patch it out for the
    duration of the test; the patch is a no-op on older HA that lacks it.
    """
    import homeassistant.helpers.frame as frame_module  # pylint: disable=import-outside-toplevel

    frame_patches = []
    if hasattr(frame_module, "report_usage"):
        frame_patches.append(patch("homeassistant.helpers.frame.report_usage"))

    with ExitStack() as stack:
        for frame_patch in frame_patches:
            stack.enter_context(frame_patch)

        hass_instance = Mock(spec=HomeAssistant)
        hass_instance.data = {}

        # Device entities resolve their parent profile device through
        # dr.async_get_device_id_by_identifier() to populate `via_device_id`.
        # Individual tests patch this when they assert on the resulting link.
        hass_instance.data[dr.DATA_REGISTRY] = Mock()
        # The coordinator syncs device names after each update; start with no devices.
        hass_instance.data[dr.DATA_REGISTRY]._devices.get_devices_for_config_entry_id.return_value = []

        hass_instance.config_entries = Mock()
        hass_instance.config_entries.async_forward_entry_setups = AsyncMock()
        hass_instance.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass_instance.config_entries.flow = Mock()
        hass_instance.config_entries.flow.async_init = AsyncMock()
        hass_instance.services = MagicMock()
        yield hass_instance


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
