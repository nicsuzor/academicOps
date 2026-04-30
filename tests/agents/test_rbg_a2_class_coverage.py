"""Structural tests for the rbg A2 two-part class-coverage check.

Asserts that rbg.md contains the two-part A2 rule from epic-e1ddba21:

  (a) mechanical genericity (the existing check)
  (b) class-coverage across all current members of the abstract class

A test wired to a single instance of an abstract class (e.g. pinned to
gemini while claude exists) violates A2 even when the test code reads as
generic. The rbg prompt must catch this — code-level genericity is
necessary but not sufficient.

These tests exercise the *prompt prose* — they do not run the LLM. They
prevent silent regression of the rule surface that closes the false-PASS
gap documented in issue #794.

Replay scenarios the rule must catch on a judging agent:

- Drafted RBG verdict that PASSes a single-target wiring test (pinned to
  one cli_tool variant, not parameterised) → A2 two-part check requires
  REQUEST_CHANGES citing class-coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RBG = REPO_ROOT / "aops-core" / "agents" / "rbg.md"
AXIOMS = REPO_ROOT / "aops-core" / "AXIOMS.md"


@pytest.fixture(scope="module")
def rbg_text() -> str:
    return RBG.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def axioms_text() -> str:
    return AXIOMS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# rbg.md: A2 Check (Two Parts) section
# ---------------------------------------------------------------------------


def test_rbg_has_two_part_a2_check_section(rbg_text: str) -> None:
    assert "A2 Check (Two Parts)" in rbg_text, "rbg.md missing 'A2 Check (Two Parts)' section"


def test_rbg_a2_check_specifies_part_a_mechanical_genericity(rbg_text: str) -> None:
    """Part (a) — code-level mechanical genericity."""
    assert "(a)" in rbg_text, "A2 two-part check missing part (a) label"
    section_start = rbg_text.find("A2 Check (Two Parts)")
    section = rbg_text[section_start:]
    assert "mechanically generic" in section.lower(), (
        "A2 two-part check part (a) must mention mechanical genericity"
    )


def test_rbg_a2_check_specifies_part_b_class_coverage(rbg_text: str) -> None:
    """Part (b) — coverage across all current members of the abstract class."""
    assert "(b)" in rbg_text, "A2 two-part check missing part (b) label"
    section_start = rbg_text.find("A2 Check (Two Parts)")
    section = rbg_text[section_start:]
    assert "all current members" in section, (
        "A2 two-part check part (b) must require coverage of 'all current members'"
    )
    assert "abstract class" in section, (
        "A2 two-part check part (b) must reference the 'abstract class' the rule applies to"
    )


def test_rbg_a2_check_calls_single_member_a_violation(rbg_text: str) -> None:
    """If only ONE class member is covered, that's an A2 violation regardless of
    code-level genericity. Make this prose explicit."""
    section_start = rbg_text.find("A2 Check (Two Parts)")
    section = rbg_text[section_start:]
    assert "If only ONE current class member is covered" in section, (
        "A2 two-part check must state the single-member violation rule verbatim"
    )
    assert "regardless of code-level genericity" in section, (
        "A2 two-part check must say single-member coverage violates A2 "
        "regardless of code-level genericity"
    )


def test_rbg_a2_check_specifies_request_changes_verdict(rbg_text: str) -> None:
    """The verdict for a single-member wiring test must be REQUEST_CHANGES with
    a parameterise-across-class-members directive."""
    section_start = rbg_text.find("A2 Check (Two Parts)")
    section = rbg_text[section_start:]
    assert "REQUEST_CHANGES" in section, "A2 two-part check must specify REQUEST_CHANGES verdict"
    assert "parameterise across class members" in section, (
        "A2 two-part check must specify the 'parameterise across class members' rewrite"
    )


def test_rbg_a2_check_allows_marked_todo_with_followup_task(rbg_text: str) -> None:
    """The escape hatch is a clearly-marked TODO + filed follow-up task ID,
    not a free-form judgment call."""
    section_start = rbg_text.find("A2 Check (Two Parts)")
    section = rbg_text[section_start:]
    assert "TODO" in section, (
        "A2 two-part check must allow only a clearly-marked TODO as the accept-anyway path"
    )
    assert "follow-up task" in section, (
        "A2 two-part check must require a filed follow-up task ID for the TODO carve-out"
    )


def test_rbg_a2_check_cites_source_issue_794(rbg_text: str) -> None:
    """The rule must cite #794 so future maintainers find the context."""
    assert "#794" in rbg_text, "rbg.md A2 two-part check must cite issue #794"


