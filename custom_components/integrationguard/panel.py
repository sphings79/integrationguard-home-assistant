"""Registers the IntegrationGuard sidebar panel and serves its frontend bundle."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = DOMAIN
STATIC_URL = f"/{DOMAIN}-frontend"
COMPONENT_NAME = "integrationguard-panel"
BUNDLE_NAME = "integrationguard-panel.js"
CARD_NAME = "integrationguard-card.js"
PANEL_TITLE = "IntegrationGuard"
PANEL_ICON = "mdi:heart-pulse"

DATA_PANEL_REGISTERED = "panel_registered"
DATA_PANEL_ADMIN_ONLY = "panel_admin_only"
DATA_STATIC_REGISTERED = "static_registered"


async def _version(hass: HomeAssistant) -> str:
    """Return the integration version, used to bust the browser cache.

    Read through the loader rather than the manifest file directly: the file
    is already cached and reading it here would block the event loop.
    """
    integration = await async_get_integration(hass, DOMAIN)
    return str(integration.version or "dev")


async def async_register_panel(
    hass: HomeAssistant, *, require_admin: bool = True
) -> None:
    """Serve the bundle and add IntegrationGuard to the sidebar."""
    data = hass.data.setdefault(DOMAIN, {})
    frontend_dir = Path(__file__).parent / "frontend"

    if not data.get(DATA_STATIC_REGISTERED):
        # Static paths cannot be registered twice, so this survives a reload.
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(frontend_dir), cache_headers=False)]
        )
        data[DATA_STATIC_REGISTERED] = True

    if data.get(DATA_PANEL_REGISTERED):
        if data.get(DATA_PANEL_ADMIN_ONLY) == require_admin:
            return
        # Visibility changed: the panel has to be replaced, it cannot be
        # updated in place.
        frontend.async_remove_panel(hass, PANEL_URL_PATH)

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=COMPONENT_NAME,
        module_url=f"{STATIC_URL}/{BUNDLE_NAME}?v={await _version(hass)}",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=require_admin,
    )
    data[DATA_PANEL_REGISTERED] = True
    data[DATA_PANEL_ADMIN_ONLY] = require_admin
    _LOGGER.debug("Panel registered at /%s", PANEL_URL_PATH)


async def async_register_card(hass: HomeAssistant) -> None:
    """Offer the Lovelace card without the user installing anything.

    Only works with storage-mode dashboards; with a YAML dashboard the
    resource has to be added by hand, which the README explains.
    """
    resources = getattr(hass.data.get("lovelace"), "resources", None)
    if resources is None:
        _LOGGER.debug("Lovelace resources unavailable, skipping card registration")
        return
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    url = f"{STATIC_URL}/{CARD_NAME}?v={await _version(hass)}"
    base = url.split("?")[0]
    for item in resources.async_items():
        if item.get("url", "").split("?")[0] == base:
            if item["url"] != url:
                await resources.async_update_item(item["id"], {"url": url})
            return
    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.debug("Registered the Lovelace card at %s", url)


def async_remove_panel(hass: HomeAssistant) -> None:
    """Take the panel out of the sidebar when the integration is removed."""
    data = hass.data.get(DOMAIN, {})
    if not data.get(DATA_PANEL_REGISTERED):
        return
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    data[DATA_PANEL_REGISTERED] = False
