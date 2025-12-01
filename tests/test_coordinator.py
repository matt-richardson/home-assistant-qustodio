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
