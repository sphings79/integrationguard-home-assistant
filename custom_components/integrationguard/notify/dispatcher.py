"""Decides who hears about a change, and when.

Deliberately simpler than a live alerting engine: the underlying data changes
once a day, so there is no grace period, no bundling window and no escalation.
A run either announces something or it does not.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from ..channels import HANDLERS, ChannelError, RenderedMessage
from ..const import DOMAIN, REPAIR_SEVERITY, RUNTIME_SEVERITY
from ..l10n import normalise, translate
from ..models import Channel, Config, QuietHours, RuntimeInfo
from .messages import (
    Message,
    Notice,
    build_runtime_message,
    build_runtime_recovery_message,
    repositories_notice_id,
)

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
        # Our notifications that are still open in Home Assistant, with the
        # title and text they show. Lets one be updated without bringing back
        # one the user dismissed.
        self._open: dict[str, tuple[str | None, str]] = {}
        self._unsub_notices: CALLBACK_TYPE | None = None

    @callback
    def async_start(self) -> None:
        """Start following which of our notifications are open."""
        self._unsub_notices = persistent_notification.async_register_callback(
            self.hass, self._handle_notices
        )

    @callback
    def async_stop(self) -> None:
        """Stop following the notifications."""
        if self._unsub_notices is not None:
            self._unsub_notices()
            self._unsub_notices = None

    @callback
    def _handle_notices(
        self,
        update_type: persistent_notification.UpdateType,
        notifications: dict[str, persistent_notification.Notification],
    ) -> None:
        """Keep the list of open notifications current."""
        if update_type == persistent_notification.UpdateType.REMOVED:
            for notification_id in notifications:
                self._open.pop(notification_id, None)
            return
        for notification_id, notification in notifications.items():
            if notification_id.startswith(f"{DOMAIN}_"):
                self._open[notification_id] = (
                    notification["title"],
                    notification["message"],
                )

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

        # Good news does not get a notification of its own; the one about the
        # problem is removed instead.
        if severity.persistent_notification and not message.is_recovery:
            for notice in message.notices:
                self._create(notice)

        for channel_id in severity.channels:
            channel = self._config.channel(channel_id)
            if channel is None or not channel.enabled:
                continue
            await self._async_deliver(channel, message)

    @callback
    def sync_repositories(
        self, notices: dict[str, Notice], reopen: Collection[str] = ()
    ) -> None:
        """Make the per-severity notifications about repositories match.

        A severity with nothing left loses its notification. One listed in
        reopen is shown even if the user dismissed it, because something new
        was just announced in it; the others are only updated while open.
        """
        for severity in self._config.severities:
            notice = notices.get(severity.id)
            if not severity.persistent_notification:
                notice = None
            self._sync(
                repositories_notice_id(severity.id),
                notice,
                reopen=severity.id in reopen,
            )

    @callback
    def _sync(
        self, notification_id: str, notice: Notice | None, *, reopen: bool
    ) -> None:
        """Show, update or remove one notification, sending nothing else."""
        if notice is None:
            self.dismiss(notification_id)
            return
        shown = self._open.get(notification_id)
        if shown is None and not reopen:
            return
        if shown != (notice.title, notice.body):
            self._create(notice)

    @callback
    def dismiss(self, notification_id: str) -> None:
        """Remove one of our notifications, if it is still there."""
        persistent_notification.async_dismiss(self.hass, notification_id)

    @callback
    def refresh_runtime(self, info: RuntimeInfo, *, reopen: bool = False) -> None:
        """Bring an open notification about an integration up to date.

        Nothing is sent anywhere else, and a notification the user already
        dismissed stays dismissed — unless reopen asks to show it again, which
        is for bringing back what a restart took away.
        """
        severity_id = _runtime_severity(info)
        if severity_id is None:
            return
        severity = self._config.severity(severity_id)
        if severity is None or not severity.persistent_notification:
            return
        message = build_runtime_message(info, severity_id, self.language)
        for notice in message.notices:
            self._sync(notice.notification_id, notice, reopen=reopen)

    async def async_send_runtime(self, info: RuntimeInfo, now: datetime) -> bool | None:
        """Announce one runtime change, or hold it for the quiet hours.

        Returns True when it went out, False when it was held and None when
        there was nothing to say.
        """
        severity_id = _runtime_severity(info)
        if severity_id is None:
            return None

        message = build_runtime_message(info, severity_id, self.language)
        if self.is_held(message, now):
            self.held_runtime[info.domain] = (message, info.state)
            _LOGGER.debug(
                "Holding the message about %s until the quiet hours end", info.domain
            )
            return False
        await self.async_send(message)
        return True

    async def async_send_runtime_recovery(
        self, domain: str, name: str, now: datetime
    ) -> None:
        """Say that an integration works again, if the user wants to hear it."""
        if not self._config.settings.notify_on_recovery:
            return
        message = build_runtime_recovery_message(
            self._config, domain, name, self.language
        )
        if message is None:
            return
        if self.is_held(message, now):
            self.held_runtime[domain] = (message, "")
            return
        await self.async_send(message)

    async def async_flush_runtime(self, states: dict[str, RuntimeInfo]) -> list[str]:
        """Send what the quiet hours held back, if it still applies.

        Returns the domains whose problem went out.
        """
        held, self.held_runtime = self.held_runtime, {}
        announced: list[str] = []
        for domain, (message, state) in held.items():
            current = states.get(domain)
            if message.is_recovery:
                # It broke again in the meantime, so the good news is stale.
                still_valid = current is None or not current.problem
            else:
                still_valid = (
                    current is not None and current.state == state and current.problem
                )
            if not still_valid:
                _LOGGER.debug(
                    "Dropping the held message about %s, it no longer applies",
                    domain,
                )
                continue
            await self.async_send(message)
            if not message.is_recovery:
                announced.append(domain)
        return announced

    @callback
    def _create(self, notice: Notice) -> None:
        """Show one notification, replacing an older one about the same thing."""
        persistent_notification.async_create(
            self.hass,
            notice.body,
            title=notice.title,
            notification_id=notice.notification_id,
        )

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


def _runtime_severity(info: RuntimeInfo) -> str | None:
    """Return the severity a runtime problem is announced with."""
    severity_id = RUNTIME_SEVERITY.get(info.state)
    if severity_id is None and info.repairs:
        worst = max(
            (issue.severity or "warning" for issue in info.repairs),
            key=lambda name: (
                list(REPAIR_SEVERITY).index(name) if name in REPAIR_SEVERITY else 0
            ),
        )
        severity_id = REPAIR_SEVERITY.get(worst)
    return severity_id
