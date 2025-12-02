"""Tests for Qustodio API client."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from custom_components.qustodio.const import LOGIN_RESULT_OK
from custom_components.qustodio.exceptions import (
    QustodioAPIError,
    QustodioAuthenticationError,
    QustodioConnectionError,
    QustodioDataError,
    QustodioRateLimitError,
)
from custom_components.qustodio.qustodioapi import QustodioApi, RetryConfig


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

    async def test_login_unexpected_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test login with unexpected error."""
        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(side_effect=ValueError("Unexpected error"))
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_response)

            api = QustodioApi("test@example.com", "password")

            with pytest.raises(QustodioAPIError, match="Unexpected error during login"):
                await api.login()


class TestQustodioApiRefreshToken:
    """Tests for QustodioApi refresh token flow."""

    async def test_login_with_refresh_token_success(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test successful login using refresh token."""
        # Initial login response with refresh token
        initial_login_response = {
            "access_token": "initial_access_token",
            "expires_in": 3600,
            "token_type": "bearer",
            "refresh_token": "test_refresh_token",
        }

        # Refresh token response
        refresh_response = {
            "access_token": "refreshed_access_token",
            "expires_in": 3600,
            "token_type": "bearer",
            "refresh_token": "new_refresh_token",
        }

        mock_aiohttp_response.json.side_effect = [initial_login_response, refresh_response]

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")

            # First login - get refresh token
            result = await api.login()
            assert result == LOGIN_RESULT_OK
            assert api._access_token == "initial_access_token"
            assert api._refresh_token == "test_refresh_token"

            # Expire the access token to force refresh
            api._access_token = None
            api._expires_in = None

            # Second login - use refresh token
            result = await api.login()
            assert result == LOGIN_RESULT_OK
            assert api._access_token == "refreshed_access_token"
            assert api._refresh_token == "new_refresh_token"

    async def test_login_stores_refresh_token(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test that refresh token is stored on login."""
        login_response = {
            "access_token": "test_access_token",
            "expires_in": 3600,
            "token_type": "bearer",
            "refresh_token": "test_refresh_token_12345",
        }
        mock_aiohttp_response.json.return_value = login_response

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")
            await api.login()

            assert api._refresh_token == "test_refresh_token_12345"

    async def test_refresh_token_fallback_to_password(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test fallback to password auth when refresh token fails."""
        # First response: refresh token fails with 401
        refresh_fail_response = Mock()
        refresh_fail_response.__aenter__ = AsyncMock(return_value=refresh_fail_response)
        refresh_fail_response.__aexit__ = AsyncMock(return_value=None)
        refresh_fail_response.status = 401
        refresh_fail_response.text = AsyncMock(return_value="Unauthorized")

        # Second response: password auth succeeds
        password_success_response = Mock()
        password_success_response.__aenter__ = AsyncMock(return_value=password_success_response)
        password_success_response.__aexit__ = AsyncMock(return_value=None)
        password_success_response.status = 200
        password_success_response.json = AsyncMock(
            return_value={
                "access_token": "new_access_token",
                "expires_in": 3600,
                "token_type": "bearer",
                "refresh_token": "new_refresh_token",
            }
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(side_effect=[refresh_fail_response, password_success_response])

            api = QustodioApi("test@example.com", "password")
            api._refresh_token = "expired_refresh_token"

            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert api._access_token == "new_access_token"
            assert api._refresh_token == "new_refresh_token"

    async def test_refresh_token_clears_invalid_token(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test that invalid refresh token is cleared."""
        # Refresh token fails with 401
        refresh_fail_response = Mock()
        refresh_fail_response.__aenter__ = AsyncMock(return_value=refresh_fail_response)
        refresh_fail_response.__aexit__ = AsyncMock(return_value=None)
        refresh_fail_response.status = 401
        refresh_fail_response.text = AsyncMock(return_value="Unauthorized")

        # Password auth succeeds
        password_success_response = Mock()
        password_success_response.__aenter__ = AsyncMock(return_value=password_success_response)
        password_success_response.__aexit__ = AsyncMock(return_value=None)
        password_success_response.status = 200
        password_success_response.json = AsyncMock(
            return_value={
                "access_token": "new_access_token",
                "expires_in": 3600,
                "token_type": "bearer",
            }
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(side_effect=[refresh_fail_response, password_success_response])

            api = QustodioApi("test@example.com", "password")
            api._refresh_token = "invalid_refresh_token"

            await api.login()

            # Refresh token should be cleared after 401
            assert api._refresh_token is None

    async def test_refresh_token_no_token_falls_back(
        self,
        mock_aiohttp_session: Mock,
        mock_aiohttp_response: Mock,
    ) -> None:
        """Test that login without refresh token uses password auth."""
        login_response = {
            "access_token": "test_access_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        mock_aiohttp_response.json.return_value = login_response

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=mock_aiohttp_response)

            api = QustodioApi("test@example.com", "password")
            api._refresh_token = None

            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert api._access_token == "test_access_token"

    async def test_refresh_token_rate_limit_fallback(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test fallback to password auth when refresh token hits rate limit."""
        # Refresh token fails with rate limit
        refresh_fail_response = Mock()
        refresh_fail_response.__aenter__ = AsyncMock(return_value=refresh_fail_response)
        refresh_fail_response.__aexit__ = AsyncMock(return_value=None)
        refresh_fail_response.status = 429
        refresh_fail_response.text = AsyncMock(return_value="Rate limit exceeded")

        # Password auth succeeds
        password_success_response = Mock()
        password_success_response.__aenter__ = AsyncMock(return_value=password_success_response)
        password_success_response.__aexit__ = AsyncMock(return_value=None)
        password_success_response.status = 200
        password_success_response.json = AsyncMock(
            return_value={
                "access_token": "new_access_token",
                "expires_in": 3600,
                "token_type": "bearer",
            }
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(side_effect=[refresh_fail_response, password_success_response])

            api = QustodioApi("test@example.com", "password")
            api._refresh_token = "valid_refresh_token"

            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert api._access_token == "new_access_token"
            # Refresh token should still be there (wasn't invalidated, just rate limited)
            assert api._refresh_token == "valid_refresh_token"


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

            # Check it's CoordinatorData
            assert hasattr(data, "profiles")
            assert hasattr(data, "devices")
            # Check profile data
            assert len(data.profiles) == 2
            assert "profile_1" in data.profiles
            assert "profile_2" in data.profiles
            assert data.profiles["profile_1"].name == "Child One"
            assert data.profiles["profile_2"].name == "Child Two"
            # Check device data
            assert len(data.devices) == 2

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

    async def test_fetch_account_info_token_expired(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test account info fetch with expired token."""
        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock(return_value=None)
        account_response.status = 401

        mock_aiohttp_session.get = Mock(return_value=account_response)

        api = QustodioApi("test@example.com", "password")

        with pytest.raises(QustodioAuthenticationError, match="Token expired or invalid"):
            await api._fetch_account_info(mock_aiohttp_session, {"Authorization": "Bearer token"})

    async def test_fetch_account_info_rate_limit(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test account info fetch with rate limit."""
        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock(return_value=None)
        account_response.status = 429

        mock_aiohttp_session.get = Mock(return_value=account_response)

        api = QustodioApi("test@example.com", "password")

        with pytest.raises(QustodioRateLimitError, match="API rate limit exceeded"):
            await api._fetch_account_info(mock_aiohttp_session, {"Authorization": "Bearer token"})

    async def test_fetch_account_info_http_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test account info fetch with HTTP error."""
        account_response = Mock()
        account_response.__aenter__ = AsyncMock(return_value=account_response)
        account_response.__aexit__ = AsyncMock(return_value=None)
        account_response.status = 500

        mock_aiohttp_session.get = Mock(return_value=account_response)

        api = QustodioApi("test@example.com", "password")

        with pytest.raises(QustodioAPIError, match="Failed to get account info: HTTP 500"):
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

    async def test_fetch_devices_connection_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test devices fetch with connection error returns empty dict."""
        devices_response = Mock()
        devices_response.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        devices_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.get = Mock(return_value=devices_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        devices = await api._fetch_devices(mock_aiohttp_session, {"Authorization": "Bearer token"})

        assert devices == {}

    async def test_fetch_profiles_token_expired(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test profiles fetch with expired token."""
        profiles_response = Mock()
        profiles_response.__aenter__ = AsyncMock(return_value=profiles_response)
        profiles_response.__aexit__ = AsyncMock(return_value=None)
        profiles_response.status = 401

        mock_aiohttp_session.get = Mock(return_value=profiles_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        with pytest.raises(QustodioAuthenticationError, match="Token expired or invalid"):
            await api._fetch_profiles(mock_aiohttp_session, {"Authorization": "Bearer token"})

    async def test_fetch_profiles_rate_limit(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test profiles fetch with rate limit."""
        profiles_response = Mock()
        profiles_response.__aenter__ = AsyncMock(return_value=profiles_response)
        profiles_response.__aexit__ = AsyncMock(return_value=None)
        profiles_response.status = 429

        mock_aiohttp_session.get = Mock(return_value=profiles_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        with pytest.raises(QustodioRateLimitError, match="API rate limit exceeded"):
            await api._fetch_profiles(mock_aiohttp_session, {"Authorization": "Bearer token"})

    async def test_fetch_profiles_http_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test profiles fetch with HTTP error."""
        profiles_response = Mock()
        profiles_response.__aenter__ = AsyncMock(return_value=profiles_response)
        profiles_response.__aexit__ = AsyncMock(return_value=None)
        profiles_response.status = 500

        mock_aiohttp_session.get = Mock(return_value=profiles_response)

        api = QustodioApi("test@example.com", "password")
        api._account_id = "account_123"

        with pytest.raises(QustodioAPIError, match="Failed to get profiles: HTTP 500"):
            await api._fetch_profiles(mock_aiohttp_session, {"Authorization": "Bearer token"})

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


class TestQustodioApiSessionManagement:
    """Tests for session management."""

    async def test_get_session_creates_new_session(self) -> None:
        """Test that _get_session creates a new session if none exists."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(timeout=30))

        assert api._session is None

        session = await api._get_session()

        assert session is not None
        assert api._session is session
        assert session._timeout.total == 30

        await api.close()

    async def test_get_session_reuses_existing_session(self) -> None:
        """Test that _get_session reuses existing session."""
        api = QustodioApi("test@example.com", "password")

        session1 = await api._get_session()
        session2 = await api._get_session()

        assert session1 is session2

        await api.close()

    async def test_close_session(self) -> None:
        """Test that close properly closes the session."""
        api = QustodioApi("test@example.com", "password")

        session = await api._get_session()
        assert not session.closed

        await api.close()

        assert session.closed
        assert api._session is None

    async def test_close_session_when_none(self) -> None:
        """Test that close works when no session exists."""
        api = QustodioApi("test@example.com", "password")

        # Should not raise
        await api.close()

        assert api._session is None

    async def test_close_session_already_closed(self) -> None:
        """Test that close works when session already closed."""
        api = QustodioApi("test@example.com", "password")

        session = await api._get_session()
        await session.close()

        # Close sets session to None even if already closed
        await api.close()

        # Session should be set to None after close
        assert api._session is None or api._session.closed


class TestQustodioApiRetryLogic:
    """Tests for retry logic."""

    def test_should_retry_connection_error(self) -> None:
        """Test retry on connection error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error = QustodioConnectionError("Connection failed")
        assert api._should_retry(error, 1) is True
        assert api._should_retry(error, 2) is True
        assert api._should_retry(error, 3) is False

    def test_should_retry_timeout_error(self) -> None:
        """Test retry on timeout error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error = asyncio.TimeoutError()
        assert api._should_retry(error, 1) is True
        assert api._should_retry(error, 2) is True
        assert api._should_retry(error, 3) is False

    def test_should_retry_rate_limit_error(self) -> None:
        """Test retry on rate limit error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error = QustodioRateLimitError("Rate limit exceeded")
        assert api._should_retry(error, 1) is True
        assert api._should_retry(error, 2) is True
        assert api._should_retry(error, 3) is False

    def test_should_not_retry_authentication_error(self) -> None:
        """Test no retry on authentication error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error = QustodioAuthenticationError("Invalid credentials")
        assert api._should_retry(error, 1) is False
        assert api._should_retry(error, 2) is False

    def test_should_retry_server_error_5xx(self) -> None:
        """Test retry on server errors (5xx)."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error_500 = QustodioAPIError("Server error", status_code=500)
        error_502 = QustodioAPIError("Bad gateway", status_code=502)
        error_503 = QustodioAPIError("Service unavailable", status_code=503)

        assert api._should_retry(error_500, 1) is True
        assert api._should_retry(error_502, 1) is True
        assert api._should_retry(error_503, 1) is True

    def test_should_not_retry_client_error_4xx(self) -> None:
        """Test no retry on client errors (4xx)."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        error_400 = QustodioAPIError("Bad request", status_code=400)
        error_404 = QustodioAPIError("Not found", status_code=404)

        assert api._should_retry(error_400, 1) is False
        assert api._should_retry(error_404, 1) is False

    async def test_retry_delay_exponential_backoff(self) -> None:
        """Test exponential backoff delay calculation."""
        api = QustodioApi(
            "test@example.com",
            "password",
            retry_config=RetryConfig(base_delay=1.0, max_delay=10.0),
        )

        # Mock sleep to capture delay values
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await api._retry_delay(1)
            await api._retry_delay(2)
            await api._retry_delay(3)

        # First delay: base_delay * (2^0) = 1.0 ± jitter
        assert 0.75 <= delays[0] <= 1.25

        # Second delay: base_delay * (2^1) = 2.0 ± jitter
        assert 1.5 <= delays[1] <= 2.5

        # Third delay: base_delay * (2^2) = 4.0 ± jitter
        assert 3.0 <= delays[2] <= 5.0

    async def test_retry_delay_max_delay_cap(self) -> None:
        """Test retry delay is capped at max_delay."""
        api = QustodioApi(
            "test@example.com",
            "password",
            retry_config=RetryConfig(base_delay=10.0, max_delay=15.0),
        )

        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await api._retry_delay(5)  # Would be 10 * (2^4) = 160 without cap

        # Should be capped at max_delay (15.0) ± jitter
        assert delays[0] <= 18.75  # 15.0 + 25% jitter

    async def test_login_retry_on_timeout(
        self,
        mock_aiohttp_session: Mock,
        mock_api_login_response: dict,
    ) -> None:
        """Test login retries on timeout."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3, base_delay=0.01))

        # First two attempts timeout, third succeeds
        timeout_response = Mock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_response.__aexit__ = AsyncMock(return_value=None)

        success_response = Mock()
        success_response.__aenter__ = AsyncMock(return_value=success_response)
        success_response.__aexit__ = AsyncMock(return_value=None)
        success_response.status = 200
        success_response.json = AsyncMock(return_value=mock_api_login_response)

        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(side_effect=[timeout_response, timeout_response, success_response])

            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert mock_aiohttp_session.post.call_count == 3

        await api.close()

    async def test_login_retry_on_server_error(
        self,
        mock_aiohttp_session: Mock,
        mock_api_login_response: dict,
    ) -> None:
        """Test login retries on server error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3, base_delay=0.01))

        # First attempt returns 500, second succeeds
        error_response = Mock()
        error_response.__aenter__ = AsyncMock(return_value=error_response)
        error_response.__aexit__ = AsyncMock(return_value=None)
        error_response.status = 500
        error_response.text = AsyncMock(return_value="Internal Server Error")

        success_response = Mock()
        success_response.__aenter__ = AsyncMock(return_value=success_response)
        success_response.__aexit__ = AsyncMock(return_value=None)
        success_response.status = 200
        success_response.json = AsyncMock(return_value=mock_api_login_response)

        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(side_effect=[error_response, success_response])

            result = await api.login()

            assert result == LOGIN_RESULT_OK
            assert mock_aiohttp_session.post.call_count == 2

        await api.close()

    async def test_login_no_retry_on_auth_error(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test login does not retry on authentication error."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3))

        auth_error_response = Mock()
        auth_error_response.__aenter__ = AsyncMock(return_value=auth_error_response)
        auth_error_response.__aexit__ = AsyncMock(return_value=None)
        auth_error_response.status = 401

        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=auth_error_response)

            with pytest.raises(QustodioAuthenticationError):
                await api.login()

            # Should only attempt once
            assert mock_aiohttp_session.post.call_count == 1

        await api.close()

    async def test_login_exhausts_retries(
        self,
        mock_aiohttp_session: Mock,
    ) -> None:
        """Test login raises error after exhausting retries."""
        api = QustodioApi("test@example.com", "password", retry_config=RetryConfig(max_attempts=3, base_delay=0.01))

        timeout_response = Mock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        timeout_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            mock_aiohttp_session.post = Mock(return_value=timeout_response)

            with pytest.raises(QustodioConnectionError, match="Connection timeout during login"):
                await api.login()

            # Should attempt exactly 3 times
            assert mock_aiohttp_session.post.call_count == 3

        await api.close()

    async def test_custom_retry_parameters(self) -> None:
        """Test API client accepts custom retry parameters."""
        config = RetryConfig(
            timeout=60,
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
        )
        api = QustodioApi("test@example.com", "password", retry_config=config)

        assert api._retry_config.timeout == 60
        assert api._retry_config.max_attempts == 5
        assert api._retry_config.base_delay == 2.0
        assert api._retry_config.max_delay == 60.0

        await api.close()


class TestQustodioApiGetAppUsage:
    """Tests for QustodioApi.get_app_usage() method."""

    @pytest.mark.asyncio
    async def test_get_app_usage_success(self, mock_aiohttp_session, mock_aiohttp_response) -> None:
        """Test get_app_usage returns app usage data successfully."""
        from datetime import date

        api = QustodioApi("test@example.com", "password")

        # Mock response data
        app_usage_data = {
            "items": [
                {
                    "app_name": "Clash Royale",
                    "exe": "com.supercell.scroll",
                    "minutes": 11,
                    "platform": 4,
                    "thumbnail": "https://static.qustodio.com/app/icon.jpg",
                    "questionable": False,
                },
                {
                    "app_name": "Microsoft Teams",
                    "exe": "com.microsoft.teams2",
                    "minutes": 4,
                    "platform": 1,
                },
            ],
            "questionable_count": 0,
        }

        mock_aiohttp_response.status = 200
        mock_aiohttp_response.json = AsyncMock(return_value=app_usage_data)
        mock_aiohttp_session.get = Mock(return_value=mock_aiohttp_response)

        # Patch _get_session and login to avoid real API calls
        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            with patch.object(api, "login", new_callable=AsyncMock):
                api._access_token = "test_token"
                api._account_uid = "account_uid_123"

                result = await api.get_app_usage("profile_uid_123", date(2025, 12, 2), date(2025, 12, 2))

                # Verify result
                assert result == app_usage_data
                assert len(result["items"]) == 2
                assert result["items"][0]["app_name"] == "Clash Royale"
                assert result["questionable_count"] == 0

                # Verify API call
                mock_aiohttp_session.get.assert_called_once()
                call_args = mock_aiohttp_session.get.call_args
                assert (
                    "/v2/accounts/account_uid_123/profiles/profile_uid_123/summary/domains-and-apps" in call_args[0][0]
                )

        await api.close()

    @pytest.mark.asyncio
    async def test_get_app_usage_missing_account_uid(self, mock_aiohttp_session) -> None:
        """Test get_app_usage raises QustodioDataError when account_uid is missing."""
        from datetime import date

        api = QustodioApi("test@example.com", "password")

        # Patch _get_session and login to avoid real API calls
        with patch.object(api, "_get_session", return_value=mock_aiohttp_session):
            with patch.object(api, "login", new_callable=AsyncMock):
                api._access_token = "test_token"
                api._account_uid = None  # Missing account_uid

                with pytest.raises(QustodioDataError) as exc_info:
                    await api.get_app_usage("profile_uid_123", date(2025, 12, 2), date(2025, 12, 2))

                assert "Account UID not available" in str(exc_info.value)

        await api.close()
