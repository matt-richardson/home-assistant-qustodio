"""Tests for Qustodio DataUpdateCoordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.qustodio.coordinator import QustodioDataUpdateCoordinator
from custom_components.qustodio.exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioException,
)


class TestQustodioDataUpdateCoordinator:
    """Tests for QustodioDataUpdateCoordinator."""

    async def test_coordinator_init(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator initialization."""
        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        assert coordinator.hass == hass
        assert coordinator.api == mock_qustodio_api
        assert coordinator.entry == mock_config_entry
        assert coordinator.name == "qustodio"

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_coordinator_update_success(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
        mock_config_entry: Any,
    ) -> None:
        """Test successful data update."""
        mock_qustodio_api.get_data.return_value = mock_profile_data

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)
        result = await coordinator._async_update_data()

        assert result == mock_profile_data
        assert "profile_1" in result
        assert "profile_2" in result
        mock_qustodio_api.get_data.assert_called_once()
        # Verify issues were dismissed on success
        assert mock_delete_issue.call_count == 6

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_authentication_error(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with authentication error."""
        mock_qustodio_api.get_data.side_effect = QustodioAuthenticationError("Invalid credentials")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()

        # Verify issue was created
        mock_create_issue.assert_called_once()

    async def test_coordinator_connection_error(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with connection error."""
        mock_qustodio_api.get_data.side_effect = QustodioConnectionError("Connection timeout")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Connection error"):
            await coordinator._async_update_data()

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_api_error(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with API error."""
        mock_qustodio_api.get_data.side_effect = QustodioAPIError("API error occurred")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="API error"):
            await coordinator._async_update_data()

        # Verify issue was created
        mock_create_issue.assert_called_once()

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_generic_exception(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with generic Qustodio exception."""
        mock_qustodio_api.get_data.side_effect = QustodioException("Generic error")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Error"):
            await coordinator._async_update_data()

        # Verify issue was created
        mock_create_issue.assert_called_once()

    async def test_coordinator_unexpected_exception(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with unexpected exception."""
        mock_qustodio_api.get_data.side_effect = ValueError("Unexpected error")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Unexpected error"):
            await coordinator._async_update_data()

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_triggers_reauth_on_auth_failure(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator triggers reauth flow on authentication failure."""
        from custom_components.qustodio.const import DOMAIN

        mock_qustodio_api.get_data.side_effect = QustodioAuthenticationError("Token expired")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # Set up hass.data with the coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

        # Mock async_get_entry and async_start_reauth
        mock_config_entry.async_start_reauth = Mock()
        hass.config_entries.async_get_entry = Mock(return_value=mock_config_entry)

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()

        # Verify reauth was triggered
        mock_config_entry.async_start_reauth.assert_called_once_with(hass)
        # Verify issue was created
        mock_create_issue.assert_called_once()

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_rate_limit_error_creates_issue(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator creates issue for rate limit errors."""
        from custom_components.qustodio.exceptions import QustodioRateLimitError

        mock_qustodio_api.get_data.side_effect = QustodioRateLimitError("Rate limit exceeded")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Rate limit exceeded"):
            await coordinator._async_update_data()

        # Verify issue was created with correct parameters
        mock_create_issue.assert_called_once()
        call_args = mock_create_issue.call_args
        # Check positional arguments (hass, domain, issue_id)
        assert call_args[0][2] == "rate_limit_error"
        # Check keyword arguments
        assert call_args[1]["translation_key"] == "rate_limit_error"

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_connection_error_threshold(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator only creates issue after 3 consecutive connection failures."""
        mock_qustodio_api.get_data.side_effect = QustodioConnectionError("Connection timeout")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # First two failures should not create issue
        for _ in range(2):
            with pytest.raises(UpdateFailed, match="Connection error"):
                await coordinator._async_update_data()

        assert mock_create_issue.call_count == 0

        # Third failure should create issue
        with pytest.raises(UpdateFailed, match="Connection error"):
            await coordinator._async_update_data()

        mock_create_issue.assert_called_once()
        assert coordinator.statistics["consecutive_failures"] == 3

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_data_error_threshold(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator only creates issue after 2 consecutive data errors."""
        from custom_components.qustodio.exceptions import QustodioDataError

        mock_qustodio_api.get_data.side_effect = QustodioDataError("Invalid data format")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # First failure should not create issue
        with pytest.raises(UpdateFailed, match="Data error"):
            await coordinator._async_update_data()

        assert mock_create_issue.call_count == 0

        # Second failure should create issue
        with pytest.raises(UpdateFailed, match="Data error"):
            await coordinator._async_update_data()

        mock_create_issue.assert_called_once()
        assert coordinator.statistics["consecutive_failures"] == 2

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_unexpected_error_threshold(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator only creates issue after 2 consecutive unexpected errors."""
        mock_qustodio_api.get_data.side_effect = ValueError("Unexpected error")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # First failure should not create issue
        with pytest.raises(UpdateFailed, match="Unexpected error"):
            await coordinator._async_update_data()

        assert mock_create_issue.call_count == 0

        # Second failure should create issue
        with pytest.raises(UpdateFailed, match="Unexpected error"):
            await coordinator._async_update_data()

        mock_create_issue.assert_called_once()
        assert coordinator.statistics["consecutive_failures"] == 2

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_dismisses_issues_on_success(
        self,
        mock_create_issue: Mock,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator dismisses all issues on successful update."""
        # First fail to create an issue
        mock_qustodio_api.get_data.side_effect = QustodioAPIError("API error")
        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        mock_create_issue.assert_called_once()

        # Then succeed
        mock_qustodio_api.get_data.side_effect = None
        mock_qustodio_api.get_data.return_value = mock_profile_data

        await coordinator._async_update_data()

        # Verify all issues were dismissed
        assert mock_delete_issue.call_count == 6
        dismissed_issues = [call[0][2] for call in mock_delete_issue.call_args_list]
        assert "authentication_error" in dismissed_issues
        assert "connection_error" in dismissed_issues
        assert "rate_limit_error" in dismissed_issues
        assert "api_error" in dismissed_issues
        assert "data_error" in dismissed_issues
        assert "unexpected_error" in dismissed_issues

    @patch("custom_components.qustodio.coordinator.ir.async_create_issue")
    async def test_coordinator_tracks_error_statistics(
        self,
        mock_create_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator tracks error statistics correctly."""
        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # Trigger different error types
        mock_qustodio_api.get_data.side_effect = QustodioAuthenticationError("Auth error")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        mock_qustodio_api.get_data.side_effect = QustodioConnectionError("Connection error")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        mock_qustodio_api.get_data.side_effect = QustodioAPIError("API error")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        # Verify statistics
        assert coordinator.statistics["total_updates"] == 3
        assert coordinator.statistics["failed_updates"] == 3
        assert coordinator.statistics["consecutive_failures"] == 3
        assert coordinator.statistics["error_counts"]["QustodioAuthenticationError"] == 1
        assert coordinator.statistics["error_counts"]["QustodioConnectionError"] == 1
        assert coordinator.statistics["error_counts"]["QustodioAPIError"] == 1

    async def test_get_app_usage_cache_seconds_default(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _get_app_usage_cache_seconds returns default value."""
        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # Default is 60 minutes = 3600 seconds
        assert coordinator._app_usage_cache_seconds == 3600

    async def test_get_app_usage_cache_seconds_custom(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _get_app_usage_cache_seconds returns custom value from options."""
        from custom_components.qustodio.const import CONF_APP_USAGE_CACHE_INTERVAL

        # Set custom cache interval in options
        mock_config_entry.options = {CONF_APP_USAGE_CACHE_INTERVAL: 30}  # 30 minutes

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # 30 minutes = 1800 seconds
        assert coordinator._app_usage_cache_seconds == 1800

    async def test_get_app_usage_cache_seconds_minimum(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _get_app_usage_cache_seconds with minimum value."""
        from custom_components.qustodio.const import CONF_APP_USAGE_CACHE_INTERVAL

        # Set minimum cache interval (5 minutes)
        mock_config_entry.options = {CONF_APP_USAGE_CACHE_INTERVAL: 5}

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # 5 minutes = 300 seconds
        assert coordinator._app_usage_cache_seconds == 300

    async def test_get_app_usage_cache_seconds_maximum(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _get_app_usage_cache_seconds with maximum value."""
        from custom_components.qustodio.const import CONF_APP_USAGE_CACHE_INTERVAL

        # Set maximum cache interval (1440 minutes = 24 hours)
        mock_config_entry.options = {CONF_APP_USAGE_CACHE_INTERVAL: 1440}

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # 1440 minutes = 86400 seconds
        assert coordinator._app_usage_cache_seconds == 86400

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_with_coordinator_data(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage is called and fetches data."""
        from datetime import date
        from unittest.mock import patch

        from custom_components.qustodio.models import CoordinatorData, ProfileData

        # Create CoordinatorData with profiles
        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        coordinator_data = CoordinatorData(profiles={"profile_1": profile1}, devices={}, app_usage=None)

        # Mock the API responses
        mock_qustodio_api.get_data.return_value = coordinator_data
        mock_qustodio_api.get_app_usage.return_value = {
            "items": [
                {"app_name": "YouTube", "exe": "com.youtube", "minutes": 45.0, "platform": 3, "questionable": True},
                {"app_name": "Chrome", "exe": "com.chrome", "minutes": 30.0, "platform": 3, "questionable": False},
            ],
            "questionable_count": 1,
        }

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # Patch datetime to control "now"
        with patch("custom_components.qustodio.coordinator.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.date.return_value = date(2025, 12, 2)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: date(*args, **kwargs) if args else mock_now

            # Execute update
            result = await coordinator._async_update_data()

        # Verify app usage was fetched
        assert mock_qustodio_api.get_app_usage.called
        assert result.app_usage is not None
        assert "profile_1" in result.app_usage
        assert len(result.app_usage["profile_1"]) == 2
        assert result.app_usage["profile_1"][0].name == "YouTube"
        assert result.app_usage["profile_1"][0].minutes == 45.0

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_uses_cache(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage uses cached data when within cache interval."""
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        # Create CoordinatorData
        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        coordinator_data = CoordinatorData(profiles={"profile_1": profile1}, devices={}, app_usage=None)

        mock_qustodio_api.get_data.return_value = coordinator_data
        mock_qustodio_api.get_app_usage.return_value = {"items": [], "questionable_count": 0}

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # First update - should fetch
        await coordinator._async_update_data()
        first_call_count = mock_qustodio_api.get_app_usage.call_count

        # Second update immediately after (within cache window) - should use cache
        await coordinator._async_update_data()
        second_call_count = mock_qustodio_api.get_app_usage.call_count

        # Should not have called API again
        assert second_call_count == first_call_count

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_refreshes_after_cache_expires(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage refreshes data after cache expires."""
        from datetime import datetime, timezone
        from unittest.mock import patch

        from custom_components.qustodio.const import CONF_APP_USAGE_CACHE_INTERVAL
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        # Set short cache interval (5 minutes)
        mock_config_entry.options = {CONF_APP_USAGE_CACHE_INTERVAL: 5}

        # Create CoordinatorData
        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        coordinator_data = CoordinatorData(profiles={"profile_1": profile1}, devices={}, app_usage=None)

        mock_qustodio_api.get_data.return_value = coordinator_data
        mock_qustodio_api.get_app_usage.return_value = {"items": [], "questionable_count": 0}

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # First update
        with patch("custom_components.qustodio.coordinator.datetime") as mock_datetime:
            mock_now = datetime(2025, 12, 2, 10, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            await coordinator._async_update_data()
            first_call_count = mock_qustodio_api.get_app_usage.call_count

        # Second update 6 minutes later (cache expired)
        with patch("custom_components.qustodio.coordinator.datetime") as mock_datetime:
            mock_now = datetime(2025, 12, 2, 10, 6, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            await coordinator._async_update_data()
            second_call_count = mock_qustodio_api.get_app_usage.call_count

        # Should have called API again after cache expired
        assert second_call_count > first_call_count

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_handles_profile_error_gracefully(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage continues when one profile fails."""
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        # Create CoordinatorData with two profiles
        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        profile2 = ProfileData(
            id="profile_2",
            uid="uid2",
            name="Child Two",
            device_count=1,
            device_ids=[2],
            raw_data={"id": 2, "uid": "uid2", "name": "Child Two"},
        )
        coordinator_data = CoordinatorData(
            profiles={"profile_1": profile1, "profile_2": profile2}, devices={}, app_usage=None
        )

        mock_qustodio_api.get_data.return_value = coordinator_data
        # First profile fails, second succeeds
        mock_qustodio_api.get_app_usage.side_effect = [
            Exception("API Error for profile 1"),
            {"items": [{"app_name": "App", "exe": "app", "minutes": 10.0, "platform": 3, "questionable": False}]},
        ]

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        # Execute - should not raise exception
        result = await coordinator._async_update_data()

        # Verify we got data for profile_2 despite profile_1 failing
        assert result.app_usage is not None
        assert "profile_1" in result.app_usage
        assert result.app_usage["profile_1"] == []  # Empty due to error
        assert "profile_2" in result.app_usage
        assert len(result.app_usage["profile_2"]) == 1

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_exception_with_cache(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage uses cached data when fetching fails."""
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        coordinator_data = CoordinatorData(profiles={"profile_1": profile1}, devices={}, app_usage=None)

        mock_qustodio_api.get_data.return_value = coordinator_data

        # First update - successful fetch
        mock_qustodio_api.get_app_usage.return_value = {
            "items": [
                {"app_name": "YouTube", "exe": "com.youtube", "minutes": 45.0, "platform": 3, "questionable": True}
            ]
        }

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)
        result1 = await coordinator._async_update_data()

        # Verify first fetch succeeded
        assert result1.app_usage is not None
        assert "profile_1" in result1.app_usage
        assert len(result1.app_usage["profile_1"]) == 1

        # Second update - fetch fails, should use cache
        mock_qustodio_api.get_app_usage.side_effect = Exception("API Error")
        result2 = await coordinator._async_update_data()

        # Should still have app usage from cache
        assert result2.app_usage is not None
        assert "profile_1" in result2.app_usage
        assert len(result2.app_usage["profile_1"]) == 1
        assert result2.app_usage["profile_1"][0].name == "YouTube"

    @patch("custom_components.qustodio.coordinator.ir.async_delete_issue")
    async def test_fetch_app_usage_exception_without_cache(
        self,
        mock_delete_issue: Mock,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test _fetch_app_usage sets empty list per profile when fetching fails without cache."""
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        profile1 = ProfileData(
            id="profile_1",
            uid="uid1",
            name="Child One",
            device_count=1,
            device_ids=[1],
            raw_data={"id": 1, "uid": "uid1", "name": "Child One"},
        )
        coordinator_data = CoordinatorData(profiles={"profile_1": profile1}, devices={}, app_usage=None)

        mock_qustodio_api.get_data.return_value = coordinator_data
        # First fetch fails immediately
        mock_qustodio_api.get_app_usage.side_effect = Exception("API Error")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)
        result = await coordinator._async_update_data()

        # Should have empty list for profile (per-profile exception handling)
        assert result.app_usage is not None
        assert "profile_1" in result.app_usage
        assert result.app_usage["profile_1"] == []
