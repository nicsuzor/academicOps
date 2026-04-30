"""Structural tests for the rbg structured exemption schema.

Asserts that rbg.md replaces the free-form 'Judgment calls (no action
required)' section with the structured form from epic-e1ddba21:

  - Requires `Why this serves the principle's intent:` rationale
  - Forbids scope-based dismissals (`pre-existing`, `out of scope for
    this PR`) as exemption grounds
  - Requires a fix-attempt for mechanical violations RBG can fix before
    the exemption is available

These tests exercise the *prompt prose* — they do not run the LLM. They
prevent silent regression of the rule surface that closes the false-PASS
gap documented in issue #811 (thin 'judgment call' exemptions with
scope-based excuses).

Replay scenarios the rule must catch on a judging agent:

- Drafted RBG verdict with a 'Judgment calls' section and a scope-based
  excuse ('pre-existing', 'out of scope for this PR') and no rationale
  → structured-exemption rule rewrites or flags as violation, not soft pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RBG = REPO_ROOT / "aops-core" / "agents" / "rbg.md"


@pytest.fixture(scope="module")
def rbg_text() -> str:
    return RBG.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# rbg.md: Structured Exemption Schema section
# ---------------------------------------------------------------------------


def test_rbg_has_structured_exemption_schema_section(rbg_text: str) -> None:
    assert "Structured Exemption Schema" in rbg_text, (
        "rbg.md missing 'Structured Exemption Schema' section"
    )


def test_rbg_exemption_schema_replaces_judgment_calls_freeform(rbg_text: str) -> None:
    """The schema must explicitly replace the free-form 'Judgment calls
    (no action required)' shape — not coexist with it."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert "Judgment calls (no action required)" in section, (
        "Structured exemption schema must reference and replace the legacy "
        "'Judgment calls (no action required)' section name"
    )
    # The verb must be 'replace' to make the substitution explicit.
    assert "Replace" in section or "replace" in section, (
        "Structured exemption schema must use 'replace' to make the "
        "substitution of the legacy section explicit"
    )


def test_rbg_exemption_schema_requires_rationale_line(rbg_text: str) -> None:
    """The schema must require a `Why this serves the principle's intent:`
    line with one-sentence rationale."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert "Why this serves the principle's intent:" in section, (
        "Structured exemption schema must require the verbatim "
        "'Why this serves the principle's intent:' line"
    )
    # The rationale must be required, not optional.
    assert "required" in section.lower(), (
        "Structured exemption schema must mark the rationale line as required"
    )


def test_rbg_exemption_schema_treats_missing_rationale_as_violation(rbg_text: str) -> None:
    """No rationale → flagged violation, not soft pass."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert "flagged violation" in section, (
        "Structured exemption schema must specify that missing rationale is a 'flagged violation'"
    )
    assert "not a soft pass" in section, (
        "Structured exemption schema must explicitly contrast with 'soft pass'"
    )


def test_rbg_exemption_schema_lists_forbidden_grounds_section(rbg_text: str) -> None:
    """A FORBIDDEN exemption grounds list must exist and be unambiguous."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert "FORBIDDEN exemption grounds" in section, (
        "Structured exemption schema must include a 'FORBIDDEN exemption grounds' subsection header"
    )


@pytest.mark.parametrize(
    "phrase",
    [
        # Scope-based dismissals from issue #811 — must appear verbatim so
        # the rbg agent can pattern-match them in drafted exemptions.
        "pre-existing",
        "out of scope for this PR",
        "we'll get to it later",
    ],
)
def test_rbg_exemption_schema_forbids_scope_based_grounds(rbg_text: str, phrase: str) -> None:
    """Each scope-based dismissal must be enumerated verbatim."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert phrase in section, f"Structured exemption schema missing forbidden ground: {phrase!r}"


def test_rbg_exemption_schema_requires_fix_attempt_for_mechanical_violations(
    rbg_text: str,
) -> None:
    """For violations RBG has authority to fix mechanically, the agent
    MUST attempt the fix before the exemption is available."""
    section_start = rbg_text.find("Structured Exemption Schema")
    section = rbg_text[section_start:]
    assert "mechanical violations" in section, (
        "Structured exemption schema must mention 'mechanical violations'"
    )
    assert "attempt the fix" in section, (
        "Structured exemption schema must require RBG to 'attempt the fix' "
        "before the exemption is available"
    )
    assert "before the exemption" in section, (
        "Structured exemption schema must order fix-attempt BEFORE exemption-availability"
    )


def test_rbg_exemption_schema_cites_source_issue_811(rbg_text: str) -> None:
    """The rule must cite #811 so future maintainers find the context."""
    assert "#811" in rbg_text, "rbg.md structured exemption schema must cite issue #811"


# ---------------------------------------------------------------------------
# Fixture-style replay: a thin 'Judgment calls' exemption with scope-based
# excuse must collide with the schema.
# ---------------------------------------------------------------------------


DRAFTED_RBG_VERDICT_WITH_THIN_EXEMPTION = """
A5 — PASS

Judgment calls (no action required):
- The duplicated config block in `cli.py` and `gemini_wrapper.py` is
  pre-existing and out of scope for this PR. We can consolidate later.
"""


def test_drafted_thin_exemption_is_caught_by_schema(rbg_text: str) -> None:
    """A drafted RBG exemption that uses scope-based excuses with no
    rationale must collide with the structured schema. If this fails,
    either the fixture or the rule has drifted."""
    drafted_lower = DRAFTED_RBG_VERDICT_WITH_THIN_EXEMPTION.lower()
    rbg_lower = rbg_text.lower()

    # The drafted exemption's failure modes:
    #   1. Uses 'pre-existing' as exemption ground (FORBIDDEN)
    #   2. Uses 'out of scope for this PR' as exemption ground (FORBIDDEN)
    #   3. No `Why this serves the principle's intent:` line (REQUIRED)
    assert "pre-existing" in drafted_lower, (
        "Fixture must contain the 'pre-existing' scope-based excuse"
    )
    assert "out of scope for this pr" in drafted_lower, (
        "Fixture must contain the 'out of scope for this PR' scope-based excuse"
    )
    assert "why this serves the principle's intent:" not in drafted_lower, (
        "Fixture must lack the required rationale line"
    )

    # Rule must define each of these patterns.
    assert "pre-existing" in rbg_lower, (
        "rbg.md schema must list 'pre-existing' as forbidden to catch this draft"
    )
    assert "out of scope for this pr" in rbg_lower, (
        "rbg.md schema must list 'out of scope for this PR' as forbidden to catch this draft"
    )
    assert "why this serves the principle's intent:" in rbg_lower, (
        "rbg.md schema must require the rationale line to flag its absence in this draft"
    )
