"""Structural tests for A8 composition-time enforcement in the supervisor skill.

Asserts that the verbatim phrase blacklist from issues #720 and #821 is
embedded in the supervisor SKILL.md and decomposition-and-review.md, plus
the permitted halt template and the prohibited halt template that the
prose scan must flag.

These tests exercise the *prompt prose* — they do not run the LLM. They
prevent silent regression of the rule surface that closes the A8
composition-time gap.

Replay scenarios the rules must catch on a judging agent:

- Drafted supervisor decomposition containing "drift candidate",
  "skip on host", or "relax the assertion" prose → A8 prose scan rewrites
  or blocks.
- Drafted plan-review summary containing a fix-vs-skip menu →
  permitted-vs-prohibited halt content section flags it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL = REPO_ROOT / "aops-core" / "skills" / "supervisor" / "SKILL.md"
DECOMP = (
    REPO_ROOT
    / "aops-core"
    / "skills"
    / "supervisor"
    / "instructions"
    / "decomposition-and-review.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def decomp_text() -> str:
    return DECOMP.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# SKILL.md — Engineering Integrity (A8) Is Non-Negotiable subsection
# ---------------------------------------------------------------------------


def test_skill_has_engineering_integrity_section(skill_text: str) -> None:
    assert "Engineering Integrity (A8) Is Non-Negotiable" in skill_text, (
        "SKILL.md missing the A8 design-principle subsection"
    )


def test_skill_cites_a8_explicitly(skill_text: str) -> None:
    """The A8 binding must be in the Design Principles section, not buried."""
    # Section anchor must appear before Phases.
    a8_idx = skill_text.find("Engineering Integrity (A8)")
    phases_idx = skill_text.find("## Phases")
    assert 0 < a8_idx < phases_idx, "Engineering Integrity (A8) section must precede ## Phases"


@pytest.mark.parametrize(
    "phrase",
    [
        # Supervisor drift-framing blacklist (issue #821 verbatim)
        "drift candidate",
        "skip on <host>",
        "host-conditional",
        "skip-on-env",
        "relax the assertion",
        "softening the test",
        "loosen the check",
        "pytest.skip",
        "xfail",
        "fix vs skip",
        "we can either fix it or work around it",
    ],
)
def test_skill_contains_drift_framing_blacklist(skill_text: str, phrase: str) -> None:
    """The full verbatim blacklist from issue #821 must appear in SKILL.md."""
    assert phrase in skill_text, f"SKILL.md A8 section missing prohibited phrase: {phrase!r}"


def test_skill_contains_permitted_halt_template(skill_text: str) -> None:
    """The permitted halt template must appear verbatim so agents can match."""
    template_markers = [
        "A8 halt:",
        "Investigation produced",
        "Two options:",
        "Test stays as written",
    ]
    for marker in template_markers:
        assert marker in skill_text, f"SKILL.md permitted halt template missing marker: {marker!r}"


def test_skill_contains_worked_decomposition_example(skill_text: str) -> None:
    """The worked example anchors the rule with a concrete failing-test case."""
    assert "test_workspace_writes_visible_on_host" in skill_text, (
        "SKILL.md missing worked decomposition example"
    )
    assert "_is_remote_daemon()" in skill_text, (
        "SKILL.md worked example must reference _is_remote_daemon investigation"
    )


def test_skill_says_test_stays_untouched(skill_text: str) -> None:
    """Core rule: the test is not modified to make the failure go away."""
    # Either the SKILL.md says "the test is untouched" or "test stays as written".
    assert ("test stays as written" in skill_text.lower()) or (
        "test itself is **untouched**" in skill_text or "test itself is untouched" in skill_text
    ), "SKILL.md must explicitly state the test is not modified"


def test_skill_rejects_casual_user_authorisation(skill_text: str) -> None:
    """Casual user phrasing must not be treated as A8 exemption."""
    assert "we may need to adjust some tests" in skill_text, (
        "SKILL.md must call out the exact casual-phrasing trap from issue #821"
    )
    assert "A7" in skill_text, (
        "SKILL.md A8 binding must reference A7 (delegated authority) re user authorisation"
    )


# ---------------------------------------------------------------------------
# decomposition-and-review.md — A8 prose scan + halt content
# ---------------------------------------------------------------------------


def test_decomp_has_a8_prose_scan(decomp_text: str) -> None:
    assert "A8 prose scan" in decomp_text, (
        "decomposition-and-review.md missing A8 prose scan checkpoint"
    )


