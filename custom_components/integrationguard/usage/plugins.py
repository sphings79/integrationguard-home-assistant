"""Decides whether a Lovelace plugin is used by any dashboard.

Two halves: which custom element types a plugin brings, taken out of the
installed bundle, and which types the dashboards ask for. What cannot be read
out of a bundle never becomes "unused" — it becomes "undetermined", which is
what keeps libraries like card-mod or kiosk-mode out of the results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Any

from homeassistant.components.lovelace.const import (
    LOVELACE_DATA,
    MODE_AUTO,
    ConfigNotFound,
)
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# A custom element name always contains a dash; that is a web component rule.
TAG = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+"

DEFINE_PATTERNS = (
    re.compile(rf"customElements\s*\.\s*define\s*\(\s*[\"'`]({TAG})[\"'`]"),
    re.compile(rf"@customElement\s*\(\s*[\"'`]({TAG})[\"'`]"),
)
# Registries a plugin announces itself in so the card picker finds it.
REGISTRY_NAMES = re.compile(
    r"custom(?:Cards|Badges|CardFeatures|Rows|ViewLayouts|ElementFeatures)"
)
TYPE_IN_REGISTRY = re.compile(rf"type\s*:\s*[\"'`]({TAG})[\"'`]")
# How far after a registry mention we still look for the type it registers.
REGISTRY_WINDOW = 3000

USED_TYPE = re.compile(rf"custom:({TAG})")
# Keys of the dashboard configuration, for plugins used through one.
USED_KEY = re.compile(r'"(\w+)"\s*:')

MAX_BUNDLE_BYTES = 8 * 1024 * 1024


@dataclass(slots=True)
class PluginFiles:
    """What a plugin installed, what it registers and what it answers to."""

    directory: Path | None = None
    files: list[str] = field(default_factory=list)
    defined: set[str] = field(default_factory=set)
    registered: set[str] = field(default_factory=set)
    # Types actually used on a dashboard whose name occurs in this bundle.
    matched: set[str] = field(default_factory=set)

    @property
    def types(self) -> set[str]:
        """Return every type that could be read out of the bundle."""
        return self.defined | self.registered


@dataclass(slots=True)
class DashboardUsage:
    """Which custom types the dashboards use, and what could not be read."""

    types: dict[str, set[str]] = field(default_factory=dict)
    # Every key that appears anywhere in a dashboard. Some plugins are not
    # addressed as a card at all but through a key of their own — card-mod is
    # switched on by writing "card_mod:" under a card.
    keys: set[str] = field(default_factory=set)
    # Dashboard -> why its contents cannot be known ("unreadable", "strategy").
    uncertain: dict[str, str] = field(default_factory=dict)

    @property
    def all_types(self) -> set[str]:
        """Return every custom type used anywhere."""
        return {name for names in self.types.values() for name in names}

    def dashboards_using(self, types: set[str]) -> list[str]:
        """Return the dashboards that use any of the given types."""
        return sorted(
            dashboard for dashboard, used in self.types.items() if used & types
        )


def read_plugin_files(
    community_dir: Path, full_name: str, used_types: set[str]
) -> PluginFiles:
    """Read one plugin's bundles and work out what it answers to.

    Two directions, because neither alone is reliable:

    * forwards, by pulling element names out of the bundle. Good enough for
      most cards, but a plugin that registers through a helper hides them —
      Mushroom builds its card list from variables, so only a single badge name
      survives a regular expression.
    * backwards, by looking for the names the dashboards actually ask for. A
      card that a dashboard addresses must carry its own name as a string
      somewhere in the bundle, whatever it does with it afterwards.

    Runs in the executor: this touches the disk.
    """
    result = PluginFiles()
    directory = _plugin_directory(community_dir, full_name)
    if directory is None:
        return result
    result.directory = directory
    needles = {
        used: (f'"{used}"', f"'{used}'", f"`{used}`", f"custom:{used}")
        for used in used_types
    }

    for path in sorted(directory.rglob("*.js")):
        try:
            if path.stat().st_size > MAX_BUNDLE_BYTES:
                _LOGGER.debug("Skipping %s, it is too large to scan", path)
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as err:
            _LOGGER.debug("Cannot read %s: %s", path, err)
            continue
        result.files.append(path.name)
        for pattern in DEFINE_PATTERNS:
            result.defined.update(pattern.findall(content))
        result.registered.update(_registered_types(content))
        for used, variants in needles.items():
            if used not in result.matched and any(v in content for v in variants):
                result.matched.add(used)
    return result


def _plugin_directory(community_dir: Path, full_name: str) -> Path | None:
    """Return where HACS put a plugin, tolerating a different spelling."""
    wanted = full_name.split("/")[-1]
    candidate = community_dir / wanted
    if candidate.is_dir():
        return candidate
    if not community_dir.is_dir():
        return None
    lowered = wanted.lower()
    for entry in community_dir.iterdir():
        if entry.is_dir() and entry.name.lower() == lowered:
            return entry
    return None


def _registered_types(content: str) -> set[str]:
    """Return the types a bundle announces to the card picker.

    Minified code keeps the strings, so looking at a window after every mention
    of one of the registries finds them without parsing JavaScript.
    """
    found: set[str] = set()
    for match in REGISTRY_NAMES.finditer(content):
        window = content[match.end() : match.end() + REGISTRY_WINDOW]
        found.update(TYPE_IN_REGISTRY.findall(window))
    return found


async def async_read_dashboards(hass: HomeAssistant) -> DashboardUsage:
    """Collect every ``custom:`` type used across all dashboards.

    The whole configuration is searched as text rather than walked key by key,
    so a type mentioned inside a card_mod block or a markdown template counts
    too.
    """
    usage = DashboardUsage()
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.debug("Lovelace is not set up, no dashboard can be read")
        return usage

    for url_path, dashboard in lovelace.dashboards.items():
        name = url_path or "lovelace"
        if _mode(dashboard) == MODE_AUTO:
            # Home Assistant builds this one from the entity registry. It never
            # contains a custom card, so it is not a source of uncertainty.
            continue
        try:
            config = await dashboard.async_load(False)
        except ConfigNotFound:
            usage.uncertain[name] = "unreadable"
            continue
        except Exception:
            _LOGGER.warning("Could not read dashboard %s", name, exc_info=True)
            usage.uncertain[name] = "unreadable"
            continue
        usage.types[name] = set(USED_TYPE.findall(_as_text(config)))
        if _uses_strategy(config):
            # A strategy decides at render time what to show, so what is not in
            # the stored configuration may still end up on screen.
            usage.uncertain[name] = "strategy"
    return usage


def _mode(dashboard: Any) -> str:
    """Return a dashboard's mode without ever raising."""
    try:
        return str(dashboard.mode)
    except Exception:
        _LOGGER.debug("Could not read the dashboard mode", exc_info=True)
        return ""


