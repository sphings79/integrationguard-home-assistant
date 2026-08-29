"""Delivery through ntfy, either ntfy.sh or a self-hosted server."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..models import Channel
from .base import ChannelError, ChannelHandler, RenderedMessage

_LOGGER = logging.getLogger(__name__)

DEFAULT_SERVER = "https://ntfy.sh"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class NtfyChannel(ChannelHandler):
    """Publishes the message to an ntfy topic."""

    kind = "ntfy"

    def validate(self, config: dict[str, Any]) -> str | None:
        """Require a topic; the server defaults to ntfy.sh."""
        if not config.get("topic"):
            return "topic"
        return None

    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Publish the message, with a click-through URL when there is one."""
        config = channel.config
        server = (config.get("server") or DEFAULT_SERVER).rstrip("/")
        payload: dict[str, Any] = {
            "topic": config["topic"],
            "title": message.title,
            "message": message.body,
        }
        if config.get("priority"):
            payload["priority"] = int(config["priority"])
        if config.get("tags"):
            tags = config["tags"]
            payload["tags"] = (
                [tag.strip() for tag in tags.split(",")]
                if isinstance(tags, str)
                else tags
            )
        if message.url:
            payload["click"] = message.url

        headers: dict[str, str] = {}
        if config.get("token"):
            headers["Authorization"] = f"Bearer {config['token']}"
        elif config.get("username") and config.get("password"):
            auth = aiohttp.BasicAuth(config["username"], config["password"])
            headers["Authorization"] = auth.encode()

        session = async_get_clientsession(hass)
        try:
            async with session.post(
                server, json=payload, headers=headers, timeout=TIMEOUT
            ) as response:
                if response.status >= 400:
                    detail = await response.text()
                    raise ChannelError(f"HTTP {response.status}: {detail[:200]}")
        except aiohttp.ClientError as err:
            raise ChannelError(str(err)) from err
