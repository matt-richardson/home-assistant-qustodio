"""Tests for Qustodio API client."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from qustodio.const import LOGIN_RESULT_OK
from qustodio.exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioDataError,
    QustodioRateLimitError,
)
from qustodio.qustodioapi import QustodioApi


class TestQustodioApiLogin:
    """Tests for QustodioApi.login()."""

    async def test_login_success(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
        mock_api_login_response: dict,
    ) -> None:
        """Test successful login."""
        mock_aiohttp_response.json.return_value = mock_api_login_response

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")
            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert api._access_token == "test_access_token_12345"
            assert api._expires_in is not None

    async def test_login_cached_token(self) -> None:
        """Test login with cached valid token."""
        api = QustodioApi("test@example.com", "password")
        api._access_token = "cached_token"
        api._expires_in = datetime.now().replace(year=2099)

        result = await api.login()

        assert result == LOGIN_RESULT_OK

    async def test_login_invalid_credentials(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test login with invalid credentials."""
        mock_aiohttp_response.status = 401

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "wrong_password")

            with pytest.raises(QustodioAuthenticationError, match="Invalid username or password"):
                await api.login()

    async def test_login_rate_limit(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test login with rate limit exceeded."""
        mock_aiohttp_response.status = 429

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioRateLimitError, match="API rate limit exceeded"):
                await api.login()

    async def test_login_api_error(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test login with API error."""
        mock_aiohttp_response.status = 500
        mock_aiohttp_response.text.return_value = "Internal Server Error"

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioAPIError, match="Login failed with status 500"):
                await api.login()

    async def test_login_missing_token(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test login with missing access token in response."""
        mock_aiohttp_response.json.return_value = {"expires_in": 3600}

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioDataError, match="Response missing access token"):
                await api.login()

    async def test_login_timeout(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test login with timeout."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioConnectionError, match="Connection timeout during login"):
                await api.login()

    async def test_login_connection_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test login with connection error."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioConnectionError, match="Connection error during login"):
                await api.login()


class TestQustodioApiGetData:
    """Tests for QustodioApi.get_data()."""

    async def test_get_data_success(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
        mock_api_login_response: dict,
        mock_api_account_response: dict,
        mock_api_profiles_response: list,
        mock_api_devices_response: list,
        mock_api_rules_response: dict,
        mock_api_hourly_summary_response: list,
    ) -> None:
        """Test successful data retrieval."""
        # Setup mock responses for all API calls
        login_response = Mock()
        login_response.__aenter__ = AsyncMock(return_value=login_response)
        login_response.__aexit__ = AsyncMock()
        login_response.status = 200
        login_response.json = AsyncMock(return_value=mock_api_login_response)

        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock()
        account_response.status = 200
        account_response.json = AsyncMock(return_value=mock_api_account_response)

        devices_response = Mock()
        devices_response.__aenter__ = AsyncMock(return_value=devices_response)
        devices_response.__aexit__ = AsyncMock()
        devices_response.status = 200
        devices_response.json = AsyncMock(return_value=mock_api_devices_response)

        profiles_response = Mock()
        profiles_response.__aenter__ = AsyncMock(return_value=profiles_response)
        profiles_response.__aexit__ = AsyncMock()
        profiles_response.status = 200
        profiles_response.json = AsyncMock(return_value=mock_api_profiles_response)

        rules_response = Mock()
        rules_response.__aenter__ = AsyncMock(return_value=rules_response)
        rules_response.__aexit__ = AsyncMock()
        rules_response.status = 200
        rules_response.json = AsyncMock(return_value=mock_api_rules_response)

        hourly_response = Mock()
        hourly_response.__aenter__ = AsyncMock(return_value=hourly_response)
        hourly_response.__aexit__ = AsyncMock()
        hourly_response.status = 200
        hourly_response.json = AsyncMock(return_value=mock_api_hourly_summary_response)

        mock_aiohttp_session.post = Mock(return_value=login_response)
        mock_aiohttp_session.get = Mock(
            side_effect=[
                account_response,
                devices_response,
                profiles_response,
                rules_response,
                hourly_response,
                rules_response,
                hourly_response,
            ]
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            api = QustodioApi("test@example.com", "password")
            data = await api.get_data()

            assert len(data) == 2
            assert "profile_1" in data
            assert "profile_2" in data
            assert data["profile_1"]["name"] == "Child One"
            assert data["profile_2"]["name"] == "Child Two"

    async def test_get_data_authentication_error(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test get_data with authentication error."""
        mock_aiohttp_response.status = 401

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "wrong_password")

            with pytest.raises(QustodioAuthenticationError):
                await api.get_data()

    async def test_get_data_connection_timeout(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test get_data with connection timeout."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioConnectionError, match="Connection timeout"):
                await api.get_data()

    async def test_get_data_profiles_not_list(
        self,
        mock_aiohttp_session: Mock,
        mock_api_login_response: dict,
        mock_api_account_response: dict,
        mock_api_devices_response: list,
    ) -> None:
        """Test get_data when profiles response is not a list."""
        login_response = Mock()
        login_response.__aenter__ = AsyncMock(return_value=login_response)
        login_response.__aexit__ = AsyncMock(return_value=None)
        login_response.status = 200
        login_response.json = AsyncMock(return_value=mock_api_login_response)

        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock(return_value=None)
        account_response.status = 200
        account_response.json = AsyncMock(return_value=mock_api_account_response)

        devices_response = Mock()
        devices_response.__aenter__ = AsyncMock(return_value=devices_response)
        devices_response.__aexit__ = AsyncMock(return_value=None)
        devices_response.status = 200
        devices_response.json = AsyncMock(return_value=mock_api_devices_response)

        profiles_response = Mock()
        profiles_response.__aenter__ = AsyncMock(return_value=profiles_response)
        profiles_response.__aexit__ = AsyncMock(return_value=None)
        profiles_response.status = 200
        profiles_response.json = AsyncMock(return_value={"not": "a list"})

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=login_response)
            mock_aiohttp_session.get = Mock(side_effect=[account_response, devices_response, profiles_response])

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioDataError, match="Profiles data is not a list"):
                await api.get_data()


