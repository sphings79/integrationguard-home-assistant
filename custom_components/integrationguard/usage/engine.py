"""Brings the category specific checks together into one verdict per repository."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import AppState, Category, Confidence, Usage
from ..models import Config, RepositoryInfo
from . import files, integrations, orphans, plugins, themes

_LOGGER = logging.getLogger(__name__)

TEMPLATE_DIR = "custom_templates"
PYTHON_SCRIPT_DIR = "python_scripts"
THEMES_DIR = "themes"
COMMUNITY_DIR = "www/community"


@dataclass(frozen=True, slots=True)
class UsageResult:
    """What the engine concluded about one repository."""

    usage: str = Usage.NOT_CHECKED
    confidence: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _DiskPass:
    """Everything one trip to the disk brought back."""

    plugin_files: dict[str, plugins.PluginFiles] = field(default_factory=dict)
    theme_names: dict[str, set[str]] = field(default_factory=dict)
    selected_themes: set[str] = field(default_factory=set)
    themes_readable: bool = False
    corpus: str = ""
    orphans: list[dict[str, Any]] = field(default_factory=list)


async def async_evaluate(
    hass: HomeAssistant, infos: list[RepositoryInfo], config: Config
) -> tuple[dict[str, UsageResult], list[dict[str, Any]]]:
    """Return a verdict per repository plus the list of leftovers."""
    settings = config.settings
    wanted = set(settings.categories_usage)
    config_dir = Path(hass.config.config_dir)

    dashboards = plugins.DashboardUsage()
    if Category.PLUGIN in wanted:
        dashboards = await plugins.async_read_dashboards(hass)
    urls = plugins.resource_urls(hass)

    disk = await hass.async_add_executor_job(
        _disk_pass,
        config_dir,
        infos,
        wanted,
        urls,
        settings.check_orphans,
        dashboards.all_types,
    )
    if Category.THEME in wanted:
        # The configured default themes count as chosen, same as a user's pick.
        disk.selected_themes |= themes.defaults(hass)

    required = (
        integrations.required_domains(hass) if Category.INTEGRATION in wanted else set()
    )
    marked = set(config.marked_used)

    results: dict[str, UsageResult] = {}
    for info in infos:
        if info.category not in wanted:
            results[info.key] = UsageResult()
            continue
        if info.key in marked:
            results[info.key] = UsageResult(
                Usage.USED, Confidence.HIGH, {"marked_by_user": True}
            )
            continue
        results[info.key] = _evaluate_one(hass, info, disk, dashboards, urls, required)
    return results, disk.orphans


def _evaluate_one(
    hass: HomeAssistant,
    info: RepositoryInfo,
    disk: _DiskPass,
    dashboards: plugins.DashboardUsage,
    urls: list[str],
    required: set[str],
) -> UsageResult:
    """Return the verdict for one repository."""
    match info.category:
        case Category.PLUGIN:
            return _evaluate_plugin(info, disk, dashboards, urls)
        case Category.INTEGRATION:
            if not info.domain:
                return UsageResult(Usage.UNDETERMINED, Confidence.LOW, {})
            usage, confidence, detail = integrations.evaluate(
                hass, info.domain, required
            )
            return UsageResult(usage, confidence, detail)
        case Category.THEME:
            return _evaluate_theme(info, disk)
        case Category.TEMPLATE:
            return _evaluate_file(info, disk, _template_needles(info))
        case Category.PYTHON_SCRIPT:
            return _evaluate_file(info, disk, _python_script_needles(info))
        case Category.APP:
            return _evaluate_app(info)
        case _:
            return UsageResult()


def _evaluate_plugin(
    info: RepositoryInfo,
    disk: _DiskPass,
    dashboards: plugins.DashboardUsage,
    urls: list[str],
) -> UsageResult:
    """Judge a Lovelace plugin against the dashboards."""
    found = disk.plugin_files.get(info.full_name, plugins.PluginFiles())
    detail: dict[str, Any] = {
        "types": sorted(found.types),
        "registered_types": sorted(found.registered),
        "files": found.files,
        "uncertain_dashboards": dashboards.uncertain,
    }

    if not plugins.is_registered(urls, found.directory):
        # The bundle is on disk but no dashboard could ever load it.
        return UsageResult(Usage.NOT_REGISTERED, Confidence.HIGH, detail)

    in_use = found.matched | (found.types & dashboards.all_types)
    if in_use:
        detail["used_types"] = sorted(in_use)
        detail["dashboards"] = dashboards.dashboards_using(in_use)
        return UsageResult(Usage.USED, Confidence.HIGH, detail)

    if not found.types:
        # Nothing addressable came out of the bundle. Card-mod, kiosk-mode and
        # the icon sets land here — they are used through other means, and
        # guessing would be worse than saying nothing.
        return UsageResult(Usage.UNDETERMINED, Confidence.LOW, detail)

    confidence = Confidence.HIGH if found.registered else Confidence.MEDIUM
    if dashboards.uncertain:
        # A strategy decides at render time; the card may well appear there.
        confidence = Confidence.MEDIUM if found.registered else Confidence.LOW
    return UsageResult(Usage.UNUSED, confidence, detail)


def _evaluate_app(info: RepositoryInfo) -> UsageResult:
    """Judge an app by whether it runs and whether it is meant to."""
    detail: dict[str, Any] = {"state": info.app_state, "boot": info.app_boot}
    if info.app_state in (AppState.STARTED, AppState.STARTUP):
        return UsageResult(Usage.USED, Confidence.HIGH, detail)
    # Everything else says nothing about whether anyone wants the app. A
    # stopped app that does not boot may simply be started on demand, and the
    # Supervisor does not say whether it ever ran. Stopped although it should
    # boot is a runtime question, not a usage one.
    return UsageResult(Usage.UNDETERMINED, Confidence.LOW, detail)


def _evaluate_theme(info: RepositoryInfo, disk: _DiskPass) -> UsageResult:
    """Judge a theme against the default and the per-user choices."""
    names = disk.theme_names.get(info.full_name, set())
    detail: dict[str, Any] = {"themes": sorted(names)}
    if not names:
        return UsageResult(Usage.UNDETERMINED, Confidence.LOW, detail)
    selected = names & disk.selected_themes
    if selected:
        detail["selected"] = sorted(selected)
        return UsageResult(Usage.USED, Confidence.HIGH, detail)
    if not disk.themes_readable:
        # Without the per-user files there is no way to know.
        detail["user_preferences_readable"] = False
        return UsageResult(Usage.UNDETERMINED, Confidence.LOW, detail)
    return UsageResult(Usage.UNUSED, Confidence.MEDIUM, detail)


def _evaluate_file(
    info: RepositoryInfo, disk: _DiskPass, needles: list[str]
) -> UsageResult:
    """Judge a template or python_script by looking for its name."""
    detail: dict[str, Any] = {"looked_for": needles}
    if not needles:
        return UsageResult(Usage.UNDETERMINED, Confidence.LOW, detail)
    hits = [needle for needle in needles if needle in disk.corpus]
    if hits:
        detail["found"] = hits
        return UsageResult(Usage.USED, Confidence.HIGH, detail)
    return UsageResult(Usage.UNUSED, Confidence.MEDIUM, detail)


def _template_needles(info: RepositoryInfo) -> list[str]:
    """Return the strings a template would be referenced by."""
    if not info.file_name:
        return []
    return [info.file_name]


def _python_script_needles(info: RepositoryInfo) -> list[str]:
    """Return the strings a python_script would be called by."""
    if not info.file_name:
        return []
    return [f"python_script.{Path(info.file_name).stem}"]


def _disk_pass(
    config_dir: Path,
    infos: list[RepositoryInfo],
    wanted: set[str],
    urls: list[str],
    check_orphans: bool,
    used_types: set[str],
) -> _DiskPass:
    """Do every file system read of a scan in one go, off the event loop."""
    result = _DiskPass()
    community = config_dir / COMMUNITY_DIR

    if Category.PLUGIN in wanted:
        for info in infos:
            if info.category == Category.PLUGIN:
                result.plugin_files[info.full_name] = plugins.read_plugin_files(
                    community, info.full_name, used_types
                )

    if Category.THEME in wanted:
        themes_dir = config_dir / THEMES_DIR
        for info in infos:
            if info.category == Category.THEME:
                result.theme_names[info.full_name] = themes.theme_names(
                    themes_dir, info.full_name
                )
        result.selected_themes, result.themes_readable = themes.selected_themes(
            config_dir / ".storage"
        )

    if {Category.TEMPLATE, Category.PYTHON_SCRIPT} & wanted:
        result.corpus = files.read_corpus(config_dir)

    if check_orphans:
        known_dirs = {
            info.full_name.split("/")[-1]
            for info in infos
            if info.category == Category.PLUGIN
        }
        known_domains = {
            info.domain
            for info in infos
            if info.category == Category.INTEGRATION and info.domain
        }
        result.orphans = orphans.find(config_dir, urls, known_dirs, known_domains)
    return result
