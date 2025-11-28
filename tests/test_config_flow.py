"""Tests for Qustodio config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.qustodio.config_flow import CannotConnect, ConfigFlow, InvalidAuth
from custom_components.qustodio.exceptions import (
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
        from custom_components.qustodio.config_flow import validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
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
        from custom_components.qustodio.config_flow import validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
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
        from custom_components.qustodio.config_flow import validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
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
        from custom_components.qustodio.config_flow import validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioConnectionError("Connection timeout")

            with pytest.raises(CannotConnect):
                await validate_input(
                    hass,
                    {
                        CONF_USERNAME: "test@example.com",
                        CONF_PASSWORD: "password",
                    },
                )


class TestUserFlow:
    """Tests for async_step_user flow."""

    async def test_user_step_success(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
    ) -> None:
        """Test successful user step creates entry."""
        from custom_components.qustodio.config_flow import ConfigFlow

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = mock_profile_data

            flow = ConfigFlow()
            flow.hass = hass

            result = await flow.async_step_user(
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                }
            )

            assert result["type"] == "create_entry"
            assert result["title"] == "Qustodio (test@example.com)"
            assert result["data"][CONF_USERNAME] == "test@example.com"
            assert result["data"]["profiles"] == mock_profile_data

    async def test_user_step_form(self, hass: HomeAssistant) -> None:
        """Test showing form when no user input."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_user_step_cannot_connect(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test user step with connection error."""
        from custom_components.qustodio.config_flow import ConfigFlow

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioConnectionError("Connection failed")

            flow = ConfigFlow()
            flow.hass = hass

            result = await flow.async_step_user(
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                }
            )

            assert result["type"] == "form"
            assert result["errors"]["base"] == "cannot_connect"

    async def test_user_step_invalid_auth(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test user step with invalid credentials."""
        from custom_components.qustodio.config_flow import ConfigFlow

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioAuthenticationError("Invalid credentials")

            flow = ConfigFlow()
            flow.hass = hass

            result = await flow.async_step_user(
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "wrong_password",
                }
            )

            assert result["type"] == "form"
            assert result["errors"]["base"] == "invalid_auth"

    async def test_user_step_unknown_error(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test user step with unexpected error."""
        from custom_components.qustodio.config_flow import ConfigFlow

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = Exception("Unexpected error")

            flow = ConfigFlow()
            flow.hass = hass

            result = await flow.async_step_user(
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                }
            )

            assert result["type"] == "form"
            assert result["errors"]["base"] == "unknown"

    async def test_validate_input_generic_exception(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test validate_input with generic QustodioException."""
        from custom_components.qustodio.config_flow import CannotConnect, validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioException("Generic error")

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
        from custom_components.qustodio.config_flow import OptionsFlowHandler

        assert OptionsFlowHandler is not None
        assert hasattr(OptionsFlowHandler, "__init__")


class TestReauthFlow:
    """Tests for reauthentication flow."""

    async def test_reauth_step_initiates_flow(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
    ) -> None:
        """Test reauth step initiates the reauthentication flow."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}

        with patch.object(hass.config_entries, "async_get_entry", return_value=mock_config_entry):
            result = await flow.async_step_reauth(entry_data={})

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reauth_confirm"
            assert flow._reauth_entry == mock_config_entry

    async def test_reauth_confirm_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
        mock_qustodio_api: AsyncMock,
        mock_profile_data: dict[str, Any],
    ) -> None:
        """Test successful reauthentication updates credentials."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}
        flow._reauth_entry = mock_config_entry

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = mock_profile_data

            result = await flow.async_step_reauth_confirm(
                {
                    CONF_PASSWORD: "new_password",
                }
            )

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "reauth_successful"

    async def test_reauth_confirm_shows_form(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
    ) -> None:
        """Test reauth confirm shows form with pre-filled username."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}
        flow._reauth_entry = mock_config_entry

        result = await flow.async_step_reauth_confirm(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["description_placeholders"]["username"] == "test@example.com"

    async def test_reauth_confirm_invalid_auth(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test reauthentication with invalid credentials."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}
        flow._reauth_entry = mock_config_entry

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioAuthenticationError("Invalid credentials")

            result = await flow.async_step_reauth_confirm(
                {
                    CONF_PASSWORD: "wrong_password",
                }
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    async def test_reauth_confirm_cannot_connect(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test reauthentication with connection error."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}
        flow._reauth_entry = mock_config_entry

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = QustodioConnectionError("Connection failed")

            result = await flow.async_step_reauth_confirm(
                {
                    CONF_PASSWORD: "password",
                }
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    async def test_reauth_confirm_unknown_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test reauthentication with unexpected error."""
        from custom_components.qustodio.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}
        flow._reauth_entry = mock_config_entry

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.login.side_effect = Exception("Unexpected error")

            result = await flow.async_step_reauth_confirm(
                {
                    CONF_PASSWORD: "password",
                }
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "unknown"


class TestQustodioOptionsFlow:
    """Test Qustodio options flow."""

    async def test_options_flow_init(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
    ) -> None:
        """Test options flow initialization."""
        from custom_components.qustodio.config_flow import OptionsFlowHandler
        from custom_components.qustodio.const import CONF_ENABLE_GPS_TRACKING, CONF_UPDATE_INTERVAL

        flow = OptionsFlowHandler(mock_config_entry)

        result = await flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"
        # Check that defaults are used when no options are set
        schema = result["data_schema"].schema
        assert CONF_UPDATE_INTERVAL in schema
        assert CONF_ENABLE_GPS_TRACKING in schema

    async def test_options_flow_with_existing_options(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
    ) -> None:
        """Test options flow with existing options."""
        from custom_components.qustodio.config_flow import OptionsFlowHandler
        from custom_components.qustodio.const import CONF_ENABLE_GPS_TRACKING, CONF_UPDATE_INTERVAL

        # Set up existing options
        mock_config_entry.options = {
            CONF_UPDATE_INTERVAL: 10,
            CONF_ENABLE_GPS_TRACKING: False,
        }

        flow = OptionsFlowHandler(mock_config_entry)

        result = await flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_save(
        self,
        hass: HomeAssistant,
        mock_config_entry: Any,
    ) -> None:
        """Test saving options."""
        from custom_components.qustodio.config_flow import OptionsFlowHandler
        from custom_components.qustodio.const import CONF_ENABLE_GPS_TRACKING, CONF_UPDATE_INTERVAL

        flow = OptionsFlowHandler(mock_config_entry)

        result = await flow.async_step_init(
            {
                CONF_UPDATE_INTERVAL: 15,
                CONF_ENABLE_GPS_TRACKING: False,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_UPDATE_INTERVAL: 15,
            CONF_ENABLE_GPS_TRACKING: False,
        }


class TestValidateInputCoordinatorDataExtraction:
    """Tests for validate_input CoordinatorData extraction - covers lines 57-63 in config_flow.py."""

    async def test_validate_input_extracts_profiles_from_coordinator_data(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test validate_input properly extracts profiles dict from CoordinatorData."""
        from custom_components.qustodio.config_flow import validate_input
        from custom_components.qustodio.models import CoordinatorData, ProfileData

        # Create CoordinatorData structure with proper dataclasses
        profile1_raw = {
            "id": 11282538,
            "uid": "uid_1",
            "name": "Test Child",
            "is_online": True,
            "device_count": 2,
            "device_ids": [111, 222],
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "quota": 120,
            "time": 45.5,
        }

        coordinator_data = CoordinatorData(
            profiles={
                "11282538": ProfileData.from_api_response(profile1_raw),
            },
            devices={},
        )

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = coordinator_data

            result = await validate_input(
                hass,
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                },
            )

            # Should extract profiles dict, not the entire CoordinatorData
            assert result["title"] == "Qustodio (test@example.com)"
            assert "profiles" in result
            assert isinstance(result["profiles"], dict)
            assert "11282538" in result["profiles"]
            # Should have the raw_data dict, not ProfileData object
            assert isinstance(result["profiles"]["11282538"], dict)
            assert result["profiles"]["11282538"]["id"] == 11282538
            assert result["profiles"]["11282538"]["name"] == "Test Child"
            assert result["profiles"]["11282538"]["device_count"] == 2

    async def test_validate_input_empty_profiles(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test validate_input with CoordinatorData but empty profiles."""
        from custom_components.qustodio.config_flow import validate_input
        from custom_components.qustodio.models import CoordinatorData

        # Empty CoordinatorData
        coordinator_data = CoordinatorData(
            profiles={},
            devices={},
        )

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = coordinator_data

            result = await validate_input(
                hass,
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                },
            )

            # Should return empty profiles dict
            assert result["title"] == "Qustodio (test@example.com)"
            assert result["profiles"] == {}

    async def test_validate_input_none_data(
        self,
        hass: HomeAssistant,
        mock_qustodio_api: AsyncMock,
    ) -> None:
        """Test validate_input when get_data returns None."""
        from custom_components.qustodio.config_flow import validate_input

        with patch("custom_components.qustodio.config_flow.QustodioApi", return_value=mock_qustodio_api):
            mock_qustodio_api.get_data.return_value = None

            result = await validate_input(
                hass,
                {
                    CONF_USERNAME: "test@example.com",
                    CONF_PASSWORD: "password",
                },
            )

            # Should handle None gracefully via fallback - line 63
            assert result["title"] == "Qustodio (test@example.com)"
            assert result["profiles"] == {}


class TestConfigFlowAsyncGetOptionsFlow:
    """Tests for ConfigFlow.async_get_options_flow."""

    def test_async_get_options_flow(self, mock_config_entry: Mock) -> None:
        """Test async_get_options_flow returns OptionsFlowHandler."""
        from custom_components.qustodio.config_flow import ConfigFlow, OptionsFlowHandler

        result = ConfigFlow.async_get_options_flow(mock_config_entry)

        # Should return OptionsFlowHandler instance
        assert isinstance(result, OptionsFlowHandler)
        assert result._config_entry == mock_config_entry