class TestQustodioApiHelperMethods:
    """Tests for QustodioApi helper methods."""

    async def test_fetch_account_info_success(
        self,
        mock_aiohttp_session: Mock,
        mock_api_account_response: dict,
    ) -> None:
        """Test successful account info fetch."""
        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock()
        account_response.status = 200
        account_response.json = AsyncMock(return_value=mock_api_account_response)

        mock_aiohttp_session.get = Mock(return_value=account_response)

        api = QustodioApi("test@example.com", "password")
        await api._fetch_account_info(mock_aiohttp_session, {"Authorization": "Bearer token"})

        assert api._account_id == "account_123"
        assert api._account_uid == "account_uid_456"

    async def test_fetch_account_info_missing_id(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test account info fetch with missing id."""
        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock(return_value=None)
        account_response.status = 200
        account_response.json = AsyncMock(return_value={"email": "test@example.com"})

        mock_aiohttp_session.get = Mock(return_value=account_response)

        api = QustodioApi("test@example.com", "password")

        with pytest.raises(QustodioDataError, match="Account data missing required 'id' field"):
            await api._fetch_account_info(mock_aiohttp_session, {"Authorization": "Bearer token"})

    async def test_fetch_devices_success(
        self,
        mock_aiohttp_session: Mock,
        mock_api_devices_response: list,
    ) -> None:
        """Test successful devices fetch."""
        devices_response = Mock()
        devices_response.__aenter__ = AsyncMock(return_value=devices_response)
        devices_response.__aexit__ = AsyncMock()
        devices_response.status = 200
        devices_response.json = AsyncMock(return_value=mock_api_devices_response)

        mock_aiohttp_session.get = Mock(return_value=devices_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        devices = await api._fetch_devices(mock_aiohttp_session, {"Authorization": "Bearer token"})

        assert len(devices) == 2
        assert "device_1" in devices
        assert devices["device_1"]["name"] == "iPhone 12"

    async def test_fetch_devices_failure(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test devices fetch failure returns empty dict."""
        devices_response = Mock()
        devices_response.__aenter__ = AsyncMock(return_value=devices_response)
        devices_response.__aexit__ = AsyncMock()
        devices_response.status = 500

        mock_aiohttp_session.get = Mock(return_value=devices_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        devices = await api._fetch_devices(mock_aiohttp_session, {"Authorization": "Bearer token"})

        assert devices == {}

    async def test_check_device_tampering(self) -> None:
        """Test device tampering detection."""
        api = QustodioApi("test@example.com", "password")
        profile_data = {"id": "profile_1"}
        profile = {"device_ids": ["device_1"]}
        devices = {
            "device_1": {
                "name": "iPhone 12",
                "alerts": {
                    "unauthorized_remove": True,
                },
            }
        }

        api._check_device_tampering(profile_data, profile, devices)

        assert profile_data["unauthorized_remove"] is True
        assert profile_data["device_tampered"] == "iPhone 12"

    async def test_set_location_data_online(self) -> None:
        """Test setting location data for online profile."""
        api = QustodioApi("test@example.com", "password")
        profile_data = {"is_online": True}
        profile = {
            "status": {
                "is_online": True,
                "lastseen": "2025-11-23T10:30:00Z",
                "location": {
                    "device": "device_1",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "accuracy": 10,
                },
            }
        }
        devices = {"device_1": {"name": "iPhone 12"}}

        api._set_location_data(profile_data, profile, devices)

        assert profile_data["current_device"] == "iPhone 12"
        assert profile_data["latitude"] == 37.7749
        assert profile_data["longitude"] == -122.4194
        assert profile_data["accuracy"] == 10
        assert profile_data["lastseen"] == "2025-11-23T10:30:00Z"

    async def test_set_location_data_offline(self) -> None:
        """Test setting location data for offline profile."""
        api = QustodioApi("test@example.com", "password")
        profile_data = {"is_online": False}
        profile = {
            "status": {
                "is_online": False,
                "lastseen": "2025-11-23T09:00:00Z",
                "location": {},
            }
        }
        devices = {}

        api._set_location_data(profile_data, profile, devices)

        assert profile_data["current_device"] is None
        assert profile_data["latitude"] is None
        assert profile_data["longitude"] is None