def test_decomp_post_decomp_self_check_lists_a8(decomp_text: str) -> None:
    """The self-check gate table must include the A8 prose-scan row."""
    # Find the Post-Decomposition Self-Check Gate section, then ensure the A8 row is in it.
    gate_idx = decomp_text.find("Post-Decomposition Self-Check Gate")
    assert gate_idx != -1, "Post-Decomposition Self-Check Gate section missing"
    gate_section = decomp_text[gate_idx : gate_idx + 4000]
    assert "A8 prose scan" in gate_section, (
        "Self-Check Gate table must list A8 prose scan as a check"
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "drift candidate",
        "skip on <host>",
        "host-conditional",
        "skip-on-env",
        "relax the assertion",
        "softening the test",
        "loosen the check",
        "pytest.skip",
        "xfail",
        "fix-or-skip menu",
        "fix vs skip",
        "we can either fix it or work around it",
    ],
)
def test_decomp_contains_drift_framing_blacklist(decomp_text: str, phrase: str) -> None:
    """The full verbatim blacklist must appear in decomposition-and-review.md."""
    assert phrase in decomp_text, (
        f"decomposition-and-review.md prose scan missing phrase: {phrase!r}"
    )


def test_decomp_has_permitted_halt_section(decomp_text: str) -> None:
    assert "Permitted vs prohibited halt content" in decomp_text, (
        "decomposition-and-review.md missing permitted/prohibited halt content section"
    )


def test_decomp_lists_prohibited_halt_columns(decomp_text: str) -> None:
    """The user-facing summary must explicitly forbid drift-style columns."""
    assert "Drift candidate" in decomp_text, (
        "Halt-content section must call out 'Drift candidate' columns as prohibited"
    )


def test_decomp_contains_permitted_halt_template(decomp_text: str) -> None:
    template_markers = [
        "A8 halt:",
        "Investigation produced",
        "Test stays as written",
    ]
    for marker in template_markers:
        assert marker in decomp_text, (
            f"decomposition-and-review.md permitted halt template missing: {marker!r}"
        )


def test_decomp_contains_prohibited_halt_template(decomp_text: str) -> None:
    """The prohibited halt template (drift candidate + skip on host) must be shown so the prose scan can flag it."""
    # Look for the prohibited shape's distinctive markers within a single window.
    window_start = decomp_text.find("Prohibited halt template")
    assert window_start != -1, (
        "decomposition-and-review.md missing 'Prohibited halt template' subsection"
    )
    window = decomp_text[window_start : window_start + 2000]
    for marker in ("Drift candidate", "Update the test", "Skip on"):
        assert marker in window, f"Prohibited halt template missing distinctive marker: {marker!r}"


# ---------------------------------------------------------------------------
# Fixture-style test: a drafted decomposition with prohibited prose must contain
# at least one phrase the prose-scan rule defines as forbidden.
# ---------------------------------------------------------------------------


DRAFTED_DECOMPOSITION_WITH_DRIFT_FRAMING = """
## Decomposition Proposal

### Subtasks

| ID | Title | Drift candidate? |
| -- | ----- | ---------------- |
| s1 | Investigate test_workspace_writes_visible_on_host | Yes |
| s2 | Either fix _is_remote_daemon() or skip on hosts where mount round-trip can't be guaranteed | — |

### Notes

If SessionStart is fired but late: relax the test to allow a wider tolerance.
We can either fix it or work around it via xfail on WSL2.
"""


def test_drafted_decomposition_with_drift_framing_is_caught_by_blacklist(
    decomp_text: str,
) -> None:
    """A drafted decomposition with prohibited prose must contain at least one
    phrase the prose-scan rule defines as forbidden — i.e. the rule definition
    actually covers the failure shape from issue #821."""
    drafted = DRAFTED_DECOMPOSITION_WITH_DRIFT_FRAMING.lower()

    # Each of these phrases is in the rule's blacklist AND in the drafted text.
    matched = []
    for phrase in [
        "drift candidate",
        "relax the test",
        "we can either fix it or work around it",
        "xfail",
    ]:
        if phrase in drafted and phrase in decomp_text.lower():
            matched.append(phrase)

    assert matched, (
        "Drafted prohibited decomposition must match at least one rule-blacklist phrase. "
        "If this fails, either the fixture or the rule has drifted."
    )
