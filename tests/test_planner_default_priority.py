"""Regression test: planner skill must mandate P3-default priority.

The planner has no privileged view of urgency — only the user does.
Auto-assigning P0/P1/P2 trains the user to ignore priority signals.
This test asserts the canonical default-P3 rule is present in the skill
body (verbatim) and that capture + decompose modes both reference it.
"""

import re
from pathlib import Path

import pytest

PLANNER_DIR = Path(__file__).parent.parent / "aops-core" / "skills" / "planner"
SKILL_MD = PLANNER_DIR / "SKILL.md"
DECOMPOSE_MD = PLANNER_DIR / "workflows" / "decompose.md"

# Verbatim phrasing required by task-e410b794 acceptance criteria.
DEFAULT_P3_RULE = (
    "Do not assign priority based on your assessment of importance. "
    "Use P3 as default. "
    "Only elevate when the user explicitly indicates urgency."
)


def test_skill_md_exists():
    assert SKILL_MD.is_file(), f"missing planner skill: {SKILL_MD}"


def test_decompose_workflow_exists():
    assert DECOMPOSE_MD.is_file(), f"missing decompose workflow: {DECOMPOSE_MD}"


def test_skill_contains_default_p3_rule_verbatim():
    """The exact verbatim default-P3 rule must appear in SKILL.md."""
    content = SKILL_MD.read_text()
    assert DEFAULT_P3_RULE in content, (
        "planner SKILL.md must contain the verbatim default-P3 rule "
        f"(see task-e410b794): {DEFAULT_P3_RULE!r}"
    )


def test_skill_has_priority_assignment_section():
    """The Priority Assignment Rules section must exist."""
    content = SKILL_MD.read_text()
    assert re.search(r"^##\s+Priority Assignment Rules\s*$", content, re.M), (
        "planner SKILL.md missing '## Priority Assignment Rules' section"
    )


def test_capture_mode_defaults_to_p3():
    """Capture mode instructions must default priority to P3."""
    content = SKILL_MD.read_text()
    # Capture mode lives between '### capture' and the next '### ' heading.
    capture_match = re.search(
        r"###\s+capture\b(.*?)(?=^###\s+\w+|\Z)",
        content,
        re.S | re.M,
    )
    assert capture_match, "could not locate '### capture' section in SKILL.md"
    capture_block = capture_match.group(1)
    assert re.search(r"default[^\n]{0,40}P3", capture_block, re.I), (
        "capture mode section must default priority to P3"
    )


def test_decompose_mode_defaults_subtasks_to_p3():
    """Decompose mode (in SKILL.md) must default subtasks to P3."""
    content = SKILL_MD.read_text()
    decompose_match = re.search(
        r"###\s+decompose\b(.*?)(?=^###\s+\w+|\Z)",
        content,
        re.S | re.M,
    )
    assert decompose_match, "could not locate '### decompose' section in SKILL.md"
    decompose_block = decompose_match.group(1)
    assert re.search(
        r"subtask[^\n]{0,80}P3|P3[^\n]{0,80}subtask|priority[^\n]{0,40}P3",
        decompose_block,
        re.I,
    ), "decompose mode must default subtask priority to P3"


def test_decompose_workflow_file_defaults_to_p3():
    """The decompose workflow file must default subtask priority to P3."""
    content = DECOMPOSE_MD.read_text()
    assert re.search(r"default[^\n]{0,40}P3|P3[^\n]{0,40}default", content, re.I), (
        "workflows/decompose.md must default subtask priority to P3"
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "Default for all new tasks",  # P3 row in the priority table
        "user explicitly",  # rule wording — only elevate when user signals
    ],
)
def test_skill_contains_supporting_phrases(phrase):
    content = SKILL_MD.read_text()
    assert phrase in content, f"planner SKILL.md missing expected phrase: {phrase!r}"
