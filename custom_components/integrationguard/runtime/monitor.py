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
from homeassistant.helpers.start import async_at_started
from homeassistant.loader import IntegrationNotLoaded, async_get_loaded_integration
from homeassistant.util import dt as dt_util

from ..const import (
    EVENT_RUNTIME_CHANGED,
    RUNTIME_DEBOUNCE_SECONDS,
    RUNTIME_GRACE_STATES,
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

# While an entry is being set up or unloaded, the last verdict still stands.
# Otherwise a broken entry being reloaded would look fixed for a moment.
IN_PROGRESS = {ConfigEntryState.SETUP_IN_PROGRESS, ConfigEntryState.UNLOAD_IN_PROGRESS}


def _worse(left: str, right: str) -> str:
    """Return whichever of two runtime states is the worse one."""
    order = list(RUNTIME_ORDER)
    left_index = order.index(left) if left in order else 0
    right_index = order.index(right) if right in order else 0
    return left if left_index >= right_index else right


def _stamp(book: dict[str, list[str]], key: str, state: str, now: datetime) -> str:
    """Return since when a key has been in a state, starting the clock if new."""
    remembered = book.get(key)
    if remembered is None or remembered[0] != state:
        remembered = [state, now.isoformat()]
        book[key] = remembered
    return remembered[1]


def _elapsed(since: str | None, now: datetime, grace: timedelta) -> bool:
    """Return whether a state that began at since has outlasted the grace."""
    started = dt_util.parse_datetime(since) if since else None
    return started is not None and now - started >= grace


def _is_news(
    previous: tuple[str, bool, tuple[str, ...] | None] | None,
    current: tuple[str, bool, tuple[str, ...]],
) -> bool:
    """Return whether a domain's new picture is worth announcing."""
    if previous is None or previous[:2] != current[:2]:
        return True
    # Same verdict. Only an entry joining the affected ones is news; fewer
    # broken entries is not, and neither is learning the ids after an update.
    if previous[2] is None:
        return False
    return not set(current[2]) <= set(previous[2])


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
        # The same per config entry. The grace period is judged per entry, so
        # a second device dropping out waits its turn like the first one did.
        self._entry_since: dict[str, list[str]] = {}
        # Domain -> (state, problem, affected entry ids). None for the ids
        # means "not known yet", as after an update from an older version.
        self._previous: dict[str, tuple[str, bool, tuple[str, ...] | None]] = {}
        self._unsubs: list[Callable[[], None]] = []
        self._unsub_grace: Callable[[], None] | None = None
        self._debouncer: Debouncer | None = None
        # False until Home Assistant has finished starting. Before that most
        # entries are simply not set up yet, which says nothing.
        self.ready = False

    async def async_start(self) -> None:
        """Subscribe to the two registries, and look once Home Assistant is up."""
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
        self._unsubs.append(async_at_started(self.hass, self._handle_started))

    async def _handle_started(self, _hass: HomeAssistant) -> None:
        """Take the first look, and always report it.

        The first report is what tells the listener that the picture is
        complete, even when it is the same as before the restart.
        """
        self.ready = True
        await self._async_refresh(first=True)

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
            "entry_since": self._entry_since,
            "previous": {
                domain: [state, problem, list(ids) if ids is not None else None]
                for domain, (state, problem, ids) in self._previous.items()
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
        self._entry_since = {
            entry_id: list(value)
            for entry_id, value in (data.get("entry_since") or {}).items()
            if isinstance(value, list) and len(value) == 2
        }
        self._previous = {}
        for domain, value in (data.get("previous") or {}).items():
            if not isinstance(value, list) or len(value) not in (2, 3):
                continue
            ids = value[2] if len(value) == 3 else None
            self._previous[domain] = (
                value[0],
                bool(value[1]),
                tuple(ids) if isinstance(ids, list) else None,
            )

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

    async def _async_refresh(self, first: bool = False) -> None:
        """Rebuild the picture and announce what changed."""
        if not self.ready:
            return
        settings = self._settings()
        if not settings.runtime_enabled:
            if self.states:
                self.states = {}
                self._on_change([])
            return

        self.states = self._evaluate(settings)
        self._schedule_grace_check(settings)

        current = {
            domain: (
                info.state,
                info.problem,
                tuple(sorted(entry["entry_id"] for entry in info.affected)),
            )
            for domain, info in self.states.items()
        }
        changed: list[RuntimeInfo] = []
        for domain, value in current.items():
            previous = self._previous.get(domain)
            if not _is_news(previous, value):
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
        if current != self._previous or first:
            self._previous = current
            self._on_change(changed)

    def _evaluate(self, settings: Settings) -> dict[str, RuntimeInfo]:
        """Look at every watched domain and judge it."""
        issues = self._issues_by_domain()
        now = dt_util.utcnow()
        grace = timedelta(minutes=max(0, settings.runtime_grace_minutes))
        result: dict[str, RuntimeInfo] = {}
        seen_entries: set[str] = set()

        for domain in self._watched_domains(settings):
            # Entries the user ignored during discovery exist only to stop
            # Home Assistant offering the device again. It never sets them up
            # (config_entries.py: "if self.source == SOURCE_IGNORE"), so they
            # are permanently "not loaded" and say nothing about the
            # integration.
            entries = self.hass.config_entries.async_entries(
                domain, include_ignore=False
            )
            if not entries:
                # No config entry means nothing to judge here. Whether the
                # integration is used at all is a different question.
                continue

            info = RuntimeInfo(
                domain=domain,
                name=self._integration_name(domain),
                full_name=self._domains.get(domain, ""),
                title=entries[0].title,
                repairs=issues.get(domain, []),
            )
            for entry in entries:
                state = self._entry_state(entry)
                seen_entries.add(entry.entry_id)
                info.entries.append(
                    {
                        "entry_id": entry.entry_id,
                        "title": entry.title,
                        "state": state,
                        "reason": entry.reason or "",
                        "since": _stamp(self._entry_since, entry.entry_id, state, now),
                    }
                )
                if _worse(info.state, state) != info.state:
                    # Name the entry the state and the reason belong to, not
                    # just whichever one happens to come first.
                    info.state = state
                    info.title = entry.title
                    info.reason = entry.reason or ""
                    info.translation_key = entry.error_reason_translation_key

            self._finalise(info, now, grace)
            result[domain] = info

        for domain in set(self._state_since) - set(result):
            del self._state_since[domain]
        for entry_id in set(self._entry_since) - seen_entries:
            del self._entry_since[entry_id]
        return result

    def _finalise(self, info: RuntimeInfo, now: datetime, grace: timedelta) -> None:
        """Stamp the state with a start time and decide whether it counts."""
        info.since = _stamp(self._state_since, info.domain, info.state, now)

        if info.state not in RUNTIME_PROBLEM_STATES:
            info.problem = bool(info.repairs)
            return

        worst = [entry for entry in info.entries if entry["state"] == info.state]
        if info.state in RUNTIME_GRACE_STATES:
            # Normal for a while after a restart or a brief outage.
            if not worst:
                info.problem = _elapsed(info.since, now, grace)
                return
            worst = [
                entry for entry in worst if _elapsed(entry.get("since"), now, grace)
            ]

        info.affected = worst
        info.problem = bool(worst) or not info.entries
        if worst:
            # Name an entry that is actually part of the problem.
            info.title = worst[0]["title"]
            info.reason = worst[0]["reason"]

    def _schedule_grace_check(self, settings: Settings) -> None:
        """Wake up again when the earliest grace period runs out."""
        if self._unsub_grace is not None:
            self._unsub_grace()
            self._unsub_grace = None

        now = dt_util.utcnow()
        grace = timedelta(minutes=max(0, settings.runtime_grace_minutes))
        delays = []
        for info in self.states.values():
            if info.state not in RUNTIME_GRACE_STATES:
                continue
            stamps = [
                entry.get("since")
                for entry in info.entries
                if entry["state"] == info.state
            ] or [info.since]
            for stamp in stamps:
                started = dt_util.parse_datetime(stamp) if stamp else None
                if started is None or now - started >= grace:
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
            return {
                entry.domain
                for entry in self.hass.config_entries.async_entries(
                    include_ignore=False
                )
            }
        return set(self._domains)

    def _integration_name(self, domain: str) -> str:
        """Return the integration's display name, the domain if unknown."""
        try:
            return async_get_loaded_integration(self.hass, domain).name
        except (IntegrationNotLoaded, KeyError):
            return domain

    def _entry_state(self, entry: ConfigEntry) -> str:
        """Return the runtime state of one config entry."""
        if entry.disabled_by is not None:
            return RuntimeState.DISABLED
        if any(entry.async_get_active_flows(self.hass, REAUTH_SOURCES)):
            return RuntimeState.REAUTH
        if entry.state in IN_PROGRESS and (
            remembered := self._entry_since.get(entry.entry_id)
        ):
            return remembered[0]
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
