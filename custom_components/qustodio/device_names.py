"""Keep Home Assistant device names in step with Qustodio profile and device names."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .models import CoordinatorData


def expected_device_name(identifier: str, data: CoordinatorData) -> str | None:
    """Return the name a Qustodio HA device should have, from the latest data.

    Args:
        identifier: The device's Qustodio identifier: ``"<profile_id>"`` for a
            profile device, ``"<profile_id>_<device_id>"`` for a child device.
        data: The latest coordinator data.

    Returns:
        The profile name, or ``"<profile name> <device name>"`` (the same format
        as ``QustodioDeviceEntity.device_info``); None if the profile or device
        isn't in the data.
    """
    if (profile := data.profiles.get(identifier)) is not None:
        return profile.name
    profile_id, _, device_id = identifier.partition("_")
    profile = data.profiles.get(profile_id)
    device = data.devices.get(device_id)
    if profile is None or device is None:
        return None
    return f"{profile.name} {device.name}"


@callback
def async_sync_device_names(hass: HomeAssistant, entry_id: str, data: CoordinatorData) -> None:
    """Rename this config entry's HA devices whose Qustodio name has changed.

    Only the integration-provided ``name`` is updated; a name the user set in HA
    (``name_by_user``) is left alone and keeps taking precedence.

    Args:
        hass: Home Assistant instance.
        entry_id: The Qustodio config entry id.
        data: The latest coordinator data.
    """
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry_id):
        for domain, identifier in device.identifiers:
            if domain != DOMAIN:
                continue
            expected = expected_device_name(identifier, data)
            if expected is not None and expected != device.name:
                registry.async_update_device(device.id, name=expected)
