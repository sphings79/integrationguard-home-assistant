"""Notification channels.

Every channel is a handler registered under a `kind`. The dispatcher renders
a message once and hands it to each selected handler.
"""

from __future__ import annotations

from .base import ChannelError, ChannelHandler, RenderedMessage
from .ha_service import HaServiceChannel
from .ntfy import NtfyChannel
from .pushover import PushoverChannel
from .smtp import SmtpChannel
from .telegram import TelegramChannel

HANDLERS: dict[str, ChannelHandler] = {
    handler.kind: handler
    for handler in (
        HaServiceChannel(),
        SmtpChannel(),
        TelegramChannel(),
        PushoverChannel(),
        NtfyChannel(),
    )
}

# What each kind needs, so the panel can build its form without knowing the
# handlers. `secret` fields are never sent back to the browser.
CHANNEL_FIELDS: dict[str, tuple[dict[str, object], ...]] = {
    "ha_service": (
        {
            "key": "service",
            "type": "text",
            "required": True,
            "example": "notify.mobile_app_phone",
        },
        {"key": "target", "type": "text"},
        {"key": "data", "type": "object"},
    ),
    "smtp": (
        {
            "key": "host",
            "type": "text",
            "required": True,
            "example": "smtp.example.com",
        },
        {"key": "port", "type": "number", "default": 587},
        {
            "key": "encryption",
            "type": "select",
            "options": ("starttls", "ssl", "none"),
            "default": "starttls",
        },
        {"key": "username", "type": "text"},
        {"key": "password", "type": "secret"},
        {
            "key": "sender",
            "type": "text",
            "required": True,
            "example": "homeassistant@example.com",
        },
        {
            "key": "recipients",
            "type": "text",
            "required": True,
            "example": "me@example.com, you@example.com",
        },
    ),
    "telegram": (
        {"key": "token", "type": "secret", "required": True},
        {
            "key": "chat_id",
            "type": "text",
            "required": True,
            "example": "-1001234567890",
        },
    ),
    "pushover": (
        {"key": "token", "type": "secret", "required": True},
        {"key": "user_key", "type": "secret", "required": True},
        {"key": "device", "type": "text"},
        {
            "key": "priority",
            "type": "select",
            "options": ("-2", "-1", "0", "1", "2"),
            "default": "0",
        },
        {"key": "sound", "type": "text"},
    ),
    "ntfy": (
        {"key": "server", "type": "text", "default": "https://ntfy.sh"},
        {"key": "topic", "type": "text", "required": True},
        {"key": "token", "type": "secret"},
        {"key": "username", "type": "text"},
        {"key": "password", "type": "secret"},
        {
            "key": "priority",
            "type": "select",
            "options": ("1", "2", "3", "4", "5"),
            "default": "3",
        },
        {"key": "tags", "type": "text", "example": "warning, house"},
    ),
}

# Sent in place of a stored secret. Saving it back keeps the stored value.
SECRET_PLACEHOLDER = "__unchanged__"


def secret_keys(kind: str) -> set[str]:
    """Return the config keys of a kind that must never leave the server."""
    return {
        str(field["key"])
        for field in CHANNEL_FIELDS.get(kind, ())
        if field.get("type") == "secret"
    }


__all__ = [
    "CHANNEL_FIELDS",
    "HANDLERS",
    "SECRET_PLACEHOLDER",
    "ChannelError",
    "ChannelHandler",
    "RenderedMessage",
    "secret_keys",
]
