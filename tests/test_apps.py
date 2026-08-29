"""Apps from the Supervisor: how they are read and how they are judged."""

from __future__ import annotations

from custom_components.integrationguard.const import Category, RuleId, Status, Usage
from custom_components.integrationguard.health.engine import evaluate
from custom_components.integrationguard.sources.apps import _build, _github_name
from custom_components.integrationguard.usage.engine import _evaluate_app

from .conftest import NOW

ADDON = {
    "slug": "45df7312_zigbee2mqtt",
    "name": "Zigbee2MQTT",
    "description": "Zigbee to MQTT bridge",
    "repository": "45df7312",
    "state": "started",
    "stage": "stable",
    "boot": "auto",
    "detached": False,
    "available": True,
    "version": "2.6.2",
    "version_latest": "2.6.2",
    "update_available": False,
    "homeassistant": "2025.9.0",
    "url": "https://github.com/zigbee2mqtt/hassio-zigbee2mqtt/tree/master/zigbee2mqtt",
}
SOURCES = {"45df7312": "https://github.com/zigbee2mqtt/hassio-zigbee2mqtt"}


def build(**overrides):
    """Return one app, with fields overridden as the test needs."""
    return _build({**ADDON, **overrides}, SOURCES, NOW.isoformat())


def run(info, config, usage=Usage.NOT_CHECKED):
    """Evaluate an app and return the fired rules, the score and the status."""
    findings, score, status = evaluate(
        info, config, now=NOW, ha_version="2026.8.3", usage=usage
    )
    return {f.rule_id for f in findings}, score, status


def test_github_name_is_taken_from_the_url():
    assert _github_name("https://github.com/foo/bar") == "foo/bar"
    assert _github_name("https://github.com/foo/bar.git") == "foo/bar"
    assert _github_name("https://github.com/foo/bar/") == "foo/bar"
    assert _github_name("git@github.com:foo/bar.git") == "foo/bar"
    assert _github_name("https://gitlab.com/foo/bar") == ""
    assert _github_name("") == ""


def test_the_store_repository_wins_over_the_app_url():
    """The store repository delivers the updates, so it is the one to watch."""
    info = build()
    assert info.full_name == "zigbee2mqtt/hassio-zigbee2mqtt"


def test_the_app_url_is_the_fallback():
    info = _build(ADDON, {}, NOW.isoformat())
    assert info.full_name == "zigbee2mqtt/hassio-zigbee2mqtt"


def test_apps_are_keyed_by_slug():
    """Several apps share one store repository, so the slug is the identity."""
    info = build()
    assert info.key == "app:45df7312_zigbee2mqtt"
    assert info.category == Category.APP
    assert info.hacs_url == "/hassio/addon/45df7312_zigbee2mqtt/info"


def test_fields_are_carried_over():
    info = build()
    assert info.installed_version == "2.6.2"
    assert info.min_ha_version == "2025.9.0"
    assert info.app_state == "started"
    assert info.app_boot == "auto"
    assert info.detached is False


def test_a_healthy_app_fires_nothing(config):
    """The release rules must stay out of the way; apps have no releases."""
    info = build()
    info.data_sources["github"] = NOW.isoformat()
    fired, score, status = run(info, config)
    assert fired == set()
    assert score == 100
    assert status == Status.HEALTHY


def test_detached_app_is_critical(config):
    info = build(detached=True)
    fired, score, status = run(info, config)
    assert fired == {RuleId.APP_DETACHED}
    assert score == 50
    assert status == Status.ABANDONED


def test_deprecated_app_is_critical(config):
    info = build(stage="deprecated")
    fired, _, status = run(info, config)
    assert fired == {RuleId.APP_DEPRECATED}
    assert status == Status.ABANDONED


def test_unavailable_app_is_a_warning(config):
    info = build(available=False)
    fired, _, status = run(info, config)
    assert fired == {RuleId.APP_UNAVAILABLE}
    assert status == Status.STALE


def test_an_outdated_app_is_noted(config):
    info = build(version="2.6.0", update_available=True)
    fired, _, _ = run(info, config)
    assert RuleId.OUTDATED in fired


def test_the_ha_version_rule_applies_to_apps_too(config):
    info = build(homeassistant="2027.1.0")
    fired, _, _ = run(info, config)
    assert RuleId.HA_VERSION in fired


def test_hacs_only_rules_never_fire_on_an_app(config):
    """An app is not distributed as a GitHub release, so these say nothing."""
    info = build()
    info.removed_from_hacs = True
    info.critical = True
    fired, score, _ = run(info, config)
    assert (
        not {
            RuleId.NO_RELEASE,
            RuleId.PRERELEASE_ONLY,
            RuleId.UNPINNED,
            RuleId.REMOVED,
            RuleId.CRITICAL_LIST,
        }
        & fired
    )
    assert score == 100


def test_a_running_app_is_used():
    result = _evaluate_app(build(state="started"))
    assert result.usage == Usage.USED


def test_a_stopped_app_that_never_boots_is_unused():
    result = _evaluate_app(build(state="stopped", boot="manual"))
    assert result.usage == Usage.UNUSED


def test_a_stopped_app_that_should_boot_is_a_runtime_matter():
    result = _evaluate_app(build(state="stopped", boot="auto"))
    assert result.usage == Usage.UNDETERMINED


def test_an_app_in_error_is_not_called_unused():
    result = _evaluate_app(build(state="error"))
    assert result.usage == Usage.UNDETERMINED
