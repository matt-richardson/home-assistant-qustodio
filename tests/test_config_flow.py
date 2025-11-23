"""Tests for Qustodio config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from qustodio.config_flow import CannotConnect, ConfigFlow, InvalidAuth
from qustodio.const import DOMAIN
from qustodio.exceptions import (
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioException,
)


class TestConfigFlow:
    """Tests for Qustodio config flow."""

    async def test_reconfigure_step(self, hass: HomeAssistant) -> None:
        """Test reconfigure step delegates to user step."""
        flow = ConfigFlow()
        flow.hass = hass

        # Call async_step_reconfigure with None
        result = await flow.async_step_reconfigure(None)

        # It should return a form for user input
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_is_matching(self, hass: HomeAssistant) -> None:
        """Test is_matching always returns False."""
        flow = ConfigFlow()
        flow.hass = hass

        other_flow = ConfigFlow()
        other_flow.hass = hass

        assert flow.is_matching(other_flow) is False


class TestValidateInput:
    """Tests for validate_input helper function."""

    async def test_validate_input_success(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
    ) -> None:
        """Test successful input validation."""
        from qustodio.config_flow import validate_input

        with patch("qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = mock_profile_data

            result = await validate_input(
                hass,
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                },
            )

            assert result["title"] == "Qustodio (test@example.com)"
            assert result["profiles"] == mock_profile_data

    async def test_validate_input_no_profiles(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test input validation with no profiles."""
        from qustodio.config_flow import validate_input

        with patch("qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = {}

            result = await validate_input(
                hass,
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                },
            )

            assert result["title"] == "Qustodio (test@example.com)"
            assert result["profiles"] == {}

    async def test_validate_input_invalid_auth(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test input validation with invalid auth."""
        from qustodio.config_flow import validate_input

        with patch("qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioAuthenticationError("Invalid credentials")

            with pytest.raises(InvalidAuth):
                await validate_input(
                    hass,
                    {
                        CONF_USERNAME: "test@example.com",
                        CONF_PASSWORD: "wrong_password",
                    },
                )

    async def test_validate_input_cannot_connect(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test input validation with connection error."""
        from qustodio.config_flow import validate_input

        with patch("qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioConnectionError("Connection timeout")

            with pytest.raises(CannotConnect):
                await validate_input(
                    hass,
                    {
                        CONF_USERNAME: "test@example.com",
                        CONF_PASSWORD: "password",
                    },
                )


class TestOptionsFlow:
    """Tests for Qustodio options flow."""

    async def test_options_flow_exists(self) -> None:
        """Test that OptionsFlowHandler class exists."""
        from qustodio.config_flow import OptionsFlowHandler

        assert OptionsFlowHandler is not None
        assert hasattr(OptionsFlowHandler, "__init__")
