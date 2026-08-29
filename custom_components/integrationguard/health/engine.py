"""Turns the facts about a repository into findings, a score and a status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from awesomeversion import AwesomeVersion, AwesomeVersionException

from ..const import STATUS_ORDER, AppStage, RuleId, Status, Usage, status_for_priority
from ..models import Config, Finding, RepositoryInfo, Rule
from .rules import RULE_DEFINITIONS, RuleDefinition

_LOGGER = logging.getLogger(__name__)

# Fallback when a rule points at a severity the user has deleted.
FALLBACK_PRIORITY = 50


@dataclass(frozen=True, slots=True)
class Context:
    """Everything a check needs beyond the repository itself."""

    now: datetime
    ha_version: str
    usage: str = Usage.NOT_CHECKED


type Check = Callable[[RepositoryInfo, Rule, Context], dict[str, Any] | None]


def _age_days(value: datetime | None, now: datetime) -> int | None:
    """Return how many days ago a timestamp lies, or None if unknown."""
    if value is None:
        return None
    return max(0, int((now - value).total_seconds() // 86400))


def _push_age(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the last push is older than the threshold."""
    days = _age_days(info.last_push, ctx.now)
    if days is None or rule.threshold is None or days < rule.threshold:
        return None
    return {"days": days, "threshold": int(rule.threshold)}


def _release_age(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the newest release is older than the threshold.

    A repository without any release is covered by ``no_release`` instead, so a
    missing date never counts as an infinitely old release.
    """
    days = _age_days(info.last_release_at, ctx.now)
    if days is None or rule.threshold is None or days < rule.threshold:
        return None
    return {
        "days": days,
        "threshold": int(rule.threshold),
        "version": info.last_version or "",
    }


def _ha_version(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the repository asks for a newer Home Assistant than we run."""
    if not info.min_ha_version or not ctx.ha_version:
        return None
    try:
        if AwesomeVersion(info.min_ha_version) <= AwesomeVersion(ctx.ha_version):
            return None
    except AwesomeVersionException:
        _LOGGER.debug(
            "Cannot compare %s against Home Assistant %s for %s",
            info.min_ha_version,
            ctx.ha_version,
            info.full_name,
        )
        return None
    return {"required": info.min_ha_version, "installed": ctx.ha_version}


def _unpinned(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the download follows a branch instead of a release."""
    if info.selected_tag and info.selected_tag == info.default_branch:
        return {"branch": info.selected_tag}
    if not info.has_releases and info.installed_commit:
        return {"commit": info.installed_commit}
    return None


def _many_issues(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the repository has more open issues than the threshold."""
    if info.open_issues is None or rule.threshold is None:
        return None
    if info.open_issues <= rule.threshold:
        return None
    return {"count": info.open_issues, "threshold": int(rule.threshold)}


def _few_stars(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when hardly anybody has starred the repository."""
    if info.stars is None or rule.threshold is None:
        return None
    if info.stars >= rule.threshold:
        return None
    return {"count": info.stars, "threshold": int(rule.threshold)}


def _no_release(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the repository never published a release."""
    return None if info.has_releases else {}


def _prerelease_only(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the only published versions are prereleases."""
    if info.last_version or not info.prerelease:
        return None
    return {"version": info.prerelease}


def _outdated(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when a newer version than the installed one is available."""
    if not info.pending_update:
        return None
    return {"installed": info.installed_version, "available": info.available_version}


def _unused(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the usage engine found nothing that uses this."""
    return {"category": info.category} if ctx.usage == Usage.UNUSED else None


def _app_deprecated(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the author declared the app deprecated."""
    if info.app_stage != AppStage.DEPRECATED:
        return None
    return {"stage": info.app_stage}


def _app_unavailable(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
    """Fire when the Supervisor cannot offer the app any more."""
    return {} if info.available is False else None


def _flag(attribute: str) -> Check:
    """Build a check that fires when a boolean attribute is exactly True."""

    def check(info: RepositoryInfo, rule: Rule, ctx: Context) -> dict | None:
        return {} if getattr(info, attribute) is True else None

    return check


CHECKS: dict[str, Check] = {
    RuleId.CRITICAL_LIST: _flag("critical"),
    RuleId.GONE: _flag("gone"),
    RuleId.ARCHIVED: _flag("archived"),
    RuleId.REMOVED: _flag("removed_from_hacs"),
    RuleId.PUSH_AGE: _push_age,
    RuleId.PUSH_AGE_SEVERE: _push_age,
    RuleId.RELEASE_AGE: _release_age,
    RuleId.RELEASE_AGE_SEVERE: _release_age,
    RuleId.HA_VERSION: _ha_version,
    RuleId.MANY_ISSUES: _many_issues,
    RuleId.FEW_STARS: _few_stars,
    RuleId.NO_RELEASE: _no_release,
    RuleId.PRERELEASE_ONLY: _prerelease_only,
    RuleId.OUTDATED: _outdated,
    RuleId.UNPINNED: _unpinned,
    RuleId.UNUSED: _unused,
    RuleId.APP_DETACHED: _flag("detached"),
    RuleId.APP_DEPRECATED: _app_deprecated,
    RuleId.APP_UNAVAILABLE: _app_unavailable,
}


def _priority(config: Config, severity_id: str) -> int:
    """Return the priority of a severity, falling back when it is gone."""
    severity = config.severity(severity_id)
    if severity is None:
        _LOGGER.warning(
            "Rule points at unknown severity %s, treating it as a warning",
            severity_id,
        )
        return FALLBACK_PRIORITY
    return severity.priority


def _applicable(definition: RuleDefinition, info: RepositoryInfo) -> bool:
    """Return whether a rule can be judged with the data we have.

    Rules that need the GitHub API stay silent until an answer arrived, rather
    than firing on data that is merely missing.
    """
    if not definition.requires_github:
        return True
    return "github" in info.data_sources


def evaluate(
    info: RepositoryInfo,
    config: Config,
    *,
    now: datetime,
    ha_version: str,
    usage: str = Usage.NOT_CHECKED,
) -> tuple[list[Finding], int, str]:
    """Return the findings, score and status for one repository."""
    context = Context(now=now, ha_version=ha_version, usage=usage)
    findings: list[Finding] = []
    superseded: set[str] = set()

    for definition in RULE_DEFINITIONS:
        rule_id = str(definition.id)
        rule = config.rule(rule_id)
        if rule is None or not rule.enabled or rule_id in superseded:
            continue
        if not definition.applies_to(info.category):
            continue
        if not _applicable(definition, info):
            continue
        check = CHECKS.get(rule_id)
        if check is None:
            continue
        params = check(info, rule, context)
        if params is None:
            continue
        findings.append(
            Finding(
                rule_id=rule_id,
                severity_id=rule.severity_id,
                penalty=rule.penalty,
                params=params,
            )
        )
        if definition.supersedes is not None:
            superseded.add(str(definition.supersedes))

    score = max(0, 100 - sum(f.penalty for f in findings))
    status = Status.HEALTHY
    for finding in findings:
        candidate = status_for_priority(_priority(config, finding.severity_id))
        if STATUS_ORDER.index(candidate) > STATUS_ORDER.index(status):
            status = candidate
    return findings, score, status
