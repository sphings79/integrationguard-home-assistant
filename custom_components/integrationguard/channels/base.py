"""The contract every notification channel follows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant

from ..models import Channel


@dataclass(slots=True)
class RenderedMessage:
    """A message ready to be delivered, rendered once for all channels."""

    title: str
    body: str
    severity: str = ""
    # The repositories, apps or integrations the message is about.
    keys: list[str] = field(default_factory=list)
    url: str | None = None
    is_recovery: bool = False


class ChannelError(Exception):
    """A channel could not deliver its message."""


class ChannelHandler(ABC):
    """Delivers a rendered message through one kind of destination."""

    kind: str = ""

    @abstractmethod
    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Deliver the message, raising ChannelError on failure."""

    def validate(self, config: dict[str, Any]) -> str | None:
        """Return the name of the first missing setting, or None if complete."""
        return None
