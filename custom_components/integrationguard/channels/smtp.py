"""Delivery by e-mail over SMTP.

Uses the standard library in an executor thread rather than adding an async
mail dependency, which keeps the integration free of extra requirements.
"""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate
import logging
import smtplib
from typing import Any

from homeassistant.core import HomeAssistant

from ..models import Channel
from .base import ChannelError, ChannelHandler, RenderedMessage

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 587


class SmtpChannel(ChannelHandler):
    """Sends the message as an e-mail."""

    kind = "smtp"

    def validate(self, config: dict[str, Any]) -> str | None:
        """Host, sender and at least one recipient are required."""
        for key in ("host", "sender", "recipients"):
            if not config.get(key):
                return key
        return None

    async def async_send(
        self, hass: HomeAssistant, channel: Channel, message: RenderedMessage
    ) -> None:
        """Hand the blocking SMTP conversation to an executor thread."""
        config = channel.config
        await hass.async_add_executor_job(self._send, config, message)

    def _send(self, config: dict[str, Any], message: RenderedMessage) -> None:
        """Build and deliver the mail. Runs outside the event loop."""
        recipients = config["recipients"]
        if isinstance(recipients, str):
            recipients = [
                item.strip() for item in recipients.split(",") if item.strip()
            ]

        mail = EmailMessage()
        mail["Subject"] = message.title
        mail["From"] = config["sender"]
        mail["To"] = ", ".join(recipients)
        mail["Date"] = formatdate(localtime=True)
        mail.set_content(message.body)

        host = config["host"]
        port = int(config.get("port") or DEFAULT_PORT)
        timeout = int(config.get("timeout") or 20)
        encryption = config.get("encryption", "starttls")

        try:
            if encryption == "ssl":
                server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
            with server:
                if encryption == "starttls":
                    server.starttls()
                username = config.get("username")
                password = config.get("password")
                if username and password:
                    server.login(username, password)
                server.send_message(mail)
        except (smtplib.SMTPException, OSError) as err:
            raise ChannelError(str(err)) from err
