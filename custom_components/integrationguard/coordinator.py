"""Runs the scans and keeps the result everything else reads from."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_point_in_time
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util

from .const import (
    CONF_GITHUB_TOKEN,
    EVENT_SCAN_COMPLETED,
    EVENT_STATUS_CHANGED,
    HACS_CATEGORIES,
    HASSIO_DOMAIN,
    SIGNAL_UPDATED,
    STARTUP_DELAY_SECONDS,
    Category,
    RuleId,
    Status,
)
from .health.engine import evaluate
from .history import History
from .models import Config, RepositoryHealth, RepositoryInfo, RuntimeInfo, ScanResult
from .notify.dispatcher import Dispatcher, next_quiet_end
from .notify.messages import (
    build_problem_messages,
    build_recovery_message,
    collect_changes,
)
from .runtime.monitor import RuntimeMonitor
from .sources import apps as apps_source, hacs as hacs_source
from .sources.github import GitHubSource
from .sources.store_data import StoreData, parse_last_updated
from .store import IntegrationGuardStore
from .usage.engine import UsageResult, async_evaluate

_LOGGER = logging.getLogger(__name__)

RELEASE_RULES = (RuleId.RELEASE_AGE, RuleId.RELEASE_AGE_SEVERE)


class IntegrationGuardCoordinator:
    """Owns the scan schedule, the data sources and the latest result."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: IntegrationGuardStore,
    ) -> None:
        """Set up the coordinator without touching the network yet."""
        self.hass = hass
        self.entry = entry
        self.store = store
        self.result: ScanResult | None = None
        self.store_data = StoreData(hass)
        self.github = GitHubSource(hass, self.github_token)
        self.runtime = RuntimeMonitor(
            hass, lambda: self.config.settings, self._handle_runtime_change
        )
        self.history = History(hass)
        self.dispatcher = Dispatcher(hass, store.config)
        # What the user has actually been told, which is not the same as what
        # the last scan found: the quiet hours may have held something back.
        self._announced: dict[str, str] = {}
        self._unsub_quiet: Any = None
        self._previous: dict[str, str] = {}
        self._last_scan: str | None = None
        self._lock = asyncio.Lock()
        self._unsub_timer: Any = None
        self._unsub_start: Any = None

    @property
    def config(self) -> Config:
        """Return the current configuration."""
        return self.store.config

    @property
    def github_token(self) -> str | None:
        """Return the stored GitHub token, if there is one."""
        return self.entry.data.get(CONF_GITHUB_TOKEN) or None

    async def async_set_github_token(self, token: str) -> None:
        """Store a new token. An actual change reloads the entry."""
        if (self.github_token or "") == token:
            return
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, CONF_GITHUB_TOKEN: token}
        )

    async def async_start(self) -> None:
        """Restore the caches and arm the schedule."""
        state = await self.store.async_load_state()
        self.store_data.restore(state.get("store_data"))
        self.github.restore(state.get("github"))
        self.runtime.restore(state.get("runtime"))
        self._previous = dict(state.get("previous") or {})
        self._announced = dict(state.get("announced") or {})

        await self.history.async_setup()
        await self.history.async_purge(self.config.settings.history_retention_days)
        await self.runtime.async_start()
        self._unsub_start = async_at_started(self.hass, self._handle_started)
        self._schedule_next()

    async def async_stop(self) -> None:
        """Cancel every timer and subscription."""
        await self.runtime.async_stop()
        for unsub in (self._unsub_timer, self._unsub_start, self._unsub_quiet):
            if unsub is not None:
                unsub()
        self._unsub_timer = None
        self._unsub_start = None
        self._unsub_quiet = None

    @callback
    def _handle_started(self, _: HomeAssistant) -> None:
        """Run the first scan a while after Home Assistant came up.

        HACS needs a moment to load its repositories, and a restart is a bad
        time to hammer GitHub.
        """

        async def _run(_now: datetime) -> None:
            await self.async_scan()

        async_call_later(self.hass, STARTUP_DELAY_SECONDS, _run)

    @callback
    def _schedule_next(self) -> None:
        """Arm the timer for the next scheduled scan."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        target = self._next_run()
        _LOGGER.debug("Next scan at %s", target)

        async def _run(now: datetime) -> None:
            self._unsub_timer = None
            if self.config.settings.monitoring_enabled:
                await self.async_scan()
            else:
                _LOGGER.debug("Monitoring is off, skipping the scheduled scan")
            self._schedule_next()

        self._unsub_timer = async_track_point_in_time(self.hass, _run, target)

    def _next_run(self) -> datetime:
        """Return when the next scan is due.

        The schedule is anchored to the configured time of day: with a 24 hour
        interval that is one run per day at that time, with a 6 hour interval it
        is that time plus every six hours after it.
        """
        settings = self.config.settings
        hours = max(1, int(settings.scan_interval_hours))
        now = dt_util.now()
        try:
            hour, minute = (int(part) for part in settings.scan_time.split(":", 1))
        except ValueError:
            _LOGGER.warning(
                "Cannot read the configured scan time %r, falling back to 04:00",
                settings.scan_time,
            )
            hour, minute = 4, 0
        anchor = now.replace(
            hour=hour % 24, minute=minute % 60, second=0, microsecond=0
        )
        step = timedelta(hours=hours)
        while anchor <= now:
            anchor += step
        return anchor

    async def async_config_changed(self) -> None:
        """React to settings the user changed in the panel."""
        self.dispatcher.set_config(self.config)
        self._schedule_next()
        self.runtime.schedule_refresh()
        self._notify()

    @callback
    def _handle_runtime_change(self, changed: list[RuntimeInfo]) -> None:
        """Announce, record and save after a runtime state changed."""
        self._notify()
        self.hass.async_create_task(self._async_runtime_changed(changed))

    async def _async_runtime_changed(self, changed: list[RuntimeInfo]) -> None:
        """Write the history and tell the user, unless it is quiet hours."""
        if changed:
            await self.history.async_record(
                [
                    {
                        "kind": "runtime",
                        "key": info.domain,
                        "name": info.title or info.domain,
                        "category": "integration",
                        "status": info.state,
                        "detail": {"reason": info.reason, "problem": info.problem},
                    }
                    for info in changed
                ]
            )
            if self.config.settings.monitoring_enabled:
                now = dt_util.utcnow()
                for info in changed:
                    if info.problem:
                        await self.dispatcher.async_send_runtime(info, now)
                self._schedule_quiet_flush()
        await self._async_save_state()

    async def async_scan(self, *, force: bool = False) -> ScanResult | None:
        """Run one full scan. Concurrent calls wait for the running one."""
        if self._lock.locked():
            _LOGGER.debug("A scan is already running, waiting for it to finish")
            async with self._lock:
                return self.result
        async with self._lock:
            return await self._scan(force=force)

    async def _scan(self, *, force: bool = False) -> ScanResult | None:
        """Collect the data, judge it and publish the result."""
        started = dt_util.utcnow()
        settings = self.config.settings
        errors: dict[str, str] = {}

        infos = hacs_source.async_installed_repositories(self.hass)
        if infos is None:
            _LOGGER.warning(
                "HACS is not available, IntegrationGuard has nothing to look at"
            )
            if self.result is not None:
                # Keep the last picture rather than replacing it with an empty
                # one; HACS being briefly gone is not the same as owning no
                # repositories.
                self.result.source_errors["hacs"] = "unavailable"
                self._notify()
                return self.result
            errors["hacs"] = "unavailable"
            infos = []

        wanted_categories = set(settings.categories_health)
        infos = [info for info in infos if info.category in wanted_categories]

        if Category.APP in wanted_categories:
            apps = apps_source.async_installed_apps(self.hass)
            if apps is None and apps_source.async_is_available(self.hass):
                errors["supervisor"] = "unavailable"
            elif apps:
                infos.extend(apps)

        await self._enrich(infos, errors, force=force)

        usage: dict[str, UsageResult] = {}
        orphans: list[dict[str, Any]] = []
        try:
            usage, orphans = await async_evaluate(self.hass, infos, self.config)
        except Exception:
            _LOGGER.exception("The usage check failed, reporting health only")
            errors["usage"] = "failed"

        now = dt_util.utcnow()
        repositories = [self._judge(info, now, usage.get(info.key)) for info in infos]
        repositories.sort(key=lambda item: item.key.lower())

        result = ScanResult(
            started=started,
            finished=dt_util.utcnow(),
            repositories=repositories,
            orphans=orphans,
            source_errors=errors,
            github_remaining=self.github.remaining,
            github_pending=self.github.pending(infos),
        )
        self.result = result
        self.runtime.schedule_refresh()
        domains = {
            item.info.domain: item.full_name
            for item in repositories
            if item.info.category == Category.INTEGRATION and item.info.domain
        }
        if Category.APP in wanted_categories and apps_source.async_is_available(
            self.hass
        ):
            # The Supervisor raises its own repair messages — unhealthy and
            # unsupported system states land there.
            domains[HASSIO_DOMAIN] = ""
        self.runtime.set_domains(domains)
        await self._publish(result)
        return result

    async def _enrich(
        self,
        infos: list[RepositoryInfo],
        errors: dict[str, str],
        *,
        force: bool = False,
    ) -> None:
        """Fill in everything HACS itself could not tell us."""
        await self.store_data.async_refresh_lists()

        # Only HACS has a store index. Apps never have a push date from the
        # Supervisor, so without this they would ask for a category endpoint
        # that does not exist.
        missing = {
            info.category
            for info in infos
            if info.last_push is None
            and info.is_default_store
            and info.category in HACS_CATEGORIES
        }
        if missing:
            await self.store_data.async_refresh_categories(
                missing, {info.full_name.lower() for info in infos}
            )

        fetched = dt_util.utcnow().isoformat()
        for info in infos:
            if info.category not in HACS_CATEGORIES:
                continue
            info.removed_from_hacs = self.store_data.is_removed(info.full_name)
            info.critical = self.store_data.is_critical(info.full_name)
            self._apply_store_entry(info, fetched)

        need_release = any(
            (rule := self.config.rule(str(rule_id))) is not None and rule.enabled
            for rule_id in RELEASE_RULES
        )
        await self.github.async_update(infos, need_release=need_release, force=force)

        errors.update(self.store_data.errors)
        errors.update(self.github.errors)

    def _apply_store_entry(self, info: RepositoryInfo, fetched: str) -> None:
        """Copy fields from the HACS store data where ours are still empty."""
        entry = self.store_data.get(info.full_name)
        if not entry:
            return
        if info.last_push is None:
            info.last_push = parse_last_updated(entry.get("last_updated"))
        if info.stars is None and entry.get("stargazers_count") is not None:
            info.stars = int(entry["stargazers_count"])
        if info.open_issues is None and entry.get("open_issues") is not None:
            info.open_issues = int(entry["open_issues"])
        if not info.last_version and entry.get("last_version"):
            info.last_version = entry["last_version"]
            info.has_releases = True
        if not info.min_ha_version and entry.get("homeassistant"):
            info.min_ha_version = entry["homeassistant"]
        info.data_sources["store"] = fetched

    def _judge(
        self, info: RepositoryInfo, now: datetime, usage: UsageResult | None
    ) -> RepositoryHealth:
        """Run the rules against one repository."""
        verdict = usage or UsageResult()
        findings, score, status = evaluate(
            info,
            self.config,
            now=now,
            ha_version=HA_VERSION,
            usage=verdict.usage,
        )
        return RepositoryHealth(
            info=info,
            findings=findings,
            score=score,
            status=status,
            usage=verdict.usage,
            usage_confidence=verdict.confidence,
            usage_detail=verdict.detail,
            ignored=self._is_ignored(info.key, now),
        )

    def _is_ignored(self, key: str, now: datetime) -> bool:
        """Return whether the user asked not to hear about this repository."""
        ignore = self.config.ignore(key)
        if ignore is None:
            return False
        if not ignore.until:
            return True
        until = dt_util.parse_datetime(ignore.until)
        return until is None or until > now

    async def _publish(self, result: ScanResult) -> None:
        """Fire the events, save the state and wake the entities up."""
        by_key = {item.key: item for item in result.repositories if not item.ignored}
        current = {key: item.status for key, item in by_key.items()}
        for key, status in current.items():
            previous = self._previous.get(key)
            if previous is None or previous == status:
                continue
            item = by_key[key]
            self.hass.bus.async_fire(
                EVENT_STATUS_CHANGED,
                {
                    "key": key,
                    "repository": item.full_name,
                    "name": item.info.name,
                    "category": item.info.category,
                    "previous": previous,
                    "status": status,
                    "url": item.info.url,
                },
            )
        self._previous = current

        self.hass.bus.async_fire(
            EVENT_SCAN_COMPLETED,
            {
                "repositories": len(result.repositories),
                "problems": len(result.problems()),
                "duration": round(result.duration, 1),
                "errors": sorted(result.source_errors),
            },
        )

        await self._async_record(result)
        await self._async_announce(result)

        self._last_scan = result.finished.isoformat()
        await self._async_save_state()
        self._notify()
        _LOGGER.debug(
            "Scan finished in %.1fs: %s repositories, %s with problems",
            result.duration,
            len(result.repositories),
            len(result.problems()),
        )

    async def _async_record(self, result: ScanResult) -> None:
        """Write every verdict that moved into the history."""
        events = []
        for item in result.repositories:
            previous = self._previous.get(item.key)
            if previous is None or previous == item.status:
                continue
            events.append(
                {
                    "kind": "status",
                    "key": item.key,
                    "name": item.info.name,
                    "category": item.info.category,
                    "previous": previous,
                    "status": item.status,
                    "detail": {
                        "score": item.score,
                        "rules": [f.rule_id for f in item.findings],
                    },
                }
            )
        await self.history.async_record(events)

    async def _async_announce(self, result: ScanResult) -> None:
        """Tell the user what changed, unless the quiet hours say otherwise."""
        if not self.config.settings.monitoring_enabled:
            return
        problems, recoveries = collect_changes(result.repositories, self._announced)
        if not self.config.settings.notify_on_recovery:
            recoveries = []
        if not problems and not recoveries:
            return

        language = self.dispatcher.language
        now = dt_util.utcnow()
        messages = build_problem_messages(self.config, problems, language)
        if recovery := build_recovery_message(self.config, recoveries, language):
            messages.append(recovery)

        held = False
        for message in messages:
            if self.dispatcher.is_held(message, now):
                # Not marking these as announced is what makes them come back
                # once the quiet hours are over — and quietly disappear if they
                # resolved themselves in the meantime.
                held = True
                continue
            await self.dispatcher.async_send(message)
            for key in message.keys:
                item = next((r for r in result.repositories if r.key == key), None)
                if item is not None:
                    self._announced[key] = item.status
        if held:
            self._schedule_quiet_flush()

    @callback
    def _schedule_quiet_flush(self) -> None:
        """Wake up when the quiet hours end and deliver what was held back."""
        if self._unsub_quiet is not None:
            return
        target = next_quiet_end(self.config.settings.quiet_hours, dt_util.now())
        if target is None:
            return

        async def _flush(_now: datetime) -> None:
            self._unsub_quiet = None
            await self.dispatcher.async_flush_runtime(self.runtime.states)
            if self.result is not None:
                await self._async_announce(self.result)
            await self._async_save_state()

        _LOGGER.debug("Holding notifications until %s", target)
        self._unsub_quiet = async_track_point_in_time(self.hass, _flush, target)

    async def _async_save_state(self) -> None:
        """Write the caches and the last known states to disk."""
        await self.store.async_save_state(
            {
                "store_data": self.store_data.to_state(),
                "github": self.github.to_state(),
                "runtime": self.runtime.to_state(),
                "previous": self._previous,
                "announced": self._announced,
                "last_scan": self._last_scan,
            }
        )

    @callback
    def _notify(self) -> None:
        """Tell the entities that something changed."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    def average_score(self) -> int | None:
        """Return the mean score across all judged repositories."""
        if not self.result or not self.result.repositories:
            return None
        scores = [r.score for r in self.result.repositories if not r.ignored]
        if not scores:
            return None
        return round(sum(scores) / len(scores))

    def worst(self) -> RepositoryHealth | None:
        """Return the repository with the lowest score."""
        if not self.result:
            return None
        candidates = [r for r in self.result.repositories if not r.ignored]
        return min(candidates, key=lambda r: r.score) if candidates else None

    def count(self, status: Status) -> int:
        """Return how many repositories carry a given status."""
        return len(self.result.by_status(status)) if self.result else 0
