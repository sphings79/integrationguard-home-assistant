"""One binary sensor: is anything critical going on."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import IntegrationGuardConfigEntry
from .const import DOMAIN, Status
from .coordinator import IntegrationGuardCoordinator
from .entity import IntegrationGuardEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the critical indicator."""
    async_add_entities([CriticalBinarySensor(entry.runtime_data)])


class CriticalBinarySensor(IntegrationGuardEntity, BinarySensorEntity):
    """Turns on when a repository is archived, gone or flagged by HACS."""

    _attr_translation_key = "critical"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Create the indicator."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_critical"

    @property
    def is_on(self) -> bool | None:
        """Return whether anything needs attention right now."""
        result = self.coordinator.result
        if result is None:
            return None
        return bool(self._affected())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List what turned the sensor on."""
        return {"repositories": sorted(item.key for item in self._affected())}

    def _affected(self) -> list:
        """Return the repositories in a critical or abandoned state."""
        result = self.coordinator.result
        if result is None:
            return []
        return result.by_status(Status.CRITICAL) + result.by_status(Status.ABANDONED)
