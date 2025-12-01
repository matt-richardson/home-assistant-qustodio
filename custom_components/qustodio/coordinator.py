"""Data update coordinator for Qustodio integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioDataError,
    QustodioException,
    QustodioRateLimitError,
)
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)


class QustodioDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: QustodioApi, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry

        # Initialize statistics tracking
        self.statistics: dict[str, Any] = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "consecutive_failures": 0,
            "error_counts": {},  # Track errors by type
        }

        # Get update interval from options or use default
        update_interval_minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        update_interval = timedelta(minutes=update_interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data via library."""
        update_time = datetime.now(timezone.utc).isoformat()
        self.statistics["total_updates"] += 1
        self.statistics["last_update_time"] = update_time

        try:
            data = await self.api.get_data()
            self._handle_update_success(update_time)
            return data
        except QustodioAuthenticationError as err:
            self._handle_authentication_error(err)
        except QustodioRateLimitError as err:
            self._handle_rate_limit_error(err)
        except QustodioConnectionError as err:
            self._handle_connection_error(err)
        except QustodioAPIError as err:
            self._handle_api_error(err)
        except QustodioDataError as err:
            self._handle_data_error(err)
        except QustodioException as err:
            self._handle_generic_qustodio_error(err)
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Catch all unexpected errors to provide user-friendly notifications
            self._handle_unexpected_error(err)

    def _handle_update_success(self, update_time: str) -> None:
        """Handle successful data update.

        Args:
            update_time: ISO timestamp of the update
        """
        self.statistics["successful_updates"] += 1
        self.statistics["last_success_time"] = update_time
        self.statistics["consecutive_failures"] = 0

        # Dismiss any existing error issues on success
        issue_ids = [
            "authentication_error",
            "connection_error",
            "rate_limit_error",
            "api_error",
            "data_error",
            "unexpected_error",
        ]
        for issue_id in issue_ids:
            self._dismiss_issue(issue_id)

    def _handle_authentication_error(self, err: QustodioAuthenticationError) -> None:
        """Handle authentication errors and trigger reauth.

        Args:
            err: The authentication error
        """
        self._track_failure("QustodioAuthenticationError")
        _LOGGER.error("Authentication failed: %s", err)

        # Trigger reauth flow
        entry_id = self._get_entry_id()
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                _LOGGER.info("Triggering reauthentication flow for entry %s", entry_id)
                entry.async_start_reauth(self.hass)

        self._create_issue("authentication_error", "authentication_error", severity=ir.IssueSeverity.ERROR)
        raise UpdateFailed(f"Authentication failed: {err}") from err

    def _handle_rate_limit_error(self, err: QustodioRateLimitError) -> None:
        """Handle rate limit errors.

        Args:
            err: The rate limit error
        """
        self._track_failure("QustodioRateLimitError")
        _LOGGER.warning("Rate limit exceeded: %s", err)

        self._create_issue(
            "rate_limit_error",
            "rate_limit_error",
            severity=ir.IssueSeverity.WARNING,
            translation_placeholders={
                "update_interval": str(self.entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            },
        )
        raise UpdateFailed(f"Rate limit exceeded: {err}") from err

    def _handle_connection_error(self, err: QustodioConnectionError) -> None:
        """Handle connection errors.

        Args:
            err: The connection error
        """
        self._track_failure("QustodioConnectionError")
        _LOGGER.warning("Connection error: %s", err)

        # Only create issue after multiple consecutive failures
        if self.statistics["consecutive_failures"] >= 3:
            self._create_issue(
                "connection_error",
                "connection_error",
                severity=ir.IssueSeverity.WARNING,
                translation_placeholders={"consecutive_failures": str(self.statistics["consecutive_failures"])},
            )
        raise UpdateFailed(f"Connection error: {err}") from err

    def _handle_api_error(self, err: QustodioAPIError) -> None:
        """Handle API errors.

        Args:
            err: The API error
        """
        self._track_failure("QustodioAPIError")
        _LOGGER.error("Qustodio API error: %s (status: %s)", err, getattr(err, "status_code", "unknown"))

        self._create_issue(
            "api_error",
            "api_error",
            severity=ir.IssueSeverity.ERROR,
            translation_placeholders={
                "error_message": str(err),
                "status_code": str(getattr(err, "status_code", "unknown")),
            },
        )
        raise UpdateFailed(f"API error: {err}") from err

    def _handle_data_error(self, err: QustodioDataError) -> None:
        """Handle data parsing errors.

        Args:
            err: The data error
        """
        self._track_failure("QustodioDataError")
        _LOGGER.error("Data error: %s", err)

        # Only create issue after multiple consecutive data errors
        if self.statistics["consecutive_failures"] >= 2:
            self._create_issue(
                "data_error",
                "data_error",
                severity=ir.IssueSeverity.WARNING,
                translation_placeholders={"error_message": str(err)},
            )
        raise UpdateFailed(f"Data error: {err}") from err

    def _handle_generic_qustodio_error(self, err: QustodioException) -> None:
        """Handle generic Qustodio errors.

        Args:
            err: The Qustodio error
        """
        self._track_failure("QustodioException")
        _LOGGER.error("Qustodio error: %s", err)

        self._create_issue(
            "api_error",
            "generic_error",
            severity=ir.IssueSeverity.ERROR,
            translation_placeholders={"error_message": str(err)},
        )
        raise UpdateFailed(f"Error: {err}") from err

    def _handle_unexpected_error(self, err: Exception) -> None:
        """Handle unexpected errors.

        Args:
            err: The unexpected error
        """
        self._track_failure("UnexpectedError")
        _LOGGER.exception("Unexpected error updating Qustodio data")

        # Create notification for unexpected errors after multiple failures
        if self.statistics["consecutive_failures"] >= 2:
            self._create_issue(
                "unexpected_error",
                "unexpected_error",
                severity=ir.IssueSeverity.ERROR,
                translation_placeholders={"error_message": str(err)},
            )
        raise UpdateFailed(f"Unexpected error: {err}") from err

    def _get_entry_id(self) -> str | None:
        """Get the config entry ID for this coordinator.

        Returns:
            The entry ID or None if not found
        """
        for entry_id, coordinator in self.hass.data.get(DOMAIN, {}).items():
            if coordinator == self:
                return entry_id
        return None

    def _track_failure(self, error_type: str) -> None:
        """Track update failure statistics.

        Args:
            error_type: The type of error that occurred
        """
        self.statistics["failed_updates"] += 1
        self.statistics["consecutive_failures"] += 1
        self.statistics["last_failure_time"] = datetime.now(timezone.utc).isoformat()

        # Track error counts by type
        if error_type not in self.statistics["error_counts"]:
            self.statistics["error_counts"][error_type] = 0
        self.statistics["error_counts"][error_type] += 1

    def _create_issue(
        self,
        issue_id: str,
        translation_key: str,
        severity: ir.IssueSeverity = ir.IssueSeverity.ERROR,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Create or update an issue in the issue registry.

        Args:
            issue_id: Unique identifier for this issue
            translation_key: Translation key for the issue message
            severity: Severity level of the issue
            translation_placeholders: Placeholders for translation strings
        """
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=severity,
            translation_key=translation_key,
            translation_placeholders=translation_placeholders or {},
        )

    def _dismiss_issue(self, issue_id: str) -> None:
        """Dismiss an issue from the issue registry.

        Args:
            issue_id: Unique identifier for the issue to dismiss
        """
        ir.async_delete_issue(self.hass, DOMAIN, issue_id)
