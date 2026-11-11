"""Tests for syncing device registry names from Qustodio data (real HA device registry)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.qustodio.const import DOMAIN
from custom_components.qustodio.device_names import async_sync_device_names, expected_device_name
from custom_components.qustodio.models import CoordinatorData, DeviceData, ProfileData


def _data(profile_name: str = "Jacob", device_name: str = "Jacob's School Mac") -> CoordinatorData:
    profile = ProfileData(id="11", uid="u11", name=profile_name, device_count=1, device_ids=[22], raw_data={})
    device = DeviceData.from_api_response({"id": 22, "name": device_name, "platform": 1})
    return CoordinatorData(profiles={"11": profile}, devices={"22": device})


def _entry(hass: HomeAssistant, entry_id: str = "entry_1") -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, entry_id=entry_id)
    entry.add_to_hass(hass)
    return entry


def _register(device_registry: dr.DeviceRegistry, entry: MockConfigEntry, ident: str, name: str) -> dr.DeviceEntry:
    return device_registry.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, ident)}, name=name)


class TestExpectedDeviceName:
    """Tests for expected_device_name()."""

    def test_expected_device_name_profile(self) -> None:
        """A profile identifier maps to the profile name."""
        assert expected_device_name("11", _data()) == "Jacob"

    def test_expected_device_name_device(self) -> None:
        """A profile_device identifier maps to '<profile> <device>' (same as device_info)."""
        assert expected_device_name("11_22", _data()) == "Jacob Jacob's School Mac"

    def test_expected_device_name_unknown_profile_returns_none(self) -> None:
        """Unknown profiles give None, so nothing is renamed."""
        assert expected_device_name("99", _data()) is None
        assert expected_device_name("99_22", _data()) is None

    def test_expected_device_name_unknown_device_returns_none(self) -> None:
        """Unknown devices give None, so nothing is renamed."""
        assert expected_device_name("11_99", _data()) is None


class TestSyncDeviceNames:
    """Tests for async_sync_device_names() against a real device registry."""

    async def test_sync_renames_profile_device(self, hass: HomeAssistant, device_registry: dr.DeviceRegistry) -> None:
        """A profile renamed in Qustodio renames its HA device."""
        entry = _entry(hass)
        device = _register(device_registry, entry, "11", "Old")

        async_sync_device_names(hass, entry.entry_id, _data(profile_name="New"))

        assert device_registry.async_get(device.id).name == "New"

    async def test_sync_renames_child_device(self, hass: HomeAssistant, device_registry: dr.DeviceRegistry) -> None:
        """A device renamed in Qustodio renames its HA device."""
        entry = _entry(hass)
        device = _register(device_registry, entry, "11_22", "Jacob Old Mac")

        async_sync_device_names(hass, entry.entry_id, _data())

        assert device_registry.async_get(device.id).name == "Jacob Jacob's School Mac"

    async def test_sync_keeps_name_by_user(self, hass: HomeAssistant, device_registry: dr.DeviceRegistry) -> None:
        """Only the integration's name changes; a name the user set in HA is kept."""
        entry = _entry(hass)
        device = _register(device_registry, entry, "11_22", "Jacob Old Mac")
        device_registry.async_update_device(device.id, name_by_user="Jacob's School Mac")

        async_sync_device_names(hass, entry.entry_id, _data(device_name="MacBook"))

        updated = device_registry.async_get(device.id)
        assert updated.name == "Jacob MacBook"
        assert updated.name_by_user == "Jacob's School Mac"

    async def test_sync_no_change_keeps_device_unmodified(
        self, hass: HomeAssistant, device_registry: dr.DeviceRegistry
    ) -> None:
        """Names that already match aren't rewritten."""
        entry = _entry(hass)
        device = _register(device_registry, entry, "11", "Jacob")
        before = device_registry.async_get(device.id).modified_at

        async_sync_device_names(hass, entry.entry_id, _data())

        assert device_registry.async_get(device.id).modified_at == before

    async def test_sync_ignores_other_config_entries(
        self, hass: HomeAssistant, device_registry: dr.DeviceRegistry
    ) -> None:
        """Devices belonging to another config entry are left alone."""
        ours, other = _entry(hass, "entry_1"), _entry(hass, "entry_2")
        foreign = _register(device_registry, other, "11", "Old")

        async_sync_device_names(hass, ours.entry_id, _data(profile_name="New"))

        assert device_registry.async_get(foreign.id).name == "Old"

    async def test_sync_ignores_unknown_and_foreign_identifiers(
        self, hass: HomeAssistant, device_registry: dr.DeviceRegistry
    ) -> None:
        """Devices with unknown ids or other domains' identifiers are left alone."""
        entry = _entry(hass)
        unknown = _register(device_registry, entry, "99", "Old")
        foreign = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={("other", "11")}, name="Old"
        )

        async_sync_device_names(hass, entry.entry_id, _data(profile_name="New"))

        assert device_registry.async_get(unknown.id).name == "Old"
        assert device_registry.async_get(foreign.id).name == "Old"
