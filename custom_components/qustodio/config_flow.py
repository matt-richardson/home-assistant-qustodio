"""Config flow for Qustodio integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .exceptions import QustodioAuthenticationError, QustodioConnectionError, QustodioException
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(_hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.

    Raises:
        InvalidAuth: Invalid credentials
        CannotConnect: Connection or API errors
    """
    # Note: hass parameter reserved for future reauthentication flows
    api = QustodioApi(data[CONF_USERNAME], data[CONF_PASSWORD])

    try:
        await api.login()

        profiles = await api.get_data()
        if not profiles:
            _LOGGER.warning("No profiles found for account")

        return {
            "title": f"Qustodio ({data[CONF_USERNAME]})",
            "profiles": profiles,
        }

    except QustodioAuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise InvalidAuth from err
    except QustodioConnectionError as err:
        _LOGGER.error("Connection failed: %s", err)
        raise CannotConnect from err
    except QustodioException as err:
        _LOGGER.error("Qustodio API error: %s", err)
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Qustodio."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:  # type: ignore[override]
        """Handle reconfiguration of the integration."""
        return await self.async_step_user(user_input)

    def is_matching(self, other_flow: config_entries.ConfigFlow) -> bool:  # pylint: disable=unused-argument
        """Return True if other_flow is matching this flow."""
        return False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:  # type: ignore[override]
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Store the profiles data in the config entry
                user_input["profiles"] = info["profiles"]
                return self.async_create_entry(title=info["title"], data=user_input)  # type: ignore[return-value]

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )  # type: ignore[return-value]

    async def async_step_reauth(
        self, entry_data: dict[str, Any]  # pylint: disable=unused-argument
    ) -> FlowResult:  # type: ignore[override]
        """Handle reauthentication when credentials expire."""
        # Store the config entry for later update
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:  # type: ignore[override]
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}

        # Ensure we have a reauth entry
        assert self._reauth_entry is not None

        if user_input is not None:
            # Merge with existing config (username doesn't change)
            username = self._reauth_entry.data[CONF_USERNAME]
            data = {
                CONF_USERNAME: username,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            try:
                info = await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the config entry with new credentials and refreshed profiles
                data["profiles"] = info["profiles"]
                return self.async_update_reload_and_abort(  # type: ignore[return-value]
                    self._reauth_entry,
                    data=data,
                )

        # Show form with username pre-filled (read-only)
        username = self._reauth_entry.data[CONF_USERNAME]

        reauth_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=username, description={"suggested_value": username}): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(  # type: ignore[return-value]
            step_id="reauth_confirm",
            data_schema=reauth_schema,
            errors=errors,
            description_placeholders={"username": username},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Qustodio."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
