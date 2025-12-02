"""Tests for Qustodio diagnostics."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import Mock, patch

import pytest

from custom_components.qustodio.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
def mock_coordinator_with_data(mock_coordinator: Mock) -> Mock:
    """Create a mock coordinator with successful data."""
    mock_coordinator.last_update_success = True
    mock_coordinator.last_update_time = datetime(2025, 11, 25, 10, 30, 0)
    mock_coordinator.last_exception = None
    return mock_coordinator


@pytest.fixture
def mock_coordinator_with_error(mock_coordinator: Mock) -> Mock:
    """Create a mock coordinator with an error."""
    mock_coordinator.last_update_success = False
    mock_coordinator.last_update_time = datetime(2025, 11, 25, 10, 30, 0)
    mock_coordinator.last_exception = Exception("Test error")
    mock_coordinator.data = None
    return mock_coordinator


@pytest.fixture
def mock_entity_registry_patches():
    """Provide patches for entity registry."""
    with (
        patch(
            "custom_components.qustodio.diagnostics.er.async_get",
            return_value=Mock(),
        ) as mock_async_get,
        patch(
            "custom_components.qustodio.diagnostics.er.async_entries_for_config_entry",
            return_value=[],
        ) as mock_entries,
    ):
        yield mock_async_get, mock_entries


class TestDiagnostics:
    """Test diagnostics functionality."""

    async def test_diagnostics_basic_structure(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test basic diagnostics structure."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert "config_entry" in diagnostics
        assert "coordinator" in diagnostics
        assert "entities" in diagnostics
        assert "profiles" in diagnostics
        assert "profile_count" in diagnostics

    async def test_diagnostics_config_entry_data(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test config entry data in diagnostics."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert config entry
        assert diagnostics["config_entry"]["title"] == "Qustodio (test@example.com)"
        assert diagnostics["config_entry"]["version"] == 1
        assert diagnostics["config_entry"]["minor_version"] == 1
        assert diagnostics["config_entry"]["source"] == "user"

        # Assert sensitive data is redacted
        assert diagnostics["config_entry"]["data"]["username"] == "**REDACTED**"
        assert diagnostics["config_entry"]["data"]["password"] == "**REDACTED**"

    async def test_diagnostics_coordinator_data(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test coordinator data in diagnostics."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert coordinator
        assert diagnostics["coordinator"]["last_update_success"] is True
        assert diagnostics["coordinator"]["last_update_time"] == "2025-11-28T12:00:00+00:00"
        assert "update_interval_seconds" in diagnostics["coordinator"]
        assert diagnostics["coordinator"]["name"] is not None

    async def test_diagnostics_profile_data(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test profile data in diagnostics."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert profiles
        assert diagnostics["profile_count"] == 2
        assert len(diagnostics["profiles"]) == 2

        # Check profile summary
        profile1 = diagnostics["profiles"][0]
        assert profile1["profile_id"] == "**REDACTED**"
        assert profile1["name"] == "Child One"
        assert profile1["is_online"] is True
        assert profile1["has_location"] is True
        assert profile1["time_used_minutes"] == 120
        assert profile1["quota_minutes"] == 300

        # Assert full profile data is redacted
        assert "profile_data_full" in diagnostics
        profile_data = diagnostics["profile_data_full"]["profile_1"]
        assert profile_data["id"] == "**REDACTED**"
        assert profile_data["uid"] == "**REDACTED**"
        assert profile_data["latitude"] == "**REDACTED**"
        assert profile_data["longitude"] == "**REDACTED**"
        assert profile_data["lastseen"] == "**REDACTED**"

    async def test_diagnostics_with_error(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_error: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test diagnostics when coordinator has an error."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_error}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert diagnostics["coordinator"]["last_update_success"] is False
        assert "last_update_error" in diagnostics
        assert diagnostics["last_update_error"]["error"] == "Test error"
        assert diagnostics["last_update_error"]["error_type"] == "Exception"
        assert diagnostics["profile_count"] == 0
        assert diagnostics["profiles"] == []
        assert diagnostics["profile_data_full"] is None

    async def test_diagnostics_entities(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test entity information in diagnostics."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Mock entity registry
        mock_entity = Mock()
        mock_entity.entity_id = "sensor.child_one"
        mock_entity.name = "Child One"
        mock_entity.original_name = "Child One"
        mock_entity.platform = "qustodio"
        mock_entity.disabled = False
        mock_entity.disabled_by = None

        mock_entity_registry = Mock()
        mock_entity_registry.entities = {mock_entity.entity_id: mock_entity}

        # Patch the entity registry
        from unittest.mock import patch

        with (
            patch(
                "custom_components.qustodio.diagnostics.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch(
                "custom_components.qustodio.diagnostics.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
        ):
            # Execute
            diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert len(diagnostics["entities"]) == 1
        entity = diagnostics["entities"][0]
        assert entity["entity_id"] == "sensor.child_one"
        assert entity["name"] == "Child One"
        assert entity["platform"] == "qustodio"
        assert entity["disabled"] is False
        assert entity["disabled_by"] is None

    async def test_diagnostics_no_data(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test diagnostics when coordinator has no data."""
        # Setup
        mock_coordinator.last_update_success = True
        mock_coordinator.data = None
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert diagnostics["profile_count"] == 0
        assert diagnostics["profiles"] == []
        assert diagnostics["profile_data_full"] is None

    async def test_diagnostics_redacts_sensitive_fields(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test that sensitive fields are properly redacted."""
        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Check that sensitive fields are redacted in profile data
        for profile_id, profile_data in diagnostics["profile_data_full"].items():
            # These should be redacted
            if "id" in profile_data:
                assert profile_data["id"] == "**REDACTED**"
            if "uid" in profile_data:
                assert profile_data["uid"] == "**REDACTED**"
            if "latitude" in profile_data and profile_data["latitude"] is not None:
                assert profile_data["latitude"] == "**REDACTED**"
            if "longitude" in profile_data and profile_data["longitude"] is not None:
                assert profile_data["longitude"] == "**REDACTED**"
            if "lastseen" in profile_data and profile_data["lastseen"] is not None:
                assert profile_data["lastseen"] == "**REDACTED**"

            # These should NOT be redacted
            assert isinstance(profile_data["name"], str)
            assert isinstance(profile_data["is_online"], bool)

    async def test_diagnostics_app_usage_summary(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test app usage summary in diagnostics."""
        from custom_components.qustodio.models import AppUsage

        # Add app usage data to coordinator
        mock_coordinator_with_data.data.app_usage = {
            "profile_1": [
                AppUsage(name="YouTube", package="com.google.youtube", minutes=45.5, platform=3, questionable=True),
                AppUsage(
                    name="Minecraft", package="com.mojang.minecraft", minutes=30.0, platform=3, questionable=False
                ),
                AppUsage(name="WhatsApp", package="com.whatsapp", minutes=15.2, platform=3, questionable=False),
            ],
            "profile_2": [
                AppUsage(
                    name="TikTok", package="com.zhiliaoapp.musically", minutes=60.0, platform=4, questionable=True
                ),
            ],
        }
        mock_coordinator_with_data._last_app_fetch_date = datetime(2025, 12, 2, 10, 0, 0)

        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert app usage is present
        assert "app_usage" in diagnostics
        assert diagnostics["app_usage"] is not None
        assert "app_usage_cache_date" in diagnostics

        # Check app usage summary for profile 1
        assert "Child One" in diagnostics["app_usage"]
        profile1_usage = diagnostics["app_usage"]["Child One"]
        assert profile1_usage["total_apps"] == 3
        assert profile1_usage["total_minutes"] == 90.7  # 45.5 + 30.0 + 15.2
        assert profile1_usage["questionable_apps"] == 1
        assert len(profile1_usage["top_5_apps"]) == 3

        # Check top app details
        top_app = profile1_usage["top_5_apps"][0]
        assert top_app["name"] == "YouTube"
        assert top_app["minutes"] == 45.5
        assert top_app["platform"] == 3
        assert top_app["questionable"] is True

        # Check profile 2
        assert "Child Two" in diagnostics["app_usage"]
        profile2_usage = diagnostics["app_usage"]["Child Two"]
        assert profile2_usage["total_apps"] == 1
        assert profile2_usage["total_minutes"] == 60.0
        assert profile2_usage["questionable_apps"] == 1

    async def test_diagnostics_app_usage_no_data(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test diagnostics when there's no app usage data."""
        # No app usage data
        mock_coordinator_with_data.data.app_usage = None
        mock_coordinator_with_data._last_app_fetch_date = None

        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert "app_usage" in diagnostics
        assert diagnostics["app_usage"] is None
        assert diagnostics["app_usage_cache_date"] is None

    async def test_diagnostics_app_usage_empty(
        self,
        hass: Any,
        mock_config_entry: Mock,
        mock_coordinator_with_data: Mock,
        mock_entity_registry_patches: Any,
    ) -> None:
        """Test diagnostics when app usage is an empty dict."""
        # Empty app usage data
        mock_coordinator_with_data.data.app_usage = {}
        mock_coordinator_with_data._last_app_fetch_date = datetime(2025, 12, 2, 10, 0, 0)

        # Setup
        hass.data = {"qustodio": {mock_config_entry.entry_id: mock_coordinator_with_data}}

        # Execute
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Assert
        assert "app_usage" in diagnostics
        assert diagnostics["app_usage"] is None  # Empty dict becomes None
        assert diagnostics["app_usage_cache_date"] == "2025-12-02T10:00:00"
