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


def test_the_scan_result_survives_a_restart():
    """Everything reads from the last result, so losing it empties the panel."""
    from datetime import UTC, datetime, timedelta

    from custom_components.integrationguard.models import (
        Finding,
        RepositoryHealth,
        RepositoryInfo,
        ScanResult,
    )

    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    info = RepositoryInfo(
        full_name="someone/thing",
        category="plugin",
        name="Thing",
        last_push=now - timedelta(days=400),
        last_release_at=now - timedelta(days=30),
        stars=12,
        topics=["a", "b"],
        data_sources={"hacs": now.isoformat()},
    )
    result = ScanResult(
        started=now,
        finished=now + timedelta(seconds=3),
        repositories=[
            RepositoryHealth(
                info=info,
                findings=[Finding("push_age", "warning", 20, {"days": 400})],
                score=80,
                status=Status.STALE,
                usage=Usage.UNUSED,
                usage_confidence="high",
                usage_detail={"types": ["thing-card"]},
            )
        ],
        orphans=[{"kind": "dead_resource", "url": "/hacsfiles/x/y.js"}],
        source_errors={"hacs": "unavailable"},
        github_remaining=42,
    )

    restored = ScanResult.from_state(result.to_state())
    assert restored is not None
    assert restored.to_state() == result.to_state()
    # The values everything downstream reads must come back intact.
    item = restored.repositories[0]
    assert item.key == "someone/thing"
    assert item.info.last_push == info.last_push
    assert item.info.url == "https://github.com/someone/thing"
    assert item.findings[0].params == {"days": 400}
    assert restored.problems()[0].status == Status.STALE
    assert restored.github_remaining == 42


def test_a_missing_or_broken_result_restores_as_nothing():
    from custom_components.integrationguard.models import ScanResult

    assert ScanResult.from_state(None) is None
    assert ScanResult.from_state({}) is None
    assert ScanResult.from_state({"finished": "not a date", "started": "x"}) is None
