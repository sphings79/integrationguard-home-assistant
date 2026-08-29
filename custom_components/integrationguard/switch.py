"""Global on/off switch for the scheduled scans."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import IntegrationGuardConfigEntry
from .const import DOMAIN
from .coordinator import IntegrationGuardCoordinator
from .entity import IntegrationGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the monitoring switch."""
    async_add_entities([MonitoringSwitch(entry.runtime_data)])


class MonitoringSwitch(IntegrationGuardEntity, SwitchEntity):
    """Pauses the scheduled scans. A scan asked for by hand still runs."""

    _attr_translation_key = "monitoring"

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the global switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_monitoring"

    @property
    def is_on(self) -> bool:
        """Return whether scheduled scans are active."""
        return self.coordinator.config.settings.monitoring_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume the schedule."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause the schedule."""
        await self._async_set(False)

    async def _async_set(self, enabled: bool) -> None:
        """Persist the new setting and rearm the timer."""
        self.coordinator.config.settings.monitoring_enabled = enabled
        await self.coordinator.store.async_save()
        await self.coordinator.async_config_changed()
