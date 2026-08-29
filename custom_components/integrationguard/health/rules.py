"""The fixed catalogue of health rules.

Every rule owns exactly one threshold, one severity and one penalty. Rules that
come in two grades are two entries; the harsher one names the milder one in
``supersedes`` so only one of the pair ever fires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..const import HACS_CATEGORIES, Category, RuleId, SeverityId, ThresholdUnit
from ..models import Rule


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    """A rule as the code knows it, with the defaults a user may override."""

    id: RuleId
    severity_id: SeverityId
    penalty: int
    threshold: float | None = None
    threshold_unit: ThresholdUnit | None = None
    # True when the rule can only be decided with data from the GitHub API.
    requires_github: bool = False
    # The milder grade of the same rule, skipped when this one fires.
    supersedes: RuleId | None = None
    # Categories the rule applies to. None means all of them.
    categories: tuple[Category, ...] | None = None

    def applies_to(self, category: str) -> bool:
        """Return whether the rule says anything about this kind of thing."""
        return self.categories is None or category in self.categories


# Rules about releases and store listings only make sense for things HACS
# delivers; an app is versioned by its Supervisor repository instead.
HACS_ONLY: Final = HACS_CATEGORIES
APP_ONLY: Final = (Category.APP,)

RULE_DEFINITIONS: Final[tuple[RuleDefinition, ...]] = (
    RuleDefinition(
        RuleId.CRITICAL_LIST, SeverityId.SECURITY, penalty=100, categories=HACS_ONLY
    ),
    RuleDefinition(RuleId.GONE, SeverityId.CRITICAL, penalty=60, requires_github=True),
    RuleDefinition(
        RuleId.ARCHIVED, SeverityId.CRITICAL, penalty=50, requires_github=True
    ),
    RuleDefinition(
        RuleId.REMOVED, SeverityId.CRITICAL, penalty=50, categories=HACS_ONLY
    ),
    RuleDefinition(
        RuleId.APP_DETACHED, SeverityId.CRITICAL, penalty=50, categories=APP_ONLY
    ),
    RuleDefinition(
        RuleId.APP_DEPRECATED, SeverityId.CRITICAL, penalty=45, categories=APP_ONLY
    ),
    RuleDefinition(
        RuleId.APP_UNAVAILABLE, SeverityId.WARNING, penalty=20, categories=APP_ONLY
    ),
    RuleDefinition(
        RuleId.PUSH_AGE_SEVERE,
        SeverityId.CRITICAL,
        penalty=45,
        threshold=545,
        threshold_unit=ThresholdUnit.DAYS,
        supersedes=RuleId.PUSH_AGE,
    ),
    RuleDefinition(
        RuleId.PUSH_AGE,
        SeverityId.WARNING,
        penalty=20,
        threshold=180,
        threshold_unit=ThresholdUnit.DAYS,
    ),
    RuleDefinition(
        RuleId.RELEASE_AGE_SEVERE,
        SeverityId.WARNING,
        penalty=20,
        threshold=730,
        threshold_unit=ThresholdUnit.DAYS,
        requires_github=True,
        categories=HACS_ONLY,
        supersedes=RuleId.RELEASE_AGE,
    ),
    RuleDefinition(
        RuleId.RELEASE_AGE,
        SeverityId.INFO,
        penalty=10,
        threshold=365,
        threshold_unit=ThresholdUnit.DAYS,
        requires_github=True,
        categories=HACS_ONLY,
    ),
    RuleDefinition(RuleId.HA_VERSION, SeverityId.WARNING, penalty=15),
    RuleDefinition(RuleId.UNUSED, SeverityId.INFO, penalty=10),
    RuleDefinition(
        RuleId.MANY_ISSUES,
        SeverityId.INFO,
        penalty=5,
        threshold=50,
        threshold_unit=ThresholdUnit.COUNT,
    ),
    RuleDefinition(
        RuleId.FEW_STARS,
        SeverityId.INFO,
        penalty=5,
        threshold=5,
        threshold_unit=ThresholdUnit.COUNT,
    ),
    RuleDefinition(RuleId.NO_RELEASE, SeverityId.INFO, penalty=5, categories=HACS_ONLY),
    RuleDefinition(
        RuleId.PRERELEASE_ONLY, SeverityId.INFO, penalty=5, categories=HACS_ONLY
    ),
    RuleDefinition(RuleId.OUTDATED, SeverityId.INFO, penalty=5),
    RuleDefinition(RuleId.UNPINNED, SeverityId.INFO, penalty=5, categories=HACS_ONLY),
)

RULES_BY_ID: Final[dict[str, RuleDefinition]] = {d.id: d for d in RULE_DEFINITIONS}


def default_rules() -> list[Rule]:
    """Return the rule settings a fresh installation starts with."""
    return [
        Rule(
            id=str(definition.id),
            enabled=True,
            severity_id=str(definition.severity_id),
            penalty=definition.penalty,
            threshold=definition.threshold,
        )
        for definition in RULE_DEFINITIONS
    ]


def merge_rules(stored: list[Rule]) -> tuple[list[Rule], bool]:
    """Bring the stored rules in line with the catalogue.

    Rules added in a later version are appended with their defaults, rules that
    no longer exist are dropped, and the catalogue order is restored.
    """
    by_id = {rule.id: rule for rule in stored}
    merged: list[Rule] = []
    changed = len(by_id) != len(stored)
    for definition in RULE_DEFINITIONS:
        existing = by_id.pop(str(definition.id), None)
        if existing is None:
            changed = True
            merged.append(
                Rule(
                    id=str(definition.id),
                    severity_id=str(definition.severity_id),
                    penalty=definition.penalty,
                    threshold=definition.threshold,
                )
            )
        else:
            merged.append(existing)
    if by_id:
        changed = True
    if [r.id for r in stored] != [r.id for r in merged]:
        changed = True
    return merged, changed
