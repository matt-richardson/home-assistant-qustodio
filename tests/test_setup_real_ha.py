"""End-to-end setup tests on a real Home Assistant (pytest-homeassistant-custom-component)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.qustodio.const import DOMAIN

from .sample_data import build_coordinator_data

ENTRY_DATA = {
    CONF_USERNAME: "test@example.com",
    CONF_PASSWORD: "test_password",
    "profiles": {
        "profile_1": {"id": "profile_1", "uid": "uid_1", "name": "Child One"},
        "profile_2": {"id": "profile_2", "uid": "uid_2", "name": "Child Two"},
    },
}


def _api() -> AsyncMock:
    """Return a Qustodio API stand-in serving the shared sample data."""
    api = AsyncMock()
    api.get_data.return_value = build_coordinator_data()
    api.get_app_usage.return_value = {"items": []}
    api.get_active_restriction.return_value = None
    return api


async def test_setup_registers_devices_and_entities(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Setting up the entry loads it and registers profile devices and their entities."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="entry_1")
    entry.add_to_hass(hass)

    with patch("custom_components.qustodio.QustodioApi", return_value=_api()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    device_id = dr.async_get_device_id_by_identifier(hass, (DOMAIN, "profile_1"), config_entry_id=entry.entry_id)
    profile_device = device_registry.async_get(device_id)
    assert profile_device is not None
    assert profile_device.name == "Child One"
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert any(e.unique_id == f"{DOMAIN}_time_remaining_profile_1" for e in entities)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _device_name(hass: HomeAssistant, device_registry: dr.DeviceRegistry, entry: MockConfigEntry, ident: str) -> str:
    device_id = dr.async_get_device_id_by_identifier(hass, (DOMAIN, ident), config_entry_id=entry.entry_id)
    return device_registry.async_get(device_id).name


async def test_restart_after_qustodio_rename_uses_current_names(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    device_registry: dr.DeviceRegistry,
) -> None:
    """After a profile is renamed in Qustodio, a restart registers devices under the new name immediately.

    The config entry still holds the setup-time profile name, so this guards against setup
    re-registering devices with the stale name until the next poll.
    """
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="entry_1")
    entry.add_to_hass(hass)
    api = _api()

    with patch("custom_components.qustodio.QustodioApi", return_value=api):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert _device_name(hass, device_registry, entry, "profile_1_device_1") == "Child One iPhone 12"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        renamed = build_coordinator_data()
        renamed.profiles["profile_1"].name = "Renamed Child"
        api.get_data.return_value = renamed

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert _device_name(hass, device_registry, entry, "profile_1") == "Renamed Child"
    assert _device_name(hass, device_registry, entry, "profile_1_device_1") == "Renamed Child iPhone 12"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
