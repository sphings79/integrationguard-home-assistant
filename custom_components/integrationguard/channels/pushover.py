"""Delivery through Pushover."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..models import Channel
from .base import ChannelError, ChannelHandler, RenderedMessage

_LOGGER = logging.getLogger(__name__)

API = "https://api.pushover.net/1/messages.json"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class PushoverChannel(ChannelHandler):
    """Sends a Pushover notification."""

    kind = "pushover"

    def validate(self, config: dict[str, Any]) -> str | None:
        """Require an application token and a user key."""
        for key in ("token", "user_key"):
            if not config.get(key):
                return key
        return None

    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Send the message with the configured priority and sound."""
        config = channel.config
        payload: dict[str, Any] = {
            "token": config["token"],
            "user": config["user_key"],
            "title": message.title,
            "message": message.body,
        }
        if config.get("priority") is not None:
            payload["priority"] = int(config["priority"])
        if config.get("sound"):
            payload["sound"] = config["sound"]
        if config.get("device"):
            payload["device"] = config["device"]
        if message.url:
            payload["url"] = message.url
            payload["url_title"] = "Home Assistant"

        session = async_get_clientsession(hass)
        try:
            async with session.post(API, data=payload, timeout=TIMEOUT) as response:
                if response.status != 200:
                    detail = await response.text()
                    raise ChannelError(f"HTTP {response.status}: {detail[:200]}")
        except aiohttp.ClientError as err:
            raise ChannelError(str(err)) from err
