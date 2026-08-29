"""Config entry states and repair messages, kept up to date live.

This is the third pillar: not "is the repository still maintained" but "does
the setup work here". It deliberately stays out of the health score — an
expired API key says nothing about the state of a repository.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import (
    SIGNAL_CONFIG_ENTRY_CHANGED,
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from ..const import (
    EVENT_RUNTIME_CHANGED,
    RUNTIME_DEBOUNCE_SECONDS,
    RUNTIME_HEARTBEAT_MINUTES,
    RUNTIME_ORDER,
    RUNTIME_PROBLEM_STATES,
    RuntimeState,
)
from ..models import RepairIssue, RuntimeInfo, Settings

_LOGGER = logging.getLogger(__name__)

REAUTH_SOURCES = {SOURCE_REAUTH, SOURCE_RECONFIGURE}

STATE_MAP: dict[ConfigEntryState, RuntimeState] = {
    ConfigEntryState.LOADED: RuntimeState.OK,
    ConfigEntryState.SETUP_ERROR: RuntimeState.SETUP_ERROR,
    ConfigEntryState.MIGRATION_ERROR: RuntimeState.MIGRATION_ERROR,
    ConfigEntryState.SETUP_RETRY: RuntimeState.SETUP_RETRY,
    ConfigEntryState.FAILED_UNLOAD: RuntimeState.FAILED_UNLOAD,
    ConfigEntryState.NOT_LOADED: RuntimeState.NOT_LOADED,
    # Still working on it — not a verdict yet.
    ConfigEntryState.SETUP_IN_PROGRESS: RuntimeState.OK,
    ConfigEntryState.UNLOAD_IN_PROGRESS: RuntimeState.OK,
}


def _worse(left: str, right: str) -> str:
    """Return whichever of two runtime states is the worse one."""
    order = list(RUNTIME_ORDER)
    left_index = order.index(left) if left in order else 0
    right_index = order.index(right) if right in order else 0
    return left if left_index >= right_index else right


class RuntimeMonitor:
    """Keeps the runtime picture of the watched integrations current."""

    def __init__(
        self,
        hass: HomeAssistant,
        settings: Callable[[], Settings],
        on_change: Callable[[list[RuntimeInfo]], None],
    ) -> None:
        """Set up the monitor without subscribing yet."""
        self.hass = hass
        self._settings = settings
        self._on_change = on_change
        self.states: dict[str, RuntimeInfo] = {}
        # Domain of a HACS integration -> the repository it came from.
        self._domains: dict[str, str] = {}
        # Domain -> [state, when it began]. Drives both the "since" shown in
        # the panel and the grace period for retrying entries.
        self._state_since: dict[str, list[str]] = {}
        self._previous: dict[str, tuple[str, bool]] = {}
        self._unsubs: list[Callable[[], None]] = []
        self._unsub_grace: Callable[[], None] | None = None
        self._debouncer: Debouncer | None = None

    async def async_start(self) -> None:
        """Subscribe to the two registries and take a first look."""
        self._debouncer = Debouncer(
            self.hass,
            _LOGGER,
            cooldown=RUNTIME_DEBOUNCE_SECONDS,
            immediate=False,
            function=self._async_refresh,
        )
        self._unsubs.append(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._handle_entry_changed
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                ir.EVENT_REPAIRS_ISSUE_REGISTRY_UPDATED, self._handle_issue_changed
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._handle_heartbeat,
                timedelta(minutes=RUNTIME_HEARTBEAT_MINUTES),
            )
        )
        await self._async_refresh()

    async def async_stop(self) -> None:
        """Drop every subscription and timer."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._unsub_grace is not None:
            self._unsub_grace()
            self._unsub_grace = None
        if self._debouncer is not None:
            self._debouncer.async_shutdown()
            self._debouncer = None

    def to_state(self) -> dict[str, Any]:
        """Return what has to survive a restart."""
        return {
            "state_since": self._state_since,
            "previous": {
                domain: list(value) for domain, value in self._previous.items()
            },
        }

    def restore(self, data: dict[str, Any] | None) -> None:
        """Restore the grace timers and the last known states."""
        if not data:
            return
        self._state_since = {
            domain: list(value)
            for domain, value in (data.get("state_since") or {}).items()
            if isinstance(value, list) and len(value) == 2
        }
        self._previous = {
            domain: (value[0], bool(value[1]))
            for domain, value in (data.get("previous") or {}).items()
            if isinstance(value, list) and len(value) == 2
        }

    def set_domains(self, domains: dict[str, str]) -> None:
        """Tell the monitor which domains came from HACS."""
        if domains == self._domains:
            return
        self._domains = dict(domains)
        self.schedule_refresh()

    def problems(self) -> list[RuntimeInfo]:
        """Return the integrations that need attention."""
        return [info for info in self.states.values() if info.problem]

    def repairs(self) -> list[RepairIssue]:
        """Return every repair message on a watched integration."""
        return [issue for info in self.states.values() for issue in info.repairs]

    @callback
    def _handle_entry_changed(self, change: Any, entry: ConfigEntry) -> None:
        """React to a config entry being added, changed or removed."""
        self.schedule_refresh()

    @callback
    def _handle_issue_changed(self, event: Any) -> None:
        """React to a repair message appearing or disappearing."""
        self.schedule_refresh()

    @callback
    def _handle_heartbeat(self, _now: datetime) -> None:
        """Look again even when nothing announced itself."""
        self.schedule_refresh()

    @callback
    def schedule_refresh(self) -> None:
        """Ask for a refresh, collapsing bursts into one pass."""
        if self._debouncer is not None:
            self._debouncer.async_schedule_call()

    async def _async_refresh(self) -> None:
        """Rebuild the picture and announce what changed."""
        settings = self._settings()
        if not settings.runtime_enabled:
            if self.states:
                self.states = {}
                self._on_change([])
            return

        self.states = self._evaluate(settings)
        self._schedule_grace_check(settings)

        current = {
            domain: (info.state, info.problem) for domain, info in self.states.items()
        }
        changed: list[RuntimeInfo] = []
        for domain, value in current.items():
            previous = self._previous.get(domain)
            if previous == value:
                continue
            info = self.states[domain]
            changed.append(info)
            self.hass.bus.async_fire(
                EVENT_RUNTIME_CHANGED,
                {
                    "domain": domain,
                    "repository": info.full_name,
                    "url": info.url,
                    "state": info.state,
                    "problem": info.problem,
                    "previous": previous[0] if previous else None,
                    "reason": info.reason,
                },
            )
        for domain in set(self._previous) - set(current):
            self.hass.bus.async_fire(
                EVENT_RUNTIME_CHANGED,
                {
                    "domain": domain,
                    "repository": "",
                    "state": RuntimeState.NOT_APPLICABLE,
                    "problem": False,
                    "previous": self._previous[domain][0],
                    "reason": "",
                },
            )
        if current != self._previous:
            self._previous = current
            self._on_change(changed)

    def _evaluate(self, settings: Settings) -> dict[str, RuntimeInfo]:
        """Look at every watched domain and judge it."""
        issues = self._issues_by_domain()
        now = dt_util.utcnow()
        grace = timedelta(minutes=max(0, settings.runtime_grace_minutes))
        result: dict[str, RuntimeInfo] = {}

        for domain in self._watched_domains(settings):
            entries = self.hass.config_entries.async_entries(domain)
            if not entries:
                # No config entry means nothing to judge here. Whether the
                # integration is used at all is a different question.
                continue

            info = RuntimeInfo(
                domain=domain,
                full_name=self._domains.get(domain, ""),
                title=entries[0].title,
                repairs=issues.get(domain, []),
            )
            for entry in entries:
                state = self._entry_state(entry)
                info.entries.append(
                    {
                        "entry_id": entry.entry_id,
                        "title": entry.title,
                        "state": state,
                        "reason": entry.reason or "",
                    }
                )
                if _worse(info.state, state) != info.state:
                    info.state = state
                    info.reason = entry.reason or ""
                    info.translation_key = entry.error_reason_translation_key

            self._finalise(info, now, grace)
            result[domain] = info

        for domain in set(self._state_since) - set(result):
            del self._state_since[domain]
        return result

    def _finalise(self, info: RuntimeInfo, now: datetime, grace: timedelta) -> None:
        """Stamp the state with a start time and decide whether it counts."""
        remembered = self._state_since.get(info.domain)
        if remembered is None or remembered[0] != info.state:
            remembered = [info.state, now.isoformat()]
            self._state_since[info.domain] = remembered
        info.since = remembered[1]

        if info.state not in RUNTIME_PROBLEM_STATES:
            info.problem = bool(info.repairs)
            return
        if info.state != RuntimeState.SETUP_RETRY:
            info.problem = True
            return

        # Retrying is normal for a while after a restart or a brief outage.
        started = dt_util.parse_datetime(remembered[1])
        info.problem = started is not None and now - started >= grace

    def _schedule_grace_check(self, settings: Settings) -> None:
        """Wake up again when the earliest grace period runs out."""
        if self._unsub_grace is not None:
            self._unsub_grace()
            self._unsub_grace = None

        waiting = [
            info
            for info in self.states.values()
            if info.state == RuntimeState.SETUP_RETRY and not info.problem
        ]
        if not waiting:
            return

        now = dt_util.utcnow()
        grace = timedelta(minutes=max(0, settings.runtime_grace_minutes))
        delays = []
        for info in waiting:
            started = dt_util.parse_datetime(info.since or "") if info.since else None
            if started is None:
                continue
            delays.append(max(1.0, (started + grace - now).total_seconds()))
        if not delays:
            return

        async def _recheck(_now: datetime) -> None:
            self._unsub_grace = None
            await self._async_refresh()

        self._unsub_grace = async_call_later(self.hass, min(delays), _recheck)

    def _watched_domains(self, settings: Settings) -> set[str]:
        """Return the domains to look at."""
        if settings.runtime_include_all:
            return {entry.domain for entry in self.hass.config_entries.async_entries()}
        return set(self._domains)

    def _entry_state(self, entry: ConfigEntry) -> str:
        """Return the runtime state of one config entry."""
        if entry.disabled_by is not None:
            return RuntimeState.DISABLED
        if any(entry.async_get_active_flows(self.hass, REAUTH_SOURCES)):
            return RuntimeState.REAUTH
        return STATE_MAP.get(entry.state, RuntimeState.OK)

    def _issues_by_domain(self) -> dict[str, list[RepairIssue]]:
        """Collect the active repair messages, grouped by integration."""
        result: dict[str, list[RepairIssue]] = {}
        for issue in ir.async_get(self.hass).issues.values():
            if not issue.active or issue.dismissed_version:
                continue
            # An integration may raise an issue about another one; the message
            # belongs to the integration it is about.
            domain = issue.issue_domain or issue.domain
            result.setdefault(domain, []).append(
                RepairIssue(
                    domain=domain,
                    issue_id=issue.issue_id,
                    severity=str(issue.severity) if issue.severity else None,
                    is_fixable=issue.is_fixable,
                    translation_key=issue.translation_key,
                    learn_more_url=issue.learn_more_url,
                    breaks_in_ha_version=issue.breaks_in_ha_version,
                    created=issue.created.isoformat() if issue.created else None,
                )
            )
        return result
