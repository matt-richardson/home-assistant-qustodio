"""Tests for syncing device registry names from Qustodio data."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from custom_components.qustodio.const import DOMAIN
from custom_components.qustodio.device_names import async_sync_device_names, expected_device_name
from custom_components.qustodio.models import CoordinatorData, DeviceData, ProfileData


def _data(profile_name: str = "Jacob", device_name: str = "Jacob's School Mac") -> CoordinatorData:
    profile = ProfileData(id="11", uid="u11", name=profile_name, device_count=1, device_ids=[22], raw_data={})
    device = DeviceData.from_api_response({"id": 22, "name": device_name, "platform": 1})
    return CoordinatorData(profiles={"11": profile}, devices={"22": device})


def _entry(device_id: str, ident: str, name: str, name_by_user: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=device_id, identifiers={(DOMAIN, ident)}, name=name, name_by_user=name_by_user)


def _sync(entries: list[SimpleNamespace], data: CoordinatorData) -> Mock:
    """Run the sync against a mocked registry holding ``entries``; return the registry."""
    registry = Mock()
    with (
        patch("custom_components.qustodio.device_names.dr.async_get", return_value=registry),
        patch(
            "custom_components.qustodio.device_names.dr.async_entries_for_config_entry", return_value=entries
        ) as entries_for,
    ):
        async_sync_device_names(Mock(), "entry_1", data)
    entries_for.assert_called_once_with(registry, "entry_1")
    return registry


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
    """Tests for async_sync_device_names()."""

    def test_sync_renames_profile_device(self) -> None:
        """A profile renamed in Qustodio renames its HA device."""
        registry = _sync([_entry("d1", "11", "Old")], _data(profile_name="New"))
        registry.async_update_device.assert_called_once_with("d1", name="New")

    def test_sync_renames_child_device(self) -> None:
        """A device renamed in Qustodio renames its HA device."""
        registry = _sync([_entry("d2", "11_22", "Jacob Old Mac")], _data())
        registry.async_update_device.assert_called_once_with("d2", name="Jacob Jacob's School Mac")

    def test_sync_keeps_name_by_user(self) -> None:
        """Only the integration's name changes; a name the user set in HA is never touched."""
        registry = _sync([_entry("d2", "11_22", "Jacob Old Mac", name_by_user="Jacob's School Mac")], _data())
        registry.async_update_device.assert_called_once_with("d2", name="Jacob Jacob's School Mac")

    def test_sync_no_change_makes_no_update(self) -> None:
        """Names that already match aren't rewritten."""
        registry = _sync([_entry("d1", "11", "Jacob"), _entry("d2", "11_22", "Jacob Jacob's School Mac")], _data())
        registry.async_update_device.assert_not_called()

    def test_sync_ignores_unknown_and_foreign_identifiers(self) -> None:
        """Devices with unknown ids or other domains' identifiers are left alone."""
        foreign = SimpleNamespace(id="d9", identifiers={("other", "11")}, name="Old", name_by_user=None)
        registry = _sync([foreign, _entry("d8", "99", "Old")], _data())
        registry.async_update_device.assert_not_called()
