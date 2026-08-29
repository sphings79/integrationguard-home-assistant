"""Decides whether a theme installed through HACS is selected anywhere.

A theme is used when it is the default, the dark default, or when any user
picked it in their profile. The per-user choice lives in an internal storage
file; if it cannot be read, the answer stays "undetermined" rather than wrong.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DATA_THEMES = "frontend_themes"
DATA_DEFAULT_THEME = "frontend_default_theme"
DATA_DEFAULT_DARK_THEME = "frontend_default_dark_theme"
USER_DATA_GLOB = "frontend.user_data_*"


def selected_themes(storage_dir: Path) -> tuple[set[str], bool]:
    """Return the themes users picked, and whether the files could be read.

    Runs in the executor: this reads files.
    """
    chosen: set[str] = set()
    readable = False
    if not storage_dir.is_dir():
        return chosen, readable
    for path in sorted(storage_dir.glob(USER_DATA_GLOB)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            _LOGGER.debug("Cannot read %s: %s", path, err)
            continue
        readable = True
        themes = (payload.get("data") or {}).get("themes") or {}
        for key in ("theme", "dark_theme"):
            value = themes.get(key)
            if isinstance(value, str) and value:
                chosen.add(value)
    return chosen, readable


def theme_names(themes_dir: Path, full_name: str) -> set[str]:
    """Return the theme names one repository installed.

    The names are the top level keys of the installed YAML files, not the file
    names — a single file may define several themes.
    """
    names: set[str] = set()
    if not themes_dir.is_dir():
        return names
    wanted = full_name.split("/")[-1].lower()
    for path in sorted(themes_dir.rglob("*.yaml")):
        stem = path.stem.lower()
        if (
            wanted not in stem
            and stem not in wanted
            and wanted not in str(path.parent.name).lower()
        ):
            continue
        names.add(path.stem)
        names.update(_top_level_keys(path))
    return names


def _top_level_keys(path: Path) -> set[str]:
    """Return the top level keys of a YAML file without a YAML parser.

    Themes are shallow documents; reading the unindented keys is enough and
    avoids pulling a parser into the executor for every file.
    """
    keys: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line[0].isspace() or line.lstrip().startswith("#"):
                continue
            key, separator, _ = line.partition(":")
            if separator and key.strip():
                keys.add(key.strip().strip("\"'"))
    except OSError as err:
        _LOGGER.debug("Cannot read %s: %s", path, err)
    return keys


def defaults(hass: HomeAssistant) -> set[str]:
    """Return the themes configured as the light and dark default."""
    found: set[str] = set()
    for key in (DATA_DEFAULT_THEME, DATA_DEFAULT_DARK_THEME):
        value: Any = hass.data.get(key)
        if isinstance(value, str) and value and value != "default":
            found.add(value)
    return found
