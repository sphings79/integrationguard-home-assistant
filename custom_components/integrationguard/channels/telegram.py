"""Delivery through a Telegram bot, using its HTTP API directly."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..models import Channel
from .base import ChannelError, ChannelHandler, RenderedMessage

_LOGGER = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class TelegramChannel(ChannelHandler):
    """Posts the message into a Telegram chat."""

    kind = "telegram"

    def validate(self, config: dict[str, Any]) -> str | None:
        """Require a bot token and a chat id."""
        for key in ("token", "chat_id"):
            if not config.get(key):
                return key
        return None

    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Send the message, formatted as Markdown."""
        config = channel.config
        session = async_get_clientsession(hass)
        payload = {
            "chat_id": str(config["chat_id"]),
            "text": f"*{message.title}*\n\n{message.body}",
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            async with session.post(
                API.format(token=config["token"]), json=payload, timeout=TIMEOUT
            ) as response:
                if response.status != 200:
                    detail = await response.text()
                    raise ChannelError(f"HTTP {response.status}: {detail[:200]}")
        except aiohttp.ClientError as err:
            raise ChannelError(str(err)) from err
