"""Tests for Qustodio DataUpdateCoordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.qustodio import QustodioDataUpdateCoordinator
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

    async def test_coordinator_update_success(
        self,
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

    async def test_coordinator_authentication_error(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with authentication error."""
        mock_qustodio_api.get_data.side_effect = QustodioAuthenticationError("Invalid credentials")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()

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

    async def test_coordinator_api_error(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with API error."""
        mock_qustodio_api.get_data.side_effect = QustodioAPIError("API error occurred")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="API error"):
            await coordinator._async_update_data()

    async def test_coordinator_generic_exception(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator with generic Qustodio exception."""
        mock_qustodio_api.get_data.side_effect = QustodioException("Generic error")

        coordinator = QustodioDataUpdateCoordinator(hass, mock_qustodio_api, mock_config_entry)

        with pytest.raises(UpdateFailed, match="API error"):
            await coordinator._async_update_data()

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

    async def test_coordinator_triggers_reauth_on_auth_failure(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_config_entry: Any,
    ) -> None:
        """Test coordinator triggers reauth flow on authentication failure."""
        from unittest.mock import Mock

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
