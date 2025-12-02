"""Config flow for Qustodio integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_APP_USAGE_CACHE_INTERVAL,
    CONF_ENABLE_GPS_TRACKING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_APP_USAGE_CACHE_INTERVAL,
    DEFAULT_ENABLE_GPS_TRACKING,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .exceptions import QustodioAuthenticationError, QustodioConnectionError, QustodioException
from .models import CoordinatorData
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)

# Email validation pattern (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    return EMAIL_PATTERN.match(email.strip()) is not None


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
        InvalidEmail: Email format is invalid
        EmptyUsername: Username is empty
        EmptyPassword: Password is empty
        InvalidAuth: Invalid credentials
        CannotConnect: Connection or API errors
        NoProfiles: Account has no profiles
    """
    # Note: hass parameter reserved for future reauthentication flows
    username = data.get(CONF_USERNAME, "").strip()
    password = data.get(CONF_PASSWORD, "")

    # Validate username is not empty
    if not username:
        raise EmptyUsername

    # Validate password is not empty
    if not password:
        raise EmptyPassword

    # Validate email format
    if not validate_email(username):
        raise InvalidEmail

    api = QustodioApi(username, password)

    try:
        await api.login()

        coordinator_data = await api.get_data()

        # Extract profiles dict from CoordinatorData
        # Convert ProfileData dataclasses to dicts for storage
        profiles_dict: dict[str, dict[str, Any]] = {}
        if coordinator_data and isinstance(coordinator_data, CoordinatorData):
            for profile_id, profile_data in coordinator_data.profiles.items():
                # Store raw_data which contains all the fields we need
                profiles_dict[profile_id] = profile_data.raw_data
        elif coordinator_data and isinstance(coordinator_data, dict):
            # coordinator_data is already a dict (test mocks only)
            profiles_dict = coordinator_data  # type: ignore[assignment]
        else:
            _LOGGER.warning("No data returned from API")

        if not profiles_dict:
            _LOGGER.warning("No profiles found for account %s", username)
            raise NoProfiles

        return {
            "title": f"Qustodio ({username})",
            "profiles": profiles_dict,
            "username": username,  # Return sanitized username
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
            except EmptyUsername:
                errors["base"] = "empty_username"
            except EmptyPassword:
                errors["base"] = "empty_password"
            except InvalidEmail:
                errors["base"] = "invalid_email"
            except NoProfiles:
                errors["base"] = "no_profiles"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Use sanitized username for unique ID
                username = info["username"]
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()

                # Store the profiles data in the config entry
                user_input[CONF_USERNAME] = username  # Use sanitized username
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
            except EmptyPassword:
                errors["base"] = "empty_password"
            except NoProfiles:
                errors["base"] = "no_profiles"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the config entry with new credentials and refreshed profiles
                data[CONF_USERNAME] = info["username"]  # Use sanitized username
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
        super().__init__()
        self._config_entry = config_entry  # type: ignore[misc]

    # Only define config_entry property if the parent class doesn't have it (older HA versions)
    if not hasattr(config_entries.OptionsFlow, "config_entry"):

        @property  # type: ignore[misc]
        def config_entry(self) -> config_entries.ConfigEntry:
            """Return the config entry for older HA versions that don't provide it."""
            return self._config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:  # type: ignore[override]
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)  # type: ignore[return-value]

        # Get current values from options or fall back to defaults
        current_interval = self._config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        current_gps = self._config_entry.options.get(CONF_ENABLE_GPS_TRACKING, DEFAULT_ENABLE_GPS_TRACKING)
        current_cache = self._config_entry.options.get(CONF_APP_USAGE_CACHE_INTERVAL, DEFAULT_APP_USAGE_CACHE_INTERVAL)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                    description={"suggested_value": current_interval},
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    CONF_ENABLE_GPS_TRACKING,
                    default=current_gps,
                ): bool,
                vol.Optional(
                    CONF_APP_USAGE_CACHE_INTERVAL,
                    default=current_cache,
                    description={"suggested_value": current_cache},
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )

        return self.async_show_form(  # type: ignore[return-value]
            step_id="init",
            data_schema=options_schema,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidEmail(HomeAssistantError):
    """Error to indicate email format is invalid."""


class EmptyUsername(HomeAssistantError):
    """Error to indicate username is empty."""


class EmptyPassword(HomeAssistantError):
    """Error to indicate password is empty."""


class NoProfiles(HomeAssistantError):
    """Error to indicate account has no profiles."""
