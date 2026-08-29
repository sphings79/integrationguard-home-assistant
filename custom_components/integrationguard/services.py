"""Services IntegrationGuard offers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from .models import Ignore

if TYPE_CHECKING:
    from . import IntegrationGuardConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_SCAN = "scan"
SERVICE_IGNORE = "ignore"
SERVICE_UNIGNORE = "unignore"
SERVICE_MARK_USED = "mark_used"

SCAN_SCHEMA = vol.Schema({vol.Optional("force", default=False): cv.boolean})
IGNORE_SCHEMA = vol.Schema(
    {
        vol.Required("repository"): cv.string,
        vol.Optional("duration"): cv.positive_time_period,
        vol.Optional("reason", default=""): cv.string,
    }
)
UNIGNORE_SCHEMA = vol.Schema({vol.Required("repository"): cv.string})
MARK_USED_SCHEMA = vol.Schema(
    {
        vol.Required("repository"): cv.string,
        vol.Optional("used", default=True): cv.boolean,
    }
)


def _entries(hass: HomeAssistant) -> list[IntegrationGuardConfigEntry]:
    """Return the loaded config entries of this integration."""
    return hass.config_entries.async_loaded_entries(DOMAIN)


def _known_key(hass: HomeAssistant, key: str) -> None:
    """Raise when nothing on this installation goes by that name."""
    for entry in _entries(hass):
        result = entry.runtime_data.result
        if result is None or any(item.key == key for item in result.repositories):
            return
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="unknown_repository",
        translation_placeholders={"repository": key},
    )


def async_register_services(hass: HomeAssistant) -> None:
    """Register the services, once per process."""
    if hass.services.has_service(DOMAIN, SERVICE_SCAN):
        return

    async def _scan(call: ServiceCall) -> None:
        """Run a scan right now, outside the schedule."""
        for entry in _entries(hass):
            await entry.runtime_data.async_scan(force=call.data["force"])

    async def _ignore(call: ServiceCall) -> None:
        """Stop reporting about one repository, optionally for a while."""
        key = call.data["repository"]
        _known_key(hass, key)
        until = None
        if duration := call.data.get("duration"):
            from homeassistant.util import dt as dt_util

            until = (dt_util.utcnow() + duration).isoformat()
        for entry in _entries(hass):
            coordinator = entry.runtime_data
            config = coordinator.config
            config.ignored = [i for i in config.ignored if i.key != key]
            config.ignored.append(
                Ignore(key=key, until=until, reason=call.data["reason"])
            )
            await coordinator.store.async_save()
            await coordinator.async_config_changed()

    async def _unignore(call: ServiceCall) -> None:
        """Report about a repository again."""
        key = call.data["repository"]
        for entry in _entries(hass):
            coordinator = entry.runtime_data
            config = coordinator.config
            config.ignored = [i for i in config.ignored if i.key != key]
            await coordinator.store.async_save()
            await coordinator.async_config_changed()

    async def _mark_used(call: ServiceCall) -> None:
        """Override the usage verdict by hand."""
        key = call.data["repository"]
        _known_key(hass, key)
        for entry in _entries(hass):
            coordinator = entry.runtime_data
            config = coordinator.config
            marked = set(config.marked_used)
            marked.add(key) if call.data["used"] else marked.discard(key)
            config.marked_used = sorted(marked)
            await coordinator.store.async_save()
            await coordinator.async_scan()

    hass.services.async_register(DOMAIN, SERVICE_SCAN, _scan, schema=SCAN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_IGNORE, _ignore, schema=IGNORE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_UNIGNORE, _unignore, schema=UNIGNORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_MARK_USED, _mark_used, schema=MARK_USED_SCHEMA
    )
