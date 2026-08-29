"""Shared base class for every entity IntegrationGuard creates."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATED
from .coordinator import IntegrationGuardCoordinator


class IntegrationGuardEntity(Entity):
    """Groups all entities under one service device and keeps them in sync."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: IntegrationGuardCoordinator) -> None:
        """Attach the entity to the coordinator and the shared device."""
        self.coordinator = coordinator
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="IntegrationGuard",
            manufacturer="sphings79",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Refresh the entity after a scan or a settings change."""
        self.async_write_ha_state()
