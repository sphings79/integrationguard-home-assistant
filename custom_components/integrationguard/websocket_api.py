"""The commands the panel calls.

Reads are open to any signed-in user because the panel itself is gated; writes
always require an administrator.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from .channels import (
    CHANNEL_FIELDS,
    HANDLERS,
    SECRET_PLACEHOLDER,
    ChannelError,
    secret_keys,
)
from .const import ALL_CATEGORIES, DOMAIN, RuntimeState
from .health.rules import RULE_DEFINITIONS
from .models import Channel, Config, Ignore, Severity

_LOGGER = logging.getLogger(__name__)

DATA_REGISTERED = "websocket_registered"


def _coordinator(hass: HomeAssistant) -> Any:
    """Return the single coordinator, or None when it is not loaded."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def _rule_catalogue() -> list[dict[str, Any]]:
    """Return what the panel needs to render the rule editor."""
    return [
        {
            "id": str(definition.id),
            "default_severity": str(definition.severity_id),
            "default_penalty": definition.penalty,
            "default_threshold": definition.threshold,
            "threshold_unit": (
                str(definition.threshold_unit) if definition.threshold_unit else None
            ),
            "requires_github": definition.requires_github,
            "supersedes": (
                str(definition.supersedes) if definition.supersedes else None
            ),
            "categories": (
                [str(c) for c in definition.categories]
                if definition.categories
                else None
            ),
        }
        for definition in RULE_DEFINITIONS
    ]


def _safe_channel(channel: Channel) -> dict[str, Any]:
    """Return a channel with its secrets replaced by a placeholder."""
    secrets = secret_keys(channel.kind)
    config = {
        key: (SECRET_PLACEHOLDER if key in secrets and value else value)
        for key, value in channel.config.items()
    }
    return {**channel.to_dict(), "config": config}