# ---------------------------------------------------------------------------
# rbg.md: Structured Exemption Schema — class-coverage interaction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        # Scope-based dismissals that the structured schema FORBIDS as
        # exemption grounds — see issue #811. These must appear verbatim
        # so the rbg agent can pattern-match them in drafted exemptions.
        "pre-existing",
        "out of scope for this PR",
        "we'll get to it later",
    ],
)
def test_rbg_forbids_scope_based_exemption_grounds(rbg_text: str, phrase: str) -> None:
    """The structured exemption schema must explicitly forbid these
    scope-based dismissals as exemption grounds."""
    assert phrase in rbg_text, (
        f"rbg.md structured exemption schema missing forbidden phrase: {phrase!r}"
    )


# ---------------------------------------------------------------------------
# AXIOMS.md: A2 entry must mention class-coverage explicitly
# ---------------------------------------------------------------------------


def test_axioms_a2_entry_mentions_class_coverage(axioms_text: str) -> None:
    """The AXIOMS.md A2 entry must state the class-coverage requirement
    explicitly — not just 'no special pleading' in general."""
    a2_start = axioms_text.find("## A2:")
    a3_start = axioms_text.find("## A3:")
    assert 0 < a2_start < a3_start, "Could not locate A2 entry in AXIOMS.md"
    a2_section = axioms_text[a2_start:a3_start]
    a2_lower = a2_section.lower()
    assert "all current members" in a2_lower, (
        "AXIOMS.md A2 entry must state the class-coverage requirement: "
        "'all current members of any abstract class'"
    )
    assert "abstract class" in a2_lower, (
        "AXIOMS.md A2 entry must reference the 'abstract class' concept directly"
    )


def test_axioms_a2_entry_calls_out_single_instance_pinning(axioms_text: str) -> None:
    """The AXIOMS.md A2 entry must explicitly call out that pinning to a
    single instance violates A2 even with mechanically generic code."""
    a2_start = axioms_text.find("## A2:")
    a3_start = axioms_text.find("## A3:")
    a2_section = axioms_text[a2_start:a3_start]
    a2_lower = a2_section.lower()
    assert "single instance" in a2_lower, (
        "AXIOMS.md A2 entry must state 'single instance' wiring is a violation"
    )
    assert "mechanically generic" in a2_lower, (
        "AXIOMS.md A2 entry must call out that the violation holds even when "
        "the test code is mechanically generic"
    )


# ---------------------------------------------------------------------------
# Fixture-style replay: a drafted RBG PASS verdict on a single-target test
# must trigger the two-part check.
# ---------------------------------------------------------------------------


DRAFTED_RBG_VERDICT_PASSING_SINGLE_TARGET_TEST = """
A2 — PASS. The wiring test asserts the agent dispatches via the polecat
docker pathway. The test code is mechanically generic — no hardcoded
session IDs, no special-cased gemini-only paths. The assertion uses the
abstract `cli_tool` parameter throughout.

The test only exercises the gemini variant, but that's fine because the
claude path follows the same code path and we have integration coverage
elsewhere.
"""


def test_drafted_single_target_pass_is_caught_by_two_part_rule(rbg_text: str) -> None:
    """A drafted RBG verdict that PASSes a single-target wiring test on
    code-level genericity alone must collide with the two-part rule. If
    this fails, either the fixture or the rule has drifted."""
    drafted_lower = DRAFTED_RBG_VERDICT_PASSING_SINGLE_TARGET_TEST.lower()
    rbg_lower = rbg_text.lower()

    # The drafted verdict's failure mode is "code is generic, only one
    # variant tested" — exactly what the rule's part (b) and the
    # "regardless of code-level genericity" clause must catch.
    assert "mechanically generic" in drafted_lower, (
        "Fixture must describe the code-level-genericity-only justification"
    )
    assert "only exercises" in drafted_lower or "only the gemini" in drafted_lower, (
        "Fixture must describe the single-instance coverage failure"
    )

    # Rule must define both halves of the test.
    assert "all current members" in rbg_lower, (
        "rbg.md two-part rule must require 'all current members' coverage to "
        "catch this drafted verdict"
    )
    assert "regardless of code-level genericity" in rbg_lower, (
        "rbg.md two-part rule must contain the 'regardless of code-level "
        "genericity' clause that overrides the drafted PASS"
    )
