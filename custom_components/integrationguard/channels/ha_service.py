"""Delivery through any Home Assistant service.

Covers everything Home Assistant already knows how to notify: the mobile
apps, a configured Telegram bot, the SMTP integration, a script, and so on.
No credentials are stored here — the service owns them.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..models import Channel
from .base import ChannelError, ChannelHandler, RenderedMessage

_LOGGER = logging.getLogger(__name__)


class HaServiceChannel(ChannelHandler):
    """Calls a Home Assistant service with the rendered message."""

    kind = "ha_service"

    def validate(self, config: dict[str, Any]) -> str | None:
        """Require a service in `domain.service` form."""
        service = config.get("service", "")
        if not service or "." not in service:
            return "service"
        return None

    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Call the configured service."""
        service: str = channel.config.get("service", "")
        if "." not in service:
            raise ChannelError(f"'{service}' is not a valid service")
        domain, name = service.split(".", 1)

        data: dict[str, Any] = {
            "message": message.body,
            "title": message.title,
        }
        # Extra data lets the user pass things like a Telegram chat id or the
        # notification actions of the companion app.
        extra = channel.config.get("data")
        if isinstance(extra, dict):
            data.update(extra)

        target = channel.config.get("target")
        if target:
            data["target"] = target

        try:
            await hass.services.async_call(domain, name, data, blocking=True)
        except (HomeAssistantError, ValueError) as err:
            raise ChannelError(str(err)) from err
