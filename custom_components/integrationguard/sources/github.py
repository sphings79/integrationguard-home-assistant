"""Asks GitHub for the few things the HACS data does not contain.

Namely: whether a repository is archived or gone, when its newest release came
out, and current numbers for repositories that are not in the HACS store.

Without a token GitHub allows 60 requests per hour and IP. Conditional requests
that answer ``304 Not Modified`` do not count against that budget, so only the
first run is expensive — afterwards a daily refresh of a hundred repositories
costs almost nothing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import GITHUB_API, GITHUB_RESERVE
from ..models import RepositoryInfo

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=30)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "IntegrationGuard",
}
# Repositories whose cached answer is older than this are refreshed first.
STALE_AFTER = timedelta(hours=20)


class GitHubSource:
    """Fetches and caches the GitHub side of the picture."""

    def __init__(self, hass: HomeAssistant, token: str | None = None) -> None:
        """Set up an empty cache."""
        self._hass = hass
        self._token = token
        self._cache: dict[str, dict[str, Any]] = {}
        self.remaining: int | None = None
        self.reset_at: datetime | None = None
        self.errors: dict[str, str] = {}

    def set_token(self, token: str | None) -> None:
        """Replace the token, e.g. after the user entered one in the panel."""
        self._token = token

    def to_state(self) -> dict[str, Any]:
        """Return the cache in a form the state store can hold."""
        return {"cache": self._cache}

    def restore(self, data: dict[str, Any] | None) -> None:
        """Restore a cache written by a previous run."""
        if data:
            self._cache = dict(data.get("cache") or {})

    def pending(self, infos: list[RepositoryInfo]) -> int:
        """Return how many repositories still wait for a fresh answer."""
        now = dt_util.utcnow()
        names = {info.full_name for info in infos if info.full_name}
        return sum(1 for name in names if self._is_stale(name, now))

    async def async_update(
        self, infos: list[RepositoryInfo], *, need_release: bool, force: bool = False
    ) -> None:
        """Refresh what the budget allows, then apply the cache to every entry.

        Repositories that were not refreshed keep their last known answer, so a
        throttled run still produces a complete picture — just an older one.
        With ``force`` every repository is queued regardless of its age; the
        rate limit still applies.
        """
        now = dt_util.utcnow()
        stale = [info for info in infos if force or self._is_stale(info.full_name, now)]
        stale.sort(key=lambda info: self._fetched_at(info.full_name) or "")

        for info in stale:
            if not self._budget_left():
                _LOGGER.debug(
                    "GitHub budget spent, %s repositories keep their cached data",
                    len(stale) - stale.index(info),
                )
                break
            await self._refresh(info, need_release=need_release)

        for info in infos:
            self._apply(info)

    def _budget_left(self) -> bool:
        """Return whether another request may be spent right now."""
        if self.remaining is None:
            return True
        if self.remaining > GITHUB_RESERVE:
            return True
        # The hourly window may have rolled over since the last response.
        if self.reset_at is not None and dt_util.utcnow() >= self.reset_at:
            self.remaining = None
            return True
        return False

    def _fetched_at(self, full_name: str) -> str | None:
        """Return when the repository was last fetched."""
        entry = self._cache.get(full_name.lower())
        return entry.get("fetched") if entry else None

    def _is_stale(self, full_name: str, now: datetime) -> bool:
        """Return whether the cached answer is missing or old."""
        fetched = self._fetched_at(full_name)
        if not fetched:
            return True
        parsed = dt_util.parse_datetime(fetched)
        return parsed is None or now - parsed > STALE_AFTER

    async def _refresh(self, info: RepositoryInfo, *, need_release: bool) -> None:
        """Fetch one repository and, if wanted, its newest release."""
        key = info.full_name.lower()
        entry = self._cache.setdefault(key, {})

        payload, etag, status = await self._get(
            f"{GITHUB_API}/repos/{info.full_name}", entry.get("repo_etag")
        )
        if status in (404, 451):
            # 404 is gone or private, 451 is taken down. Either way it cannot be
            # downloaded any more.
            entry["gone"] = True
            entry["fetched"] = dt_util.utcnow().isoformat()
            return
        if status == 200 and isinstance(payload, dict):
            entry["gone"] = False
            entry["repo"] = {
                "archived": payload.get("archived"),
                "disabled": payload.get("disabled"),
                "pushed_at": payload.get("pushed_at"),
                "open_issues_count": payload.get("open_issues_count"),
                "stargazers_count": payload.get("stargazers_count"),
                "has_issues": payload.get("has_issues"),
                "default_branch": payload.get("default_branch"),
            }
            if etag:
                entry["repo_etag"] = etag
        elif status != 304:
            return

        if need_release and self._budget_left():
            await self._refresh_release(info, entry)
        entry["fetched"] = dt_util.utcnow().isoformat()

    async def _refresh_release(
        self, info: RepositoryInfo, entry: dict[str, Any]
    ) -> None:
        """Fetch the newest release of one repository."""
        payload, etag, status = await self._get(
            f"{GITHUB_API}/repos/{info.full_name}/releases/latest",
            entry.get("release_etag"),
        )
        if status == 404:
            # No release at all; the no_release rule covers that case.
            entry["release"] = None
            return
        if status == 200 and isinstance(payload, dict):
            entry["release"] = {
                "published_at": payload.get("published_at"),
                "tag_name": payload.get("tag_name"),
                "prerelease": payload.get("prerelease"),
            }
            if etag:
                entry["release_etag"] = etag

    def _apply(self, info: RepositoryInfo) -> None:
        """Copy what we know about a repository onto its facts object."""
        entry = self._cache.get(info.full_name.lower())
        if not entry or "fetched" not in entry:
            return

        if entry.get("gone"):
            info.gone = True
            info.data_sources["github"] = entry["fetched"]
            return
        info.gone = False

        repo = entry.get("repo") or {}
        if "archived" in repo:
            info.archived = bool(repo["archived"])
        if pushed := repo.get("pushed_at"):
            info.last_push = dt_util.parse_datetime(pushed) or info.last_push
        if (issues := repo.get("open_issues_count")) is not None:
            info.open_issues = int(issues)
        if (stars := repo.get("stargazers_count")) is not None:
            info.stars = int(stars)
        if (has_issues := repo.get("has_issues")) is not None:
            info.has_issues = bool(has_issues)
        if branch := repo.get("default_branch"):
            info.default_branch = info.default_branch or branch

        release = entry.get("release")
        if isinstance(release, dict):
            info.has_releases = True
            if published := release.get("published_at"):
                info.last_release_at = dt_util.parse_datetime(published)
            if not info.last_version and not release.get("prerelease"):
                info.last_version = release.get("tag_name")
        elif "release" in entry:
            info.has_releases = False

        info.data_sources["github"] = entry["fetched"]

    async def _get(self, url: str, etag: str | None) -> tuple[Any, str | None, int]:
        """Perform one conditional GET and keep the rate limit in view."""
        session = async_get_clientsession(self._hass)
        headers = dict(HEADERS)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if etag:
            headers["If-None-Match"] = etag
        try:
            response = await session.get(url, headers=headers, timeout=TIMEOUT)
            async with response:
                self._read_rate_limit(response)
                if response.status in (200, 304, 404, 451):
                    self.errors.pop(url, None)
                    payload = await response.json() if response.status == 200 else None
                    return payload, response.headers.get("ETag"), response.status
                if response.status in (403, 429):
                    self.errors["rate_limit"] = f"HTTP {response.status}"
                    _LOGGER.warning(
                        "GitHub refused the request (HTTP %s). Remaining budget: %s",
                        response.status,
                        self.remaining,
                    )
                    return None, None, response.status
                self.errors[url] = f"HTTP {response.status}"
                _LOGGER.warning("GitHub answered %s for %s", response.status, url)
                return None, None, response.status
        except (ClientError, TimeoutError) as err:
            self.errors[url] = str(err)
            _LOGGER.warning("Could not reach GitHub for %s: %s", url, err)
            return None, None, 0

    def _read_rate_limit(self, response: ClientResponse) -> None:
        """Remember how much of the hourly budget is left."""
        raw_remaining = response.headers.get("X-RateLimit-Remaining")
        if raw_remaining is not None:
            try:
                self.remaining = int(raw_remaining)
            except ValueError:
                self.remaining = None
        raw_reset = response.headers.get("X-RateLimit-Reset")
        if raw_reset is not None:
            try:
                self.reset_at = dt_util.utc_from_timestamp(int(raw_reset))
            except ValueError:
                self.reset_at = None
