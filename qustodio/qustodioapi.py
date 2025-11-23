"""Qustodio API client."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp

from .const import LOGIN_RESULT_OK
from .exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioDataError,
    QustodioRateLimitError,
)


@dataclass
class ProfileContext:
    """Context for processing a profile."""

    session: aiohttp.ClientSession
    headers: dict[str, Any]
    profile: dict[str, Any]
    devices: dict[str, Any]
    dow: str


_LOGGER = logging.getLogger(__name__)
TIMEOUT = 15

# Qustodio API URLs - these are based on reverse engineering and may change
URL_LOGIN = "https://api.qustodio.com/v1/oauth2/access_token"
URL_ACCOUNT = "https://api.qustodio.com/v1/accounts/me"
URL_PROFILES = "https://api.qustodio.com/v1/accounts/{}/profiles/"
URL_RULES = "https://api.qustodio.com/v1/accounts/{}/profiles/{}/rules?app_rules=1"
URL_DEVICES = "https://api.qustodio.com/v1/accounts/{}/devices"
URL_HOURLY_SUMMARY = "https://api.qustodio.com/v2/accounts/{}/profiles/{}/summary_hourly?date={}"
URL_ACTIVITY = "https://api.qustodio.com/v1/accounts/{}/profiles/{}/activity"

# Client credentials - these are extracted from the mobile app and may change
CLIENT_ID = "264ca1d226906aa08b03"
CLIENT_SECRET = "3e8826cbed3b996f8b206c7d6a4b2321529bc6bd"


class QustodioApi:
    """Qustodio API client."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._expires_in: datetime | None = None
        self._account_id: str | None = None
        self._account_uid: str | None = None

    async def login(self) -> str:
        """Login to Qustodio API.

        Returns LOGIN_RESULT_OK for backward compatibility.

        Raises:
            QustodioAuthenticationError: Invalid credentials
            QustodioConnectionError: Network/connection issues
            QustodioAPIError: API returned unexpected error
            QustodioDataError: Response missing expected data
        """
        if self._access_token is not None and self._expires_in is not None and self._expires_in > datetime.now():
            return LOGIN_RESULT_OK

        _LOGGER.debug("Logging in to Qustodio API")

        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers={"User-Agent": "Qustodio/2.0.0 (Android)"},
            ) as session:
                async with session.post(URL_LOGIN, data=data) as response:
                    if response.status == 401:
                        _LOGGER.error("Unauthorized: Invalid credentials")
                        raise QustodioAuthenticationError("Invalid username or password")

                    if response.status == 429:
                        _LOGGER.error("Rate limit exceeded")
                        raise QustodioRateLimitError("API rate limit exceeded")

                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("Login failed with status %s: %s", response.status, text)
                        raise QustodioAPIError(
                            f"Login failed with status {response.status}",
                            status_code=response.status,
                        )

                    response_data = await response.json()

                    if "access_token" not in response_data:
                        _LOGGER.error("No access token in response")
                        raise QustodioDataError("Response missing access token")

                    self._access_token = response_data["access_token"]
                    self._expires_in = datetime.now() + timedelta(seconds=response_data.get("expires_in", 3600))
                    _LOGGER.debug("Login successful")
                    return LOGIN_RESULT_OK

        except (
            QustodioAuthenticationError,
            QustodioConnectionError,
            QustodioRateLimitError,
            QustodioAPIError,
            QustodioDataError,
        ):
            # Re-raise our own exceptions
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Login timeout")
            raise QustodioConnectionError("Connection timeout during login") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Login connection error: %s", err)
            raise QustodioConnectionError(f"Connection error during login: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected login error: %s", err)
            raise QustodioAPIError(f"Unexpected error during login: {err}") from err

    async def _fetch_account_info(self, session: aiohttp.ClientSession, headers: dict[str, str]) -> None:
        """Fetch and store account information."""
        async with session.get(URL_ACCOUNT, headers=headers) as response:
            if response.status == 401:
                raise QustodioAuthenticationError("Token expired or invalid")
            if response.status == 429:
                raise QustodioRateLimitError("API rate limit exceeded")
            if response.status != 200:
                raise QustodioAPIError(
                    f"Failed to get account info: HTTP {response.status}",
                    status_code=response.status,
                )

            account_data = await response.json()
            if "id" not in account_data:
                raise QustodioDataError("Account data missing required 'id' field")

            self._account_id = account_data["id"]
            self._account_uid = account_data.get("uid", account_data["id"])

    async def _fetch_devices(self, session: aiohttp.ClientSession, headers: dict[str, str]) -> dict[str, Any]:
        """Fetch devices from API."""
        _LOGGER.debug("Getting devices")
        devices = {}
        try:
            async with session.get(URL_DEVICES.format(self._account_id), headers=headers) as response:
                if response.status == 200:
                    devices_data = await response.json()
                    devices = {device["id"]: device for device in devices_data}
                else:
                    _LOGGER.warning("Failed to get devices: %s", response.status)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Error getting devices: %s", err)
        return devices

    async def _fetch_profiles(self, session: aiohttp.ClientSession, headers: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch profiles from API."""
        _LOGGER.debug("Getting profiles")
        async with session.get(URL_PROFILES.format(self._account_id), headers=headers) as response:
            if response.status == 401:
                raise QustodioAuthenticationError("Token expired or invalid")
            if response.status == 429:
                raise QustodioRateLimitError("API rate limit exceeded")
            if response.status != 200:
                raise QustodioAPIError(
                    f"Failed to get profiles: HTTP {response.status}",
                    status_code=response.status,
                )

            profiles_data = await response.json()
            if not isinstance(profiles_data, list):
                raise QustodioDataError("Profiles data is not a list")
            return profiles_data

    def _check_device_tampering(
        self,
        profile_data: dict[str, Any],
        profile: dict[str, Any],
        devices: dict[str, Any],
    ) -> None:
        """Check for unauthorized device removal."""
        device_ids = profile.get("device_ids", [])
        for device_id in device_ids:
            if device_id in devices:
                device = devices[device_id]
                alerts = device.get("alerts", {})
                if alerts.get("unauthorized_remove", False):
                    profile_data["unauthorized_remove"] = True
                    profile_data["device_tampered"] = device.get("name", "Unknown")

    def _set_location_data(
        self,
        profile_data: dict[str, Any],
        profile: dict[str, Any],
        devices: dict[str, Any],
    ) -> None:
        """Set current device and location data."""
        status = profile.get("status", {})
        location = status.get("location", {})
        device_id = location.get("device")

        if profile_data["is_online"] and device_id and device_id in devices:
            profile_data["current_device"] = devices[device_id].get("name")
        else:
            profile_data["current_device"] = None

        profile_data["latitude"] = location.get("latitude")
        profile_data["longitude"] = location.get("longitude")
        profile_data["accuracy"] = location.get("accuracy", 0)
        profile_data["lastseen"] = status.get("lastseen")

    async def _fetch_quota(
        self,
        session: aiohttp.ClientSession,
        headers: dict[str, str],
        profile_data: dict[str, Any],
        dow: str,
    ) -> int:
        """Fetch quota for a profile."""
        profile_id = profile_data["id"]
        profile_name = profile_data["name"]
        try:
            async with session.get(
                URL_RULES.format(self._account_id, profile_id),
                headers=headers,
            ) as response:
                if response.status == 200:
                    rules_data = await response.json()
                    time_restrictions = rules_data.get("time_restrictions", {})
                    quotas = time_restrictions.get("quotas", {})
                    return quotas.get(dow, 0)
                _LOGGER.debug("No rules found for profile %s", profile_name)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Failed to get rules for profile %s: %s", profile_name, err)
        return 0

    async def _fetch_screen_time(
        self,
        session: aiohttp.ClientSession,
        headers: dict[str, str],
        profile_data: dict[str, Any],
    ) -> float:
        """Fetch screen time for a profile."""
        profile_uid = profile_data["uid"]
        profile_name = profile_data["name"]
        try:
            async with session.get(
                URL_HOURLY_SUMMARY.format(self._account_uid, profile_uid, date.today()),
                headers=headers,
            ) as response:
                if response.status == 200:
                    hourly_data = await response.json()
                    total_time = sum(entry.get("screen_time_seconds", 0) for entry in hourly_data)
                    return round(total_time / 60, 1)  # Convert to minutes
                _LOGGER.debug("Hourly summary not available for profile %s", profile_name)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Failed to get screen time for profile %s: %s", profile_name, err)
        return 0

    async def _process_profile(self, ctx: ProfileContext) -> dict[str, Any]:
        """Process a single profile and gather all its data."""
        _LOGGER.debug("Processing profile: %s", ctx.profile["name"])
        profile_data = {
            "id": ctx.profile["id"],
            "uid": ctx.profile.get("uid", ctx.profile["id"]),
            "name": ctx.profile["name"],
            "is_online": ctx.profile.get("status", {}).get("is_online", False),
            "unauthorized_remove": False,
            "device_tampered": None,
        }

        self._check_device_tampering(profile_data, ctx.profile, ctx.devices)
        self._set_location_data(profile_data, ctx.profile, ctx.devices)

        profile_data["quota"] = await self._fetch_quota(ctx.session, ctx.headers, profile_data, ctx.dow)
        profile_data["time"] = await self._fetch_screen_time(ctx.session, ctx.headers, profile_data)

        return profile_data

    async def get_data(self) -> dict[str, Any]:
        """Get data from Qustodio API.

        Raises:
            QustodioAuthenticationError: Authentication failed
            QustodioConnectionError: Network/connection issues
            QustodioAPIError: API returned unexpected error
            QustodioDataError: Response missing expected data
        """
        _LOGGER.debug("Getting data from Qustodio API")

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers={"User-Agent": "Qustodio/2.0.0 (Android)"},
            ) as session:
                self._session = session

                # Login will raise exceptions on failure
                await self.login()

                headers = {
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

                # Get account info
                await self._fetch_account_info(session, headers)

                # Get devices
                devices = await self._fetch_devices(session, headers)

                # Get profiles
                profiles_data = await self._fetch_profiles(session, headers)

                # Process each profile
                days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                dow = days[datetime.today().weekday()]
                data = {}

                for profile in profiles_data:
                    if "id" not in profile or "name" not in profile:
                        _LOGGER.warning("Profile missing required fields, skipping")
                        continue

                    ctx = ProfileContext(session=session, headers=headers, profile=profile, devices=devices, dow=dow)
                    profile_data = await self._process_profile(ctx)
                    data[profile_data["id"]] = profile_data

                self._session = None
                return data

        except (
            QustodioAuthenticationError,
            QustodioConnectionError,
            QustodioRateLimitError,
            QustodioAPIError,
            QustodioDataError,
        ):
            # Re-raise our own exceptions
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout getting data from Qustodio API")
            raise QustodioConnectionError("Connection timeout while fetching data") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error getting data from Qustodio API: %s", err)
            raise QustodioConnectionError(f"Connection error while fetching data: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error getting data from Qustodio API: %s", err)
            raise QustodioAPIError(f"Unexpected error while fetching data: {err}") from err
        finally:
            self._session = None
