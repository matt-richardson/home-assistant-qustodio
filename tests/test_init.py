"""Tests for Qustodio __init__.py."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.qustodio import (
    QustodioDataUpdateCoordinator,
    async_setup_entry,
    async_unload_entry,
    is_profile_available,
    setup_profile_entities,
)
from custom_components.qustodio.const import DOMAIN


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
    ) -> None:
        """Test successful setup of config entry."""
        with (
            patch("custom_components.qustodio.QustodioApi", return_value=mock_qustodio_api),
            patch(
                "custom_components.qustodio.QustodioDataUpdateCoordinator.async_config_entry_first_refresh",
                new_callable=AsyncMock,
            ),
        ):
            mock_qustodio_api.get_data.return_value = mock_profile_data

            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]
            assert isinstance(hass.data[DOMAIN][mock_config_entry.entry_id], QustodioDataUpdateCoordinator)
            hass.config_entries.async_forward_entry_setups.assert_called_once()

    async def test_setup_entry_with_existing_domain_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
    ) -> None:
        """Test setup when DOMAIN data already exists."""
        # Pre-populate hass.data with DOMAIN
        hass.data[DOMAIN] = {"other_entry": "some_data"}

        with (
            patch("custom_components.qustodio.QustodioApi", return_value=mock_qustodio_api),
            patch(
                "custom_components.qustodio.QustodioDataUpdateCoordinator.async_config_entry_first_refresh",
                new_callable=AsyncMock,
            ),
        ):
            mock_qustodio_api.get_data.return_value = mock_profile_data

            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]
            assert "other_entry" in hass.data[DOMAIN]


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_unload_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
    ) -> None:
        """Test successful unload of config entry."""
        # Setup coordinator with mock API
        mock_api = AsyncMock()
        mock_api.close = AsyncMock()
        mock_coordinator = Mock()
        mock_coordinator.api = mock_api

        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
        hass.config_entries.async_unload_platforms.assert_called_once()
        mock_api.close.assert_called_once()

    async def test_unload_entry_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
    ) -> None:
        """Test unload failure keeps data."""
        # Setup existing coordinator in hass.data
        hass.data[DOMAIN] = {mock_config_entry.entry_id: Mock()}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is False
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        hass.config_entries.async_unload_platforms.assert_called_once()

    async def test_unload_entry_closes_api_session(
        self,
        hass: HomeAssistant,
        mock_config_entry: Mock,
    ) -> None:
        """Test unload closes API session."""
        # Setup coordinator with mock API
        mock_api = AsyncMock()
        mock_api.close = AsyncMock()
        mock_coordinator = Mock()
        mock_coordinator.api = mock_api

        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
        mock_api.close.assert_called_once()


class TestSetupProfileEntities:
    """Tests for setup_profile_entities helper function."""

    def test_setup_profile_entities(self, mock_config_entry: Mock, mock_coordinator: Mock) -> None:
        """Test creating entities from profiles."""
        # Mock entity class
        mock_entity_class = Mock()

        entities = setup_profile_entities(mock_coordinator, mock_config_entry, mock_entity_class)

        # Should create 2 entities (profile_1 and profile_2)
        assert len(entities) == 2
        assert mock_entity_class.call_count == 2

    def test_setup_profile_entities_no_profiles(self, mock_coordinator: Mock) -> None:
        """Test creating entities when no profiles exist."""
        # Create config entry with no profiles
        entry = Mock(spec=ConfigEntry)
        entry.data = {}

        mock_entity_class = Mock()

        entities = setup_profile_entities(mock_coordinator, entry, mock_entity_class)

        assert len(entities) == 0
        mock_entity_class.assert_not_called()


class TestIsProfileAvailable:
    """Tests for is_profile_available helper function."""

    def test_profile_available(self, mock_coordinator: Mock) -> None:
        """Test profile availability when all conditions met."""
        mock_coordinator.last_update_success = True
        mock_coordinator.data = {"profile_1": {"name": "Test"}}

        assert is_profile_available(mock_coordinator, "profile_1") is True

    def test_profile_not_available_update_failed(self, mock_coordinator: Mock) -> None:
        """Test profile not available when last update failed."""
        mock_coordinator.last_update_success = False
        mock_coordinator.data = {"profile_1": {"name": "Test"}}

        assert is_profile_available(mock_coordinator, "profile_1") is False

    def test_profile_not_available_no_data(self, mock_coordinator: Mock) -> None:
        """Test profile not available when coordinator has no data."""
        mock_coordinator.last_update_success = True
        mock_coordinator.data = None

        assert is_profile_available(mock_coordinator, "profile_1") is False

    def test_profile_not_available_not_in_data(self, mock_coordinator: Mock) -> None:
        """Test profile not available when profile not in data."""
        mock_coordinator.last_update_success = True
        mock_coordinator.data = {"profile_2": {"name": "Test"}}

        assert is_profile_available(mock_coordinator, "profile_1") is False
