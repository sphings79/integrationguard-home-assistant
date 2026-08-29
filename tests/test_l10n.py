"""Every catalogue must carry the same keys and the same placeholders."""

from __future__ import annotations

import re

import pytest

from custom_components.integrationguard.health.rules import RULE_DEFINITIONS
from custom_components.integrationguard.l10n import (
    CATALOGUES,
    EN,
    finding_text,
    normalise,
    translate,
)

PLACEHOLDER = re.compile(r"\{(\w+)\}")


@pytest.mark.parametrize("code", sorted(CATALOGUES))
def test_catalogue_has_every_key(code):
    assert set(CATALOGUES[code]) == set(EN)


@pytest.mark.parametrize("code", sorted(CATALOGUES))
def test_placeholders_survive_translation(code):
    """A lost placeholder silently swallows a value in the notification."""
    for key, text in CATALOGUES[code].items():
        assert set(PLACEHOLDER.findall(text)) == set(PLACEHOLDER.findall(EN[key])), key


@pytest.mark.parametrize("code", sorted(CATALOGUES))
def test_no_empty_values(code):
    assert all(value.strip() for value in CATALOGUES[code].values())


def test_every_rule_has_a_sentence():
    for definition in RULE_DEFINITIONS:
        key = (
            "rule.unpinned.branch"
            if definition.id == "unpinned"
            else f"rule.{definition.id}"
        )
        assert key in EN, definition.id


def test_regional_codes_fall_back_to_the_base_language():
    assert normalise("de-CH") == "de"
    assert normalise("pt_BR") == "pt"
    assert normalise("kl") == "en"
    assert normalise(None) == "en"


def test_translation_fills_in_the_values():
    assert translate("de", "rule.many_issues", count=7) == "7 offene Issues"
    assert translate("en", "rule.many_issues", count=7) == "7 open issues"


def test_a_missing_key_returns_itself():
    assert translate("en", "nothing.like.this") == "nothing.like.this"


def test_unpinned_picks_the_matching_sentence():
    assert "main" in finding_text("en", "unpinned", {"branch": "main"})
    assert "abc1234" in finding_text("en", "unpinned", {"commit": "abc1234"})
