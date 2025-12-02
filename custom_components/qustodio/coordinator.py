"""Data update coordinator for Qustodio integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_APP_USAGE_CACHE_INTERVAL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_APP_USAGE_CACHE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioDataError,
    QustodioException,
    QustodioRateLimitError,
)
from .models import AppUsage, CoordinatorData
from .qustodioapi import QustodioApi

_LOGGER = logging.getLogger(__name__)


class QustodioDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: QustodioApi, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry

        # Initialize statistics tracking
        self.statistics = self._initialize_statistics()

        # App usage caching (configurable interval to reduce API calls)
        self._last_app_fetch_date: datetime | None = None
        self._cached_app_usage: dict[str, list] | None = None
        self._app_usage_cache_seconds = self._get_app_usage_cache_seconds(entry)

        # Get update interval from options or use default
        update_interval = self._get_update_interval(entry)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data via library."""
        update_time = self._get_current_time()
        self._record_update_start(update_time)

        try:
            # Fetch main data (profiles, devices)
            data = await self.api.get_data()

            # Fetch app usage once per hour (cached)
            await self._fetch_app_usage(data)

            self._handle_update_success(update_time, data)
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

    def _handle_update_success(self, update_time: str, data: Any) -> None:
        """Handle successful data update.

        Args:
            update_time: ISO timestamp of the update
            data: The fetched coordinator data
        """
        self._record_update_success(update_time)
        self._dismiss_all_issues()
        self._log_update_statistics(data)

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

    def _initialize_statistics(self) -> dict[str, Any]:
        """Initialize statistics tracking dictionary.

        Returns:
            Dictionary with initial statistics values
        """
        return {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_update_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "consecutive_failures": 0,
            "error_counts": {},
        }

    def _get_update_interval(self, entry: ConfigEntry) -> timedelta:
        """Get update interval from config entry options.

        Args:
            entry: The config entry

        Returns:
            Timedelta representing the update interval
        """
        update_interval_minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        return timedelta(minutes=update_interval_minutes)

    def _get_app_usage_cache_seconds(self, entry: ConfigEntry) -> int:
        """Get app usage cache interval in seconds from config entry options.

        Args:
            entry: The config entry

        Returns:
            Cache interval in seconds
        """
        cache_interval_minutes = entry.options.get(CONF_APP_USAGE_CACHE_INTERVAL, DEFAULT_APP_USAGE_CACHE_INTERVAL)
        return cache_interval_minutes * 60

    def _get_current_time(self) -> str:
        """Get current time as ISO format string.

        Returns:
            ISO formatted timestamp string
        """
        return datetime.now(timezone.utc).isoformat()

    def _record_update_start(self, update_time: str) -> None:
        """Record the start of an update attempt.

        Args:
            update_time: ISO timestamp of the update
        """
        self.statistics["total_updates"] += 1
        self.statistics["last_update_time"] = update_time

    def _record_update_success(self, update_time: str) -> None:
        """Record successful update statistics.

        Args:
            update_time: ISO timestamp of the update
        """
        self.statistics["successful_updates"] += 1
        self.statistics["last_success_time"] = update_time
        self.statistics["consecutive_failures"] = 0

    def _dismiss_all_issues(self) -> None:
        """Dismiss all known error issues."""
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

    def _log_update_statistics(self, data: CoordinatorData | Any) -> None:
        """Log statistics about the successful update.

        Args:
            data: The coordinator data
        """
        try:
            if hasattr(data, "profiles") and hasattr(data, "devices"):
                profile_count = len(data.profiles)
                device_count = len(data.devices)

                _LOGGER.debug(
                    "Successfully updated Qustodio data: %d profiles, %d devices",
                    profile_count,
                    device_count,
                )
            else:
                _LOGGER.debug("Successfully updated Qustodio data")
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Don't fail the update if logging fails
            _LOGGER.debug("Could not log update statistics: %s", err)

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

    async def _fetch_app_usage(self, data: CoordinatorData) -> None:
        """Fetch app usage data for all profiles (cached based on configuration).

        Args:
            data: Coordinator data to update with app usage
        """
        # Skip if data is not CoordinatorData (backward compatibility)
        if not isinstance(data, CoordinatorData):
            _LOGGER.debug("Skipping app usage fetch - data is not CoordinatorData instance")
            return

        now = datetime.now(timezone.utc)

        # Check if we need to fetch (based on configured cache interval)
        if self._last_app_fetch_date is not None:
            time_since_last_fetch = now - self._last_app_fetch_date
            if time_since_last_fetch.total_seconds() < self._app_usage_cache_seconds:
                # Use cached data
                data.app_usage = self._cached_app_usage
                _LOGGER.debug("Using cached app usage data from %s", self._last_app_fetch_date)
                return

        _LOGGER.debug("Fetching app usage data for all profiles")

        try:
            app_usage_by_profile: dict[str, list[AppUsage]] = {}
            today = now.date()

            # Fetch app usage for each profile
            for profile_id, profile in data.profiles.items():
                try:
                    # Get usage for today only
                    usage_response = await self.api.get_app_usage(
                        profile_uid=profile.uid,
                        min_date=today,
                        max_date=today,
                    )

                    # Convert API response to AppUsage objects
                    apps = [AppUsage.from_api_response(item) for item in usage_response.get("items", [])]

                    # Sort by minutes descending (most used first)
                    apps.sort(key=lambda x: x.minutes, reverse=True)

                    app_usage_by_profile[profile_id] = apps

                    _LOGGER.debug(
                        "Fetched %d apps for profile %s (%s)",
                        len(apps),
                        profile.name,
                        profile_id,
                    )

                except Exception as err:  # pylint: disable=broad-exception-caught
                    # Don't fail the entire update if app usage fails for one profile
                    _LOGGER.warning(
                        "Failed to fetch app usage for profile %s: %s",
                        profile_id,
                        err,
                    )
                    app_usage_by_profile[profile_id] = []

            # Update cache
            self._cached_app_usage = app_usage_by_profile
            self._last_app_fetch_date = now
            data.app_usage = app_usage_by_profile

            _LOGGER.info("Successfully fetched app usage for %d profiles", len(app_usage_by_profile))

        except Exception as err:  # pylint: disable=broad-exception-caught
            # Don't fail the entire update if app usage fails
            _LOGGER.warning("Failed to fetch app usage data: %s", err)
            # Use cached data if available
            if self._cached_app_usage is not None:
                data.app_usage = self._cached_app_usage
                _LOGGER.debug("Using previous cached app usage data due to fetch failure")
            else:
                data.app_usage = None
