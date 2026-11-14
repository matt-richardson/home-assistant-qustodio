"""Serve the screen time card from the integration and register it with the frontend."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)

DATA_FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"
WWW_DIR = Path(__file__).parent / "www"


def card_version(directory: Path = WWW_DIR) -> str:
    """Return a short fingerprint of the card files, used as the card URL's ?v= tag.

    Any change to the files gives the card a new URL, so browsers (and HA's
    frontend cache) load the new card instead of a cached older one.
    """
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.js")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card's files and register the card as a frontend module, once per instance.

    Skips the module registration (with a debug log) when the frontend component
    isn't loaded, e.g. on a headless install, so integration setup still succeeds.
    """
    if hass.data.get(DATA_FRONTEND_REGISTERED):
        return
    hass.data[DATA_FRONTEND_REGISTERED] = True

    await hass.http.async_register_static_paths([StaticPathConfig(FRONTEND_URL_BASE, str(WWW_DIR), False)])
    if "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded; not registering the screen time card")
        return
    version = await hass.async_add_executor_job(card_version)
    add_extra_js_url(hass, f"{FRONTEND_URL_BASE}/{CARD_FILENAME}?v={version}")
