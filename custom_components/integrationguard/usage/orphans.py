"""Finds leftovers: files and resources that belong to nothing any more."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Resource URL prefixes and where they point on disk.
URL_PREFIXES = (("/hacsfiles/", "www/community"), ("/local/", "www"))


def find(
    config_dir: Path,
    resource_urls: list[str],
    known_plugin_dirs: set[str],
    known_domains: set[str],
) -> list[dict[str, Any]]:
    """Return everything left behind, with a reason each.

    Runs in the executor: this reads directories.
    """
    found: list[dict[str, Any]] = []
    found.extend(_dead_resources(config_dir, resource_urls))
    found.extend(
        _unknown_directories(
            config_dir / "www" / "community", known_plugin_dirs, "unknown_plugin_dir"
        )
    )
    found.extend(
        _unknown_directories(
            config_dir / "custom_components", known_domains, "unknown_custom_component"
        )
    )
    return found


def _dead_resources(config_dir: Path, urls: list[str]) -> list[dict[str, Any]]:
    """Return Lovelace resources whose file does not exist."""
    result: list[dict[str, Any]] = []
    for url in urls:
        path = _resource_path(config_dir, url)
        if path is None or path.exists():
            continue
        result.append({"kind": "dead_resource", "url": url, "path": str(path)})
    return result


def _resource_path(config_dir: Path, url: str) -> Path | None:
    """Translate a resource URL into the file it should serve."""
    clean = url.split("?", 1)[0]
    for prefix, base in URL_PREFIXES:
        if not clean.startswith(prefix):
            continue
        relative = clean[len(prefix) :]
        if base == "www" and relative.startswith("community/"):
            # Already covered by the /hacsfiles/ prefix.
            return config_dir / "www" / relative
        return config_dir / base / relative
    return None


def _unknown_directories(
    parent: Path, known: set[str], kind: str
) -> list[dict[str, Any]]:
    """Return directories nothing claims."""
    if not parent.is_dir():
        return []
    lowered = {name.lower() for name in known}
    result: list[dict[str, Any]] = []
    for entry in sorted(parent.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name.lower() in lowered:
            continue
        result.append({"kind": kind, "name": entry.name, "path": str(entry)})
    return result
