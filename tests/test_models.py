"""Storage round-trips and the tolerance the stores rely on."""

from __future__ import annotations

from custom_components.integrationguard.const import Status, Usage
from custom_components.integrationguard.models import (
    Config,
    Ignore,
    RepositoryHealth,
    RepositoryInfo,
    Rule,
    Settings,
)


def test_config_survives_a_round_trip(config):
    restored = Config.from_dict(config.to_dict())
    assert restored.to_dict() == config.to_dict()


def test_unknown_keys_are_dropped():
    """A store written by a newer version must still load."""
    rule = Rule.from_dict({"id": "push_age", "threshold": 5, "invented_later": True})
    assert rule.id == "push_age"
    assert rule.threshold == 5


def test_settings_defaults_are_complete():
    settings = Settings.from_dict({})
    assert settings.monitoring_enabled is True
    assert "integration" in settings.categories_health


def test_lookup_helpers(config):
    config.ignored = [Ignore(key="a/b")]
    assert config.rule("push_age") is not None
    assert config.rule("nope") is None
    assert config.severity("critical") is not None
    assert config.ignore("a/b") is not None
    assert config.ignore("c/d") is None


def test_scan_result_ignores_the_ignored():
    from datetime import UTC, datetime

    from custom_components.integrationguard.models import ScanResult

    def repo(name: str, status: str, ignored: bool = False) -> RepositoryHealth:
        return RepositoryHealth(
            info=RepositoryInfo(full_name=name, category="integration"),
            status=status,
            ignored=ignored,
            usage=Usage.UNUSED,
        )

    now = datetime(2026, 8, 29, tzinfo=UTC)
    result = ScanResult(
        started=now,
        finished=now,
        repositories=[
            repo("a/ok", Status.HEALTHY),
            repo("b/stale", Status.STALE),
            repo("c/hidden", Status.ABANDONED, ignored=True),
        ],
    )
    assert [r.full_name for r in result.problems()] == ["b/stale"]
    assert [r.full_name for r in result.by_status(Status.ABANDONED)] == []
    assert [r.full_name for r in result.unused()] == ["a/ok", "b/stale"]
