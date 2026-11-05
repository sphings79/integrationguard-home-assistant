"""Reads the installed repositories out of the running HACS or Marketplace.

This is private API. Before Home Assistant 2026.11 HACS puts its ``HacsBase``
into ``hass.data["hacs"]``. From 2026.11 on the built-in Marketplace replaces
HACS and keeps its manager in the ``runtime_data`` of its config entry. Both
expose the repositories as objects of the same shape. Nothing here may raise
because of a renamed attribute, so every access goes through ``getattr`` and a
missing value becomes "unknown" rather than an error.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import HACS_DOMAIN, MARKETPLACE_DOMAIN, Category
from ..models import RepositoryInfo

_LOGGER = logging.getLogger(__name__)

KNOWN_CATEGORIES = {str(category) for category in Category}


def _parse_datetime(value: Any) -> datetime | None:
    """Parse HACS' ``last_updated``, which is GitHub's ``pushed_at``.

    The field defaults to the integer ``0`` when HACS never saw a value.
    """
    if not value or not isinstance(value, str):
        return None
    return dt_util.parse_datetime(value)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Read an attribute without ever raising."""
    try:
        value = getattr(obj, name, default)
    except Exception:
        _LOGGER.debug("Reading %s from HACS failed", name, exc_info=True)
        return default
    return default if value is None else value


def _manager(hass: HomeAssistant) -> Any | None:
    """Return the Marketplace manager, or the HACS instance, or None."""
    for entry in hass.config_entries.async_entries(MARKETPLACE_DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        manager = _get(entry, "runtime_data")
        if manager is not None:
            return manager
    return hass.data.get(HACS_DOMAIN)


def async_is_available(hass: HomeAssistant) -> bool:
    """Return whether the Marketplace or HACS is loaded and usable."""
    return _manager(hass) is not None


def _downloaded(registry: Any) -> list[Any]:
    """Return the installed repositories of either spelling of the registry."""
    # The Marketplace calls it ``list_installed``, HACS ``list_downloaded``.
    for name in ("list_installed", "list_downloaded"):
        if not hasattr(registry, name):
            continue
        value = getattr(registry, name)
        # Older HACS exposed this as a method rather than a property.
        return list(value() if callable(value) else value)
    raise AttributeError("no list of installed repositories")


def async_installed_repositories(
    hass: HomeAssistant,
) -> list[RepositoryInfo] | None:
    """Return every repository the Marketplace or HACS has downloaded.

    Returns ``None`` when neither is available at all, which is different from
    an empty list.
    """
    hacs = _manager(hass)
    if hacs is None:
        return None

    registry = _get(hacs, "repositories")
    if registry is None:
        _LOGGER.warning("HACS is loaded but exposes no repository registry")
        return None

    try:
        downloaded = _downloaded(registry)
    except Exception:
        _LOGGER.exception("Could not read the downloaded repositories from HACS")
        return None

    now = dt_util.utcnow().isoformat()
    result: list[RepositoryInfo] = []
    for repository in downloaded:
        info = _build(repository, registry, now)
        if info is not None:
            result.append(info)
    _LOGGER.debug("HACS reports %s downloaded repositories", len(result))
    return result


def _build(repository: Any, registry: Any, now: str) -> RepositoryInfo | None:
    """Convert one HACS repository object into our own facts object."""
    data = _get(repository, "data")
    if data is None:
        return None
    full_name = _get(data, "full_name", "")
    if not full_name:
        return None

    category = str(_get(data, "category", ""))
    if category not in KNOWN_CATEGORIES:
        _LOGGER.debug("Skipping %s: unknown category %s", full_name, category)
        return None

    hacs_id = str(_get(data, "id", ""))
    try:
        is_default = bool(registry.is_default(hacs_id))
    except Exception:
        is_default = True

    manifest = _get(repository, "repository_manifest")

    # ``archived`` is only meaningful when HACS itself asked GitHub. For
    # repositories that come out of the HACS store it stays False, which is not
    # the same as "confirmed not archived" — so False becomes "unknown" here and
    # the GitHub source decides.
    archived = True if _get(data, "archived") is True else None

    return RepositoryInfo(
        full_name=full_name,
        category=category,
        name=_display_name(repository, full_name),
        description=_get(data, "description", ""),
        domain=_get(data, "domain"),
        topics=list(_get(data, "topics", []) or []),
        hacs_id=hacs_id,
        is_default_store=is_default,
        file_name=str(_get(data, "file_name", "")),
        installed_version=str(_get(repository, "display_installed_version", "")),
        available_version=str(_get(repository, "display_available_version", "")),
        selected_tag=_get(data, "selected_tag"),
        default_branch=_get(data, "default_branch"),
        installed_commit=_get(data, "installed_commit"),
        last_commit=_get(data, "last_commit"),
        pending_update=bool(_get(repository, "pending_update", False)),
        has_releases=bool(_get(data, "releases", False)),
        last_version=_get(data, "last_version"),
        prerelease=_get(data, "prerelease"),
        last_push=_parse_datetime(_get(data, "last_updated")),
        stars=_as_int(_get(data, "stargazers_count")),
        open_issues=_as_int(_get(data, "open_issues")),
        downloads=_as_int(_get(data, "downloads")),
        archived=archived,
        has_issues=_get(data, "has_issues"),
        min_ha_version=_get(manifest, "homeassistant") if manifest else None,
        data_sources={"hacs": now},
    )


def _display_name(repository: Any, full_name: str) -> str:
    """Return the name HACS shows, falling back to the repository name."""
    name = _get(repository, "display_name", "")
    return str(name) if name else full_name.split("/")[-1]


def _as_int(value: Any) -> int | None:
    """Return an integer, or None when the value is not usable."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
