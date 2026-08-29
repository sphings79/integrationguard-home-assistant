"""Decides whether a template or a python_script is referenced anywhere.

Both are addressed by name from configuration and automations, so a text search
over the configuration is the honest answer: it finds every mention, including
the ones inside templates.
"""

from __future__ import annotations

import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

# Where a reference could plausibly live. The database, downloaded code and the
# web root are deliberately left out.
SEARCH_GLOBS = ("*.yaml", "*.yml", "packages/**/*.yaml", "packages/**/*.yml")
SEARCH_STORAGE = ("lovelace*", "automation*", "script*", "template*")
SKIP_DIRS = {
    "custom_components",
    "deps",
    "www",
    "themes",
    "tts",
    "blueprints",
    "python_scripts",
    "custom_templates",
    ".cloud",
    ".storage",
}
MAX_FILE_BYTES = 5 * 1024 * 1024


def read_corpus(config_dir: Path) -> str:
    """Return everything a reference could hide in, as one blob of text.

    Runs in the executor: this reads files.
    """
    parts: list[str] = []
    for pattern in SEARCH_GLOBS:
        for path in sorted(config_dir.glob(pattern)):
            if _skip(path, config_dir):
                continue
            parts.append(_read(path))
    storage = config_dir / ".storage"
    if storage.is_dir():
        for pattern in SEARCH_STORAGE:
            for path in sorted(storage.glob(pattern)):
                parts.append(_read(path))
    return "\n".join(parts)


def _skip(path: Path, config_dir: Path) -> bool:
    """Return whether a path lies somewhere not worth searching."""
    try:
        relative = path.relative_to(config_dir)
    except ValueError:
        return True
    return bool(set(relative.parts[:-1]) & SKIP_DIRS)


def _read(path: Path) -> str:
    """Read one file, skipping anything too large or unreadable."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as err:
        _LOGGER.debug("Cannot read %s: %s", path, err)
        return ""


def installed_names(directory: Path, suffixes: tuple[str, ...]) -> list[str]:
    """Return the file names a repository installed into a directory."""
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir() if path.suffix in suffixes)
