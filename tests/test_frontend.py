"""Tests for serving and registering the screen time card (real Home Assistant)."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.qustodio.const import CARD_FILENAME, DOMAIN, FRONTEND_URL_BASE
from custom_components.qustodio.frontend import async_register_frontend

from .sample_data import build_coordinator_data
from .test_setup_real_ha import ENTRY_DATA

CARD_URL = f"{FRONTEND_URL_BASE}/{CARD_FILENAME}"


def _api() -> AsyncMock:
    api = AsyncMock()
    api.get_data.return_value = build_coordinator_data()
    api.get_app_usage.return_value = {"items": []}
    api.get_active_restriction.return_value = None
    return api


@pytest.fixture
def frontend_loaded(hass: HomeAssistant) -> Mock:
    """Pretend the frontend component is loaded and capture extra module registrations."""
    hass.config.components.add("frontend")
    with patch("custom_components.qustodio.frontend.add_extra_js_url") as add:
        yield add


async def _setup_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="entry_1")
    entry.add_to_hass(hass)
    with patch("custom_components.qustodio.QustodioApi", return_value=_api()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_card_served(
    hass: HomeAssistant, enable_custom_integrations: None, frontend_loaded: Mock, hass_client
) -> None:
    """The card's JavaScript is served from the integration's static path."""
    await _setup_entry(hass)
    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    assert 'const CARD_TYPE = "qustodio-screen-time-card"' in await response.text()
    logic = await client.get(f"{FRONTEND_URL_BASE}/card-logic.js")
    assert logic.status == 200
    assert "export function renderCard" in await logic.text()


async def test_card_registered_as_module(
    hass: HomeAssistant, enable_custom_integrations: None, frontend_loaded: Mock
) -> None:
    """The card is registered as an extra frontend module, with a version for cache busting."""
    await _setup_entry(hass)
    frontend_loaded.assert_called_once()
    url = frontend_loaded.call_args.args[1]
    assert url.startswith(f"{CARD_URL}?v=")
    assert len(url) > len(f"{CARD_URL}?v=")


async def test_register_frontend_once(
    hass: HomeAssistant, enable_custom_integrations: None, frontend_loaded: Mock
) -> None:
    """Registering again (another entry or a reload) doesn't register twice."""
    await _setup_entry(hass)
    with patch.object(hass.http, "async_register_static_paths", AsyncMock()) as register_paths:
        await async_register_frontend(hass)
    register_paths.assert_not_awaited()
    frontend_loaded.assert_called_once()


async def test_card_not_registered_without_frontend(hass: HomeAssistant, enable_custom_integrations: None) -> None:
    """Without the frontend component (e.g. a headless install) setup still works and nothing is registered."""
    with patch("custom_components.qustodio.frontend.add_extra_js_url") as add:
        await _setup_entry(hass)
    add.assert_not_called()