def _uses_strategy(config: Any) -> bool:
    """Return whether a dashboard or one of its views is built by a strategy."""
    if not isinstance(config, dict):
        return False
    if "strategy" in config:
        return True
    views = config.get("views")
    if not isinstance(views, list):
        return False
    return any(isinstance(view, dict) and "strategy" in view for view in views)


def _as_text(config: Any) -> str:
    """Return a dashboard configuration as searchable text.

    Only the strings inside matter, so anything unserialisable may be coerced.
    """
    try:
        return json.dumps(config, default=str)
    except (TypeError, ValueError):
        return str(config)


def resource_urls(hass: HomeAssistant) -> list[str]:
    """Return every registered Lovelace resource URL."""
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or lovelace.resources is None:
        return []
    try:
        return [str(item.get("url", "")) for item in lovelace.resources.async_items()]
    except Exception:
        _LOGGER.debug("Could not read the Lovelace resources", exc_info=True)
        return []


def is_registered(urls: list[str], directory: Path | None) -> bool:
    """Return whether any resource points into a plugin's directory."""
    if directory is None:
        return False
    name = directory.name.lower()
    needles = (f"/hacsfiles/{name}/", f"/local/community/{name}/")
    return any(any(needle in url.lower() for needle in needles) for url in urls)


__all__ = [
    "DashboardUsage",
    "PluginFiles",
    "async_read_dashboards",
    "is_registered",
    "read_plugin_files",
    "resource_urls",
]
