"""Persistent storage for configuration and scan state."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    STORAGE_KEY_CONFIG,
    STORAGE_KEY_STATE,
    STORAGE_VERSION_CONFIG,
    STORAGE_VERSION_STATE,
    Category,
    SeverityId,
)
from .health.rules import default_rules, merge_rules
from .models import Config, Severity

_LOGGER = logging.getLogger(__name__)

SEVERITY_NAMES: dict[str, dict[str, str]] = {
    "en": {
        SeverityId.INFO: "Info",
        SeverityId.WARNING: "Warning",
        SeverityId.CRITICAL: "Critical",
        SeverityId.SECURITY: "Security",
    },
    "de": {
        SeverityId.INFO: "Info",
        SeverityId.WARNING: "Warnung",
        SeverityId.CRITICAL: "Kritisch",
        SeverityId.SECURITY: "Sicherheit",
    },
}

DEFAULT_SEVERITIES: tuple[dict[str, Any], ...] = (
    {
        "id": SeverityId.INFO,
        "name": "Info",
        "priority": 10,
        "color": "blue-grey",
        "icon": "mdi:information-outline",
    },
    {
        "id": SeverityId.WARNING,
        "name": "Warning",
        "priority": 50,
        "color": "amber",
        "icon": "mdi:alert-outline",
    },
    {
        "id": SeverityId.CRITICAL,
        "name": "Critical",
        "priority": 80,
        "color": "red",
        "icon": "mdi:alert",
    },
    {
        "id": SeverityId.SECURITY,
        "name": "Security",
        "priority": 90,
        "color": "deep-purple",
        "icon": "mdi:shield-alert",
    },
)


class ConfigStore(Store[dict[str, Any]]):
    """The configuration store, with the migrations between its versions."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Bring a configuration written by an older version up to date."""
        if old_major_version < 2:
            # Version 2 added apps as a category. A list written before that
            # cannot have opted out of something that did not exist yet.
            settings = old_data.setdefault("settings", {})
            for key in ("categories_health", "categories_usage"):
                categories = settings.get(key)
                if isinstance(categories, list) and str(Category.APP) not in categories:
                    categories.append(str(Category.APP))
            _LOGGER.debug("Migrated the stored configuration to version 2")
        return old_data


class IntegrationGuardStore:
    """Loads and saves the configuration and the scan state."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Set up both stores."""
        self._hass = hass
        self._config_store: Store[dict[str, Any]] = ConfigStore(
            hass, STORAGE_VERSION_CONFIG, STORAGE_KEY_CONFIG
        )
        self._state_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION_STATE, STORAGE_KEY_STATE
        )
        self.config = Config()

    async def async_load(self) -> Config:
        """Load the configuration, seeding defaults on first start."""
        data = await self._config_store.async_load()
        if data is None:
            self.config = Config(
                severities=self._seed_severities(), rules=default_rules()
            )
            await self.async_save()
            _LOGGER.debug("No stored configuration found, seeded the defaults")
            return self.config

        self.config = Config.from_dict(data)
        changed = False
        if not self.config.severities:
            self.config.severities = self._seed_severities()
            changed = True
        self.config.rules, rules_changed = merge_rules(self.config.rules)
        changed = changed or rules_changed
        if changed:
            await self.async_save()
        return self.config

    def _seed_severities(self) -> list[Severity]:
        """Return the default severities, named in the interface language."""
        language = (self._hass.config.language or "en").split("-")[0]
        names = SEVERITY_NAMES.get(language, SEVERITY_NAMES["en"])
        return [
            Severity.from_dict(
                {**severity, "name": names.get(str(severity["id"]), severity["name"])}
            )
            for severity in DEFAULT_SEVERITIES
        ]

    async def async_save(self) -> None:
        """Write the configuration to disk."""
        await self._config_store.async_save(self.config.to_dict())

    async def async_load_state(self) -> dict[str, Any]:
        """Return the state left behind by the previous run."""
        return await self._state_store.async_load() or {}

    async def async_save_state(self, state: dict[str, Any]) -> None:
        """Persist the scan state, caches included."""
        await self._state_store.async_save(state)

    async def async_remove(self) -> None:
        """Delete both stores when the integration is removed."""
        await self._config_store.async_remove()
        await self._state_store.async_remove()