def _merge_secrets(existing: Channel | None, kind: str, config: dict) -> dict:
    """Keep a stored secret when the browser sent the placeholder back."""
    if existing is None:
        return config
    merged = dict(config)
    for key in secret_keys(kind):
        if merged.get(key) == SECRET_PLACEHOLDER:
            merged[key] = existing.config.get(key, "")
    return merged


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register every command, once per process."""
    data = hass.data.setdefault(DOMAIN, {})
    if data.get(DATA_REGISTERED):
        return
    for handler in (
        websocket_get,
        websocket_card,
        websocket_scan,
        websocket_save_settings,
        websocket_save_rules,
        websocket_save_severities,
        websocket_save_channel,
        websocket_delete_channel,
        websocket_test_channel,
        websocket_ignore,
        websocket_mark_used,
        websocket_history,
    ):
        websocket_api.async_register_command(hass, handler)
    data[DATA_REGISTERED] = True


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get"})
@websocket_api.async_response
async def websocket_get(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Return everything the panel needs in one go."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return

    config: Config = coordinator.config
    result = coordinator.result
    connection.send_result(
        msg["id"],
        {
            "settings": config.settings.to_dict(),
            "severities": [s.to_dict() for s in config.severities],
            "rules": [r.to_dict() for r in config.rules],
            "channels": [_safe_channel(c) for c in config.channels],
            "channel_fields": {
                kind: [dict(field) for field in fields]
                for kind, fields in CHANNEL_FIELDS.items()
            },
            "ignored": [i.to_dict() for i in config.ignored],
            "marked_used": list(config.marked_used),
            "rule_catalogue": _rule_catalogue(),
            "categories": [str(c) for c in ALL_CATEGORIES],
            "runtime": [info.to_dict() for info in coordinator.runtime.states.values()],
            "runtime_states": [str(state) for state in RuntimeState],
            "repositories": (
                [item.to_dict() for item in result.repositories] if result else []
            ),
            "orphans": result.orphans if result else [],
            "scan": {
                "last": result.finished.isoformat() if result else None,
                "duration": round(result.duration, 1) if result else None,
                "errors": result.source_errors if result else {},
                "github_remaining": result.github_remaining if result else None,
                "github_pending": result.github_pending if result else 0,
                "score": coordinator.average_score(),
                "has_token": bool(coordinator.github_token),
            },
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/card"})
@websocket_api.async_response
async def websocket_card(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Return the little the Lovelace card needs.

    Separate from the full read on purpose: this carries no configuration, so
    it is safe for every signed-in user on any dashboard.
    """
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return

    result = coordinator.result
    items = [item for item in result.repositories if not item.ignored] if result else []
    connection.send_result(
        msg["id"],
        {
            "score": coordinator.average_score(),
            "last_scan": result.finished.isoformat() if result else None,
            "total": len(items),
            "problems": [
                {
                    "key": item.key,
                    "name": item.info.name,
                    "category": item.info.category,
                    "status": item.status,
                    "score": item.score,
                    "usage": item.usage,
                    "url": item.info.url,
                }
                for item in sorted(items, key=lambda entry: entry.score)
                if item.status != "healthy"
            ],
            "unused": sum(1 for item in items if item.usage == "unused"),
            "runtime": [
                {
                    "domain": info.domain,
                    "name": info.title or info.domain,
                    "state": info.state,
                    "url": info.configuration_url,
                }
                for info in coordinator.runtime.states.values()
                if info.problem
            ],
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/scan",
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.async_response
async def websocket_scan(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Run a scan now."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    await coordinator.async_scan(force=msg["force"])
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/settings/save",
        vol.Required("settings"): dict,
        vol.Optional("github_token"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def websocket_save_settings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Replace the settings, and the GitHub token when one was sent."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return

    from .models import Settings

    coordinator.config.settings = Settings.from_dict(msg["settings"])
    await coordinator.store.async_save()
    if (token := msg.get("github_token")) is not None:
        await coordinator.async_set_github_token(token.strip())
    await coordinator.async_config_changed()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/rules/save", vol.Required("rules"): list}
)
@websocket_api.async_response
async def websocket_save_rules(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Replace the rule settings and judge everything again."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return

    from .health.rules import merge_rules
    from .models import Rule

    rules, _ = merge_rules([Rule.from_dict(raw) for raw in msg["rules"]])
    coordinator.config.rules = rules
    await coordinator.store.async_save()
    await coordinator.async_scan()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/severities/save",
        vol.Required("severities"): list,
    }
)
@websocket_api.async_response
async def websocket_save_severities(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Replace the severities."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    severities = [Severity.from_dict(raw) for raw in msg["severities"]]
    if not severities:
        connection.send_error(msg["id"], "empty", "At least one severity is needed")
        return
    coordinator.config.severities = severities
    await coordinator.store.async_save()
    await coordinator.async_scan()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/channels/save", vol.Required("channel"): dict}
)
@websocket_api.async_response
async def websocket_save_channel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Create or update one channel."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return

    raw = dict(msg["channel"])
    existing = coordinator.config.channel(raw.get("id", ""))
    kind = str(raw.get("kind") or "ha_service")
    raw["config"] = _merge_secrets(existing, kind, raw.get("config") or {})
    channel = Channel.from_dict(raw)

    handler = HANDLERS.get(channel.kind)
    if handler is None:
        connection.send_error(msg["id"], "unknown_kind", channel.kind)
        return
    if missing := handler.validate(channel.config):
        connection.send_error(msg["id"], "missing_field", missing)
        return

    channels = [c for c in coordinator.config.channels if c.id != channel.id]
    channels.append(channel)
    coordinator.config.channels = channels
    await coordinator.store.async_save()
    await coordinator.async_config_changed()
    connection.send_result(msg["id"], {"channel": _safe_channel(channel)})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/channels/delete",
        # Not "id": that name belongs to the WebSocket protocol itself and a
        # command carrying it is rejected before it ever reaches this handler.
        vol.Required("channel_id"): str,
    }
)
@websocket_api.async_response
async def websocket_delete_channel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Delete one channel and unhook it from every severity."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    channel_id = msg["channel_id"]
    coordinator.config.channels = [
        c for c in coordinator.config.channels if c.id != channel_id
    ]
    for severity in coordinator.config.severities:
        severity.channels = [c for c in severity.channels if c != channel_id]
    await coordinator.store.async_save()
    await coordinator.async_config_changed()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/channels/test", vol.Required("channel"): dict}
)
@websocket_api.async_response
async def websocket_test_channel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send a test message through a channel, saved or not."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    raw = dict(msg["channel"])
    existing = coordinator.config.channel(raw.get("id", ""))
    kind = str(raw.get("kind") or "ha_service")
    raw["config"] = _merge_secrets(existing, kind, raw.get("config") or {})
    try:
        await coordinator.dispatcher.async_test(Channel.from_dict(raw))
    except ChannelError as err:
        connection.send_error(msg["id"], "send_failed", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/ignore",
        vol.Required("key"): str,
        vol.Required("ignored"): bool,
        vol.Optional("until"): vol.Any(str, None),
        vol.Optional("reason", default=""): str,
    }
)
@websocket_api.async_response
async def websocket_ignore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Silence one repository, or bring it back."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    config = coordinator.config
    config.ignored = [i for i in config.ignored if i.key != msg["key"]]
    if msg["ignored"]:
        config.ignored.append(
            Ignore(
                key=msg["key"],
                until=msg.get("until"),
                reason=msg.get("reason", ""),
            )
        )
    await coordinator.store.async_save()
    await coordinator.async_scan()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/mark_used",
        vol.Required("key"): str,
        vol.Required("used"): bool,
    }
)
@websocket_api.async_response
async def websocket_mark_used(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Override the usage verdict for one repository."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    marked = set(coordinator.config.marked_used)
    if msg["used"]:
        marked.add(msg["key"])
    else:
        marked.discard(msg["key"])
    coordinator.config.marked_used = sorted(marked)
    await coordinator.store.async_save()
    await coordinator.async_scan()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/history",
        vol.Optional("limit", default=200): int,
        vol.Optional("key"): vol.Any(str, None),
        vol.Optional("kind"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def websocket_history(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Return the recorded changes, newest first."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "IntegrationGuard is not loaded")
        return
    events = await coordinator.history.async_query(
        limit=msg["limit"], key=msg.get("key"), kind=msg.get("kind")
    )
    connection.send_result(msg["id"], {"events": events})
