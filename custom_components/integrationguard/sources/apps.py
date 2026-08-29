"""Reads the installed apps (formerly add-ons) from the Supervisor.

Apps do not come from HACS, but they are installed software with a source
repository, so the same questions apply: is it still maintained, is it still
offered, is it even being used. Only available on Home Assistant OS and
Supervised installations; everywhere else this quietly reports nothing.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.hassio import is_hassio
from homeassistant.util import dt as dt_util

from ..const import Category
from ..models import RepositoryInfo

_LOGGER = logging.getLogger(__name__)

# The first two path segments after the host are owner and repository; an
# app often points deeper into the tree, e.g. ".../tree/master/<addon>".
GITHUB_URL = re.compile(r"github\.com[:/]+([^/\s#?]+)/([^/\s#?]+)")


def async_is_available(hass: HomeAssistant) -> bool:
    """Return whether this installation has a Supervisor at all."""
    return is_hassio(hass)


def async_installed_apps(hass: HomeAssistant) -> list[RepositoryInfo] | None:
    """Return every installed app, or None when there is no Supervisor."""
    if not is_hassio(hass):
        return None

    addons = _addons(hass)
    if addons is None:
        _LOGGER.debug("The Supervisor has not reported its apps yet")
        return None

    sources = _repository_sources(hass)
    now = dt_util.utcnow().isoformat()
    result: list[RepositoryInfo] = []
    for addon in addons:
        info = _build(addon, sources, now)
        if info is not None:
            result.append(info)
    _LOGGER.debug("The Supervisor reports %s installed apps", len(result))
    return result


def _addons(hass: HomeAssistant) -> list[dict[str, Any]] | None:
    """Return the installed apps as plain dictionaries.

    The detailed view carries the boot setting, which decides whether a stopped
    app is a problem or simply not in use. If it is not there yet, the short
    list still answers everything else.
    """
    from homeassistant.components.hassio import (
        HassioNotReadyError,
        get_addons_info,
        get_addons_list,
    )

    try:
        detailed = get_addons_info(hass)
    except (HassioNotReadyError, KeyError):
        detailed = None
    except Exception:
        _LOGGER.debug("Could not read the detailed app list", exc_info=True)
        detailed = None
    if detailed:
        return [
            {**info, "slug": slug}
            for slug, info in detailed.items()
            if info is not None
        ]

    try:
        return list(get_addons_list(hass))
    except (HassioNotReadyError, KeyError):
        return None
    except Exception:
        _LOGGER.debug("Could not read the app list", exc_info=True)
        return None


def _repository_sources(hass: HomeAssistant) -> dict[str, str]:
    """Return the source URL of every app store repository, by slug."""
    from homeassistant.components.hassio import (
        HassioNotReadyError,
        get_store,
    )

    try:
        store = get_store(hass)
    except (HassioNotReadyError, KeyError):
        return {}
    except Exception:
        _LOGGER.debug("Could not read the app store repositories", exc_info=True)
        return {}

    sources: dict[str, str] = {}
    for repository in store.get("repositories") or []:
        if not isinstance(repository, dict):
            continue
        slug = str(repository.get("slug") or "")
        source = str(repository.get("source") or repository.get("url") or "")
        if slug and source:
            sources[slug] = source
    return sources


def _build(
    addon: dict[str, Any], sources: dict[str, str], now: str
) -> RepositoryInfo | None:
    """Convert one app into our own facts object."""
    slug = str(addon.get("slug") or "")
    if not slug:
        return None

    repository_slug = str(addon.get("repository") or "")
    # The store repository is what actually delivers updates; the app's own
    # url is only a fallback when the repository has no usable source.
    full_name = _github_name(sources.get(repository_slug, "")) or _github_name(
        str(addon.get("url") or "")
    )

    return RepositoryInfo(
        full_name=full_name,
        category=Category.APP,
        name=str(addon.get("name") or slug),
        description=str(addon.get("description") or ""),
        slug=slug,
        app_repository=repository_slug,
        app_state=_as_str(addon.get("state")),
        app_stage=_as_str(addon.get("stage")),
        app_boot=_as_str(addon.get("boot")),
        detached=_as_bool(addon.get("detached")),
        available=_as_bool(addon.get("available")),
        installed_version=str(addon.get("version") or ""),
        available_version=str(addon.get("version_latest") or ""),
        pending_update=bool(addon.get("update_available")),
        min_ha_version=_as_str(addon.get("homeassistant")),
        # Apps are not distributed as GitHub releases, so the release rules do
        # not apply to them; see health/rules.py.
        has_releases=False,
        is_default_store=not addon.get("detached"),
        data_sources={"supervisor": now},
    )


def _github_name(url: str) -> str:
    """Return "owner/repo" when a URL points at GitHub, else an empty string."""
    if not url:
        return ""
    match = GITHUB_URL.search(url.strip())
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"


def _as_str(value: Any) -> str | None:
    """Return a plain string, unwrapping the Supervisor's enums."""
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _as_bool(value: Any) -> bool | None:
    """Return a plain bool, or None when the Supervisor said nothing."""
    return None if value is None else bool(value)
