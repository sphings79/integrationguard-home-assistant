"""The rule catalogue and how stored rules are brought in line with it."""

from __future__ import annotations

from custom_components.integrationguard.const import RuleId
from custom_components.integrationguard.health.rules import (
    RULE_DEFINITIONS,
    RULES_BY_ID,
    default_rules,
    merge_rules,
)
from custom_components.integrationguard.models import Rule


def test_every_rule_id_has_a_definition():
    assert {str(rule_id) for rule_id in RuleId} == set(RULES_BY_ID)


def test_definitions_are_unique():
    ids = [definition.id for definition in RULE_DEFINITIONS]
    assert len(ids) == len(set(ids))


def test_a_superseded_rule_comes_after_the_harsher_one():
    """The engine walks the catalogue in order and relies on this."""
    order = [definition.id for definition in RULE_DEFINITIONS]
    for definition in RULE_DEFINITIONS:
        if definition.supersedes is not None:
            assert order.index(definition.id) < order.index(definition.supersedes)


def test_defaults_cover_the_whole_catalogue():
    rules = default_rules()
    assert [rule.id for rule in rules] == [str(d.id) for d in RULE_DEFINITIONS]


def test_merge_adds_a_missing_rule():
    stored = [rule for rule in default_rules() if rule.id != RuleId.ARCHIVED]
    merged, changed = merge_rules(stored)
    assert changed is True
    assert any(rule.id == RuleId.ARCHIVED for rule in merged)


def test_merge_drops_an_unknown_rule():
    stored = [*default_rules(), Rule(id="from_the_future")]
    merged, changed = merge_rules(stored)
    assert changed is True
    assert all(rule.id != "from_the_future" for rule in merged)


def test_merge_keeps_what_the_user_changed():
    stored = default_rules()
    for rule in stored:
        if rule.id == RuleId.PUSH_AGE:
            rule.threshold = 42
            rule.penalty = 99
    merged, changed = merge_rules(stored)
    assert changed is False
    changed_rule = next(r for r in merged if r.id == RuleId.PUSH_AGE)
    assert changed_rule.threshold == 42
    assert changed_rule.penalty == 99
