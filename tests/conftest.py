"""Shared fixtures. The modules under test need no Home Assistant instance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.integrationguard.health.rules import default_rules
from custom_components.integrationguard.models import (
    Config,
    RepositoryInfo,
    Severity,
)
from custom_components.integrationguard.store import DEFAULT_SEVERITIES

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


@pytest.fixture
def config() -> Config:
    """Return a configuration with the shipped defaults."""
    return Config(
        severities=[Severity.from_dict(dict(s)) for s in DEFAULT_SEVERITIES],
        rules=default_rules(),
    )


@pytest.fixture
def info() -> RepositoryInfo:
    """Return a healthy repository nothing should fire on."""
    return RepositoryInfo(
        full_name="someone/something",
        category="integration",
        name="Something",
        installed_version="1.0.0",
        available_version="1.0.0",
        has_releases=True,
        last_version="1.0.0",
        last_push=NOW - timedelta(days=3),
        last_release_at=NOW - timedelta(days=10),
        stars=100,
        open_issues=2,
        archived=False,
        gone=False,
        data_sources={"hacs": NOW.isoformat(), "github": NOW.isoformat()},
    )
