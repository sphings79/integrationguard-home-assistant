"""Reads the public HACS data endpoints.

These need no token and carry an ETag, so a repeated fetch of unchanged data
costs a single conditional request. Used for the removed and critical lists,
and as a fallback whenever HACS itself could not supply a repository's dates.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..const import HACS_CRITICAL_URL, HACS_DATA_BASE, HACS_REMOVED_URL

_LOGGER = logging.getLogger(__name__)

TIMEOUT = ClientTimeout(total=60)
# Only these fields are kept from the category payloads; the rest of the
# multi-megabyte document is thrown away right after parsing.
KEPT_FIELDS = (
    "description",
    "domain",
    "downloads",
    "last_commit",
    "last_updated",
    "last_version",
    "open_issues",
    "prerelease",
    "stargazers_count",
    "topics",
)


class StoreData:
    """Cached view of the HACS data endpoints."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Set up an empty cache."""
        self._hass = hass
        self._etags: dict[str, str] = {}
        self.removed: set[str] = set()
        self.critical: set[str] = set()
        self._repositories: dict[str, dict[str, Any]] = {}
        self._wanted: set[str] = set()
        self.errors: dict[str, str] = {}

    def to_state(self) -> dict[str, Any]:
        """Return the cache in a form the state store can hold."""
        return {
            "etags": self._etags,
            "removed": sorted(self.removed),
            "critical": sorted(self.critical),
            "repositories": self._repositories,
            "wanted": sorted(self._wanted),
        }

    def restore(self, data: dict[str, Any] | None) -> None:
        """Restore a cache written by a previous run."""
        if not data:
            return
        self._etags = dict(data.get("etags") or {})
        self.removed = set(data.get("removed") or [])
        self.critical = set(data.get("critical") or [])
        self._repositories = dict(data.get("repositories") or {})
        self._wanted = set(data.get("wanted") or [])

    def get(self, full_name: str) -> dict[str, Any] | None:
        """Return the store entry for a repository, if one was fetched."""
        return self._repositories.get(full_name.lower())

    async def async_refresh_lists(self) -> None:
        """Refresh the removed and critical lists."""
        removed = await self._fetch(HACS_REMOVED_URL)
        if isinstance(removed, list):
            self.removed = {str(name).lower() for name in removed}
        critical = await self._fetch(HACS_CRITICAL_URL)
        if isinstance(critical, list):
            self.critical = {
                str(
                    entry.get("repository") if isinstance(entry, dict) else entry
                ).lower()
                for entry in critical
            }

    async def async_refresh_categories(
        self, categories: set[str], wanted: set[str]
    ) -> None:
        """Fetch the category payloads and keep only the wanted repositories.

        When the set of wanted repositories grew, the stored ETag is ignored —
        the cached subset would not contain the new names.
        """
        force = not wanted <= self._wanted
        for category in sorted(categories):
            url = f"{HACS_DATA_BASE}/{category}/data.json"
            payload = await self._fetch(url, ignore_etag=force)
            if not isinstance(payload, dict):
                continue
            for entry in payload.values():
                if not isinstance(entry, dict):
                    continue
                full_name = str(entry.get("full_name") or "").lower()
                if full_name not in wanted:
                    continue
                kept = {k: entry[k] for k in KEPT_FIELDS if k in entry}
                kept["category"] = category
                manifest = entry.get("manifest")
                if isinstance(manifest, dict):
                    kept["manifest_name"] = manifest.get("name")
                    kept["homeassistant"] = manifest.get("homeassistant")
                self._repositories[full_name] = kept
        self._wanted |= wanted

    def is_removed(self, full_name: str) -> bool:
        """Return whether HACS dropped this repository from its store."""
        return full_name.lower() in self.removed

    def is_critical(self, full_name: str) -> bool:
        """Return whether the repository is on the HACS security list."""
        return full_name.lower() in self.critical

    async def _fetch(self, url: str, *, ignore_etag: bool = False) -> Any:
        """Fetch a JSON document, using the stored ETag when we have one."""
        session = async_get_clientsession(self._hass)
        headers: dict[str, str] = {}
        etag = None if ignore_etag else self._etags.get(url)
        if etag:
            headers["If-None-Match"] = etag
        try:
            response = await session.get(url, headers=headers, timeout=TIMEOUT)
            async with response:
                return await self._read(url, response)
        except (ClientError, TimeoutError) as err:
            self.errors[url] = str(err)
            _LOGGER.warning("Could not fetch %s: %s", url, err)
            return None

    async def _read(self, url: str, response: ClientResponse) -> Any:
        """Turn one response into data, or None when nothing changed."""
        if response.status == 304:
            _LOGGER.debug("%s unchanged", url)
            self.errors.pop(url, None)
            return None
        if response.status != 200:
            self.errors[url] = f"HTTP {response.status}"
            _LOGGER.warning("Fetching %s returned HTTP %s", url, response.status)
            return None
        raw = await response.read()
        # Multi-megabyte documents: parsing belongs off the event loop.
        data = await self._hass.async_add_executor_job(json.loads, raw)
        if new_etag := response.headers.get("ETag"):
            self._etags[url] = new_etag
        self.errors.pop(url, None)
        _LOGGER.debug("Fetched %s (%s bytes)", url, len(raw))
        return data


def parse_last_updated(value: Any) -> Any:
    """Parse the ``last_updated`` field of a store entry."""
    if not value or not isinstance(value, str):
        return None
    return dt_util.parse_datetime(value)
