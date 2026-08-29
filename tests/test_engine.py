"""The health engine: which rule fires when, and what it costs."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.integrationguard.const import RuleId, Status, Usage
from custom_components.integrationguard.health.engine import evaluate

from .conftest import NOW

HA_VERSION = "2026.8.3"


def run(info, config, usage=Usage.NOT_CHECKED):
    """Evaluate one repository and return the fired rule ids plus the rest."""
    findings, score, status = evaluate(
        info, config, now=NOW, ha_version=HA_VERSION, usage=usage
    )
    return {f.rule_id for f in findings}, score, status


def test_healthy_repository_fires_nothing(info, config):
    fired, score, status = run(info, config)
    assert fired == set()
    assert score == 100
    assert status == Status.HEALTHY


def test_push_age_fires_once_past_the_threshold(info, config):
    info.last_push = NOW - timedelta(days=181)
    fired, score, status = run(info, config)
    assert fired == {RuleId.PUSH_AGE}
    assert score == 80
    assert status == Status.STALE


def test_severe_push_age_supersedes_the_mild_one(info, config):
    info.last_push = NOW - timedelta(days=600)
    fired, score, status = run(info, config)
    assert fired == {RuleId.PUSH_AGE_SEVERE}
    assert score == 55
    assert status == Status.ABANDONED


def test_unknown_push_date_fires_nothing(info, config):
    info.last_push = None
    fired, _, _ = run(info, config)
    assert RuleId.PUSH_AGE not in fired


def test_release_age_needs_a_release_date(info, config):
    info.last_release_at = None
    fired, _, _ = run(info, config)
    assert RuleId.RELEASE_AGE not in fired


def test_release_age_fires_on_an_old_release(info, config):
    info.last_release_at = NOW - timedelta(days=400)
    fired, _, _ = run(info, config)
    assert fired == {RuleId.RELEASE_AGE}


def test_github_rules_stay_silent_without_a_github_answer(info, config):
    """Missing data must never be mistaken for a finding."""
    info.data_sources.pop("github")
    info.archived = True
    info.last_release_at = NOW - timedelta(days=900)
    fired, score, _ = run(info, config)
    assert fired == set()
    assert score == 100


def test_archived_is_critical(info, config):
    info.archived = True
    fired, score, status = run(info, config)
    assert fired == {RuleId.ARCHIVED}
    assert score == 50
    assert status == Status.ABANDONED


def test_gone_repository(info, config):
    info.gone = True
    fired, score, _ = run(info, config)
    assert fired == {RuleId.GONE}
    assert score == 40


def test_critical_list_wipes_the_score(info, config):
    info.critical = True
    fired, score, status = run(info, config)
    assert fired == {RuleId.CRITICAL_LIST}
    assert score == 0
    assert status == Status.CRITICAL


def test_removed_from_hacs(info, config):
    info.removed_from_hacs = True
    fired, _, status = run(info, config)
    assert fired == {RuleId.REMOVED}
    assert status == Status.ABANDONED


def test_no_release(info, config):
    info.has_releases = False
    fired, _, _ = run(info, config)
    assert RuleId.NO_RELEASE in fired


def test_prerelease_only(info, config):
    info.last_version = None
    info.prerelease = "v2.0.0b1"
    fired, _, _ = run(info, config)
    assert RuleId.PRERELEASE_ONLY in fired


def test_many_issues_and_few_stars(info, config):
    info.open_issues = 51
    info.stars = 4
    fired, _, _ = run(info, config)
    assert {RuleId.MANY_ISSUES, RuleId.FEW_STARS} <= fired


def test_thresholds_are_exclusive_at_the_edge(info, config):
    info.open_issues = 50
    info.stars = 5
    fired, _, _ = run(info, config)
    assert not {RuleId.MANY_ISSUES, RuleId.FEW_STARS} & fired


def test_ha_version_too_new(info, config):
    info.min_ha_version = "2027.1.0"
    fired, _, status = run(info, config)
    assert RuleId.HA_VERSION in fired
    assert status == Status.STALE


def test_ha_version_satisfied(info, config):
    info.min_ha_version = "2025.9.0"
    fired, _, _ = run(info, config)
    assert RuleId.HA_VERSION not in fired


def test_unreadable_version_is_not_a_finding(info, config):
    info.min_ha_version = "not a version"
    fired, _, _ = run(info, config)
    assert RuleId.HA_VERSION not in fired


def test_unpinned_branch_install(info, config):
    info.selected_tag = "main"
    info.default_branch = "main"
    fired, _, _ = run(info, config)
    assert RuleId.UNPINNED in fired


def test_unpinned_commit_install(info, config):
    info.has_releases = False
    info.installed_commit = "d3e4152"
    fired, _, _ = run(info, config)
    assert RuleId.UNPINNED in fired


def test_outdated(info, config):
    info.pending_update = True
    fired, _, _ = run(info, config)
    assert RuleId.OUTDATED in fired


def test_unused_only_fires_when_the_usage_engine_says_so(info, config):
    assert RuleId.UNUSED not in run(info, config, usage=Usage.NOT_CHECKED)[0]
    assert RuleId.UNUSED not in run(info, config, usage=Usage.UNDETERMINED)[0]
    assert RuleId.UNUSED in run(info, config, usage=Usage.UNUSED)[0]


def test_disabled_rule_never_fires(info, config):
    info.archived = True
    config.rule(RuleId.ARCHIVED).enabled = False
    fired, score, _ = run(info, config)
    assert fired == set()
    assert score == 100


def test_changed_threshold_is_respected(info, config):
    info.last_push = NOW - timedelta(days=40)
    config.rule(RuleId.PUSH_AGE).threshold = 30
    fired, _, _ = run(info, config)
    assert RuleId.PUSH_AGE in fired


def test_score_never_goes_below_zero(info, config):
    info.critical = True
    info.archived = True
    info.gone = True
    _, score, _ = run(info, config)
    assert score == 0


def test_status_follows_the_severity_priority(info, config):
    """Repointing a rule at another severity changes the resulting status."""
    info.open_issues = 500
    config.rule(RuleId.MANY_ISSUES).severity_id = "critical"
    _, _, status = run(info, config)
    assert status == Status.ABANDONED


@pytest.mark.parametrize("missing", ["stars", "open_issues"])
def test_missing_numbers_fire_nothing(info, config, missing):
    setattr(info, missing, None)
    fired, _, _ = run(info, config)
    assert not {RuleId.MANY_ISSUES, RuleId.FEW_STARS} & fired
