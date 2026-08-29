"""Decides who hears about a change, and when.

Deliberately simpler than a live alerting engine: the underlying data changes
once a day, so there is no grace period, no bundling window and no escalation.
A run either announces something or it does not.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from ..channels import HANDLERS, ChannelError, RenderedMessage
from ..const import DOMAIN, REPAIR_SEVERITY, RUNTIME_SEVERITY
from ..l10n import normalise, translate
from ..models import Channel, Config, QuietHours, RuntimeInfo
from .messages import Message, build_runtime_message

_LOGGER = logging.getLogger(__name__)


def _parse_time(value: str, fallback: time) -> time:
    """Return a HH:MM string as a time, falling back when it is unreadable."""
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
        return time(hour % 24, minute % 60)
    except (ValueError, AttributeError):
        return fallback


def in_quiet_hours(quiet: QuietHours, now: datetime) -> bool:
    """Return whether a moment falls inside the configured quiet window."""
    if not quiet.enabled:
        return False
    start = _parse_time(quiet.start, time(22, 0))
    end = _parse_time(quiet.end, time(7, 0))
    current = now.time()
    if start == end:
        return False
    if start < end:
        inside = start <= current < end
        day = now.weekday()
    else:
        # The window runs past midnight, so it belongs to the day it started on.
        inside = current >= start or current < end
        day = now.weekday() if current >= start else (now.weekday() - 1) % 7
    if not inside:
        return False
    return not quiet.weekdays or day in quiet.weekdays


def next_quiet_end(quiet: QuietHours, now: datetime) -> datetime | None:
    """Return when the current quiet window ends."""
    if not in_quiet_hours(quiet, now):
        return None
    end = _parse_time(quiet.end, time(7, 0))
    candidate = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class Dispatcher:
    """Renders messages and hands them to the channels of their severity."""

    def __init__(self, hass: HomeAssistant, config: Config) -> None:
        """Remember where to look up channels and severities."""
        self.hass = hass
        self._config = config
        # Runtime messages held back by the quiet hours, by domain.
        self.held_runtime: dict[str, tuple[Message, str]] = {}

    @property
    def language(self) -> str:
        """Return the language notifications are written in."""
        configured = self._config.settings.ui_language
        if configured and configured != "auto":
            return normalise(configured)
        return normalise(self.hass.config.language)

    def set_config(self, config: Config) -> None:
        """Point at the current configuration after a reload."""
        self._config = config

    def is_held(self, message: Message, now: datetime) -> bool:
        """Return whether the quiet hours hold this message back."""
        severity = self._config.severity(message.severity_id)
        if severity is not None and severity.ignore_quiet_hours:
            return False
        return in_quiet_hours(self._config.settings.quiet_hours, now)

    async def async_send(self, message: Message) -> None:
        """Deliver one message through everything its severity selects."""
        severity = self._config.severity(message.severity_id)
        if severity is None:
            _LOGGER.debug(
                "Dropping a message for unknown severity %s", message.severity_id
            )
            return

        if severity.persistent_notification:
            persistent_notification.async_create(
                self.hass,
                message.body if not message.url else f"{message.body}\n\n{message.url}",
                title=message.title,
                notification_id=f"{DOMAIN}_{message.severity_id}",
            )

        for channel_id in severity.channels:
            channel = self._config.channel(channel_id)
            if channel is None or not channel.enabled:
                continue
            await self._async_deliver(channel, message)

    async def async_send_runtime(self, info: RuntimeInfo, now: datetime) -> bool:
        """Announce one runtime change, or hold it for the quiet hours.

        Returns True when it went out, False when it was held.
        """
        severity_id = RUNTIME_SEVERITY.get(info.state)
        if severity_id is None and info.repairs:
            worst = max(
                (issue.severity or "warning" for issue in info.repairs),
                key=lambda name: (
                    list(REPAIR_SEVERITY).index(name) if name in REPAIR_SEVERITY else 0
                ),
            )
            severity_id = REPAIR_SEVERITY.get(worst)
        if severity_id is None:
            return True

        message = build_runtime_message(info, severity_id, self.language)
        if self.is_held(message, now):
            self.held_runtime[info.domain] = (message, info.state)
            _LOGGER.debug(
                "Holding the message about %s until the quiet hours end", info.domain
            )
            return False
        await self.async_send(message)
        return True

    async def async_flush_runtime(self, states: dict[str, RuntimeInfo]) -> None:
        """Send what the quiet hours held back, if it still applies."""
        held, self.held_runtime = self.held_runtime, {}
        for domain, (message, state) in held.items():
            current = states.get(domain)
            if current is None or current.state != state or not current.problem:
                _LOGGER.debug(
                    "Dropping the held message about %s, it resolved itself", domain
                )
                continue
            await self.async_send(message)

    async def async_test(self, channel: Channel) -> None:
        """Send a test message, raising ChannelError when it does not work."""
        message = RenderedMessage(
            title=translate(self.language, "title.test"),
            body=translate(self.language, "body.test"),
        )
        handler = HANDLERS.get(channel.kind)
        if handler is None:
            raise ChannelError(f"unknown channel kind {channel.kind}")
        await handler.async_send(self.hass, channel, message)

    async def _async_deliver(self, channel: Channel, message: Message) -> None:
        """Render for one channel and hand it over."""
        handler = HANDLERS.get(channel.kind)
        if handler is None:
            _LOGGER.warning(
                "Channel %s has an unknown kind %s", channel.name, channel.kind
            )
            return
        rendered = RenderedMessage(
            title=self._render(channel.title_template, message, message.title),
            body=self._render(channel.template, message, message.body),
            severity=message.severity_id,
            keys=message.keys,
            url=message.url,
            is_recovery=message.is_recovery,
        )
        try:
            await handler.async_send(self.hass, channel, rendered)
        except ChannelError as err:
            _LOGGER.error("Channel %s could not deliver: %s", channel.name, err)
        except Exception:
            _LOGGER.exception("Channel %s raised while delivering", channel.name)

    def _render(self, template: str, message: Message, fallback: str) -> str:
        """Render a channel's own template, falling back to the built-in text."""
        if not template.strip():
            return fallback
        severity = self._config.severity(message.severity_id)
        context: dict[str, Any] = {
            "title": message.title,
            "body": message.body,
            "keys": message.keys,
            "url": message.url or "",
            "severity": severity.name if severity else message.severity_id,
            "is_recovery": message.is_recovery,
            "now": dt_util.now(),
        }
        try:
            return Template(template, self.hass).async_render(
                context, parse_result=False
            )
        except Exception:
            _LOGGER.exception("Template of a channel could not be rendered")
            return fallback
