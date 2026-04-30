"""Tests enforcing a single canonical definition of priority labels P0–P4.

These tests guard the invariant established by task-afb598f2: TAXONOMY.md is
the sole authoritative definition of priority labels, and other framework
documents must link to it rather than redefine the labels locally.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = REPO_ROOT / "aops-core" / "skills" / "remember" / "references" / "TAXONOMY.md"


# ---------------------------------------------------------------------------
# TAXONOMY.md is the canonical source.
# ---------------------------------------------------------------------------


def test_taxonomy_file_exists() -> None:
    assert TAXONOMY_PATH.exists(), f"Canonical taxonomy missing: {TAXONOMY_PATH}"


def test_taxonomy_has_priority_labels_section() -> None:
    text = TAXONOMY_PATH.read_text(encoding="utf-8")
    assert re.search(r"^##\s+Priority Labels\b", text, flags=re.MULTILINE), (
        "TAXONOMY.md must contain a '## Priority Labels' section"
    )


@pytest.mark.parametrize("label", ["P0", "P1", "P2", "P3", "P4"])
def test_taxonomy_defines_each_priority_label(label: str) -> None:
    """Each of P0–P4 must appear in a row of the priority labels table with a description."""
    text = TAXONOMY_PATH.read_text(encoding="utf-8")
    section = _extract_section(text, "Priority Labels")
    assert section, "Could not locate '## Priority Labels' section in TAXONOMY.md"

    # Expect a markdown table row beginning with | <label> | <name> | <meaning> |
    pattern = rf"^\|\s*{label}\s*\|\s*\S[^|]*\|\s*\S[^|]+\|"
    assert re.search(pattern, section, flags=re.MULTILINE), (
        f"TAXONOMY.md Priority Labels section missing a defining row for {label}"
    )


def test_taxonomy_distinguishes_priority_from_urgency() -> None:
    """The canonical doc must call out that priority is distinct from urgency/severity."""
    text = TAXONOMY_PATH.read_text(encoding="utf-8")
    section = _extract_section(text, "Priority Labels") or ""
    lowered = section.lower()
    assert "urgency" in lowered and "severity" in lowered, (
        "Priority Labels section must clarify that priority is not urgency or severity"
    )


# ---------------------------------------------------------------------------
# Other documents must link to TAXONOMY.md, not redefine priorities locally.
# ---------------------------------------------------------------------------

LINK_REGEX = re.compile(
    r"TAXONOMY\.md#priority-labels-p0p4",
    flags=re.IGNORECASE,
)


REFERENCING_FILES = [
    "aops-core/skills/hydrator/workflows/references/email-capture-details.md",
    "aops-core/skills/hydrator/workflows/email-capture.md",
    "aops-core/skills/planner/SKILL.md",
    "aops-core/commands/pull.md",
    "aops-core/skills/daily/SKILL.md",
    "aops-core/skills/daily/instructions/status-snapshot.md",
    "aops-core/skills/aops/templates/spec.md",
]


@pytest.mark.parametrize("relpath", REFERENCING_FILES)
def test_referencing_file_links_to_canonical_definition(relpath: str) -> None:
    path = REPO_ROOT / relpath
    assert path.exists(), f"Expected file does not exist: {relpath}"
    text = path.read_text(encoding="utf-8")
    assert LINK_REGEX.search(text), (
        f"{relpath} must link to TAXONOMY.md#priority-labels-p0p4 (canonical priority definitions)"
    )


def test_hydrator_email_capture_no_local_definition_block() -> None:
    """Email capture details must no longer carry the old 'P0 (Urgent)' standalone definition list."""
    path = REPO_ROOT / "aops-core/skills/hydrator/workflows/references/email-capture-details.md"
    text = path.read_text(encoding="utf-8")
    # The old bullets defined labels in isolation; the new form is a deadline
    # heuristic table that explicitly references the canonical doc.
    forbidden_phrases = [
        "**P0 (Urgent)**: Deadlines",
        "**P1 (High)**: Deadlines",
        "**P2 (Normal)**: General correspondence",
        "**P3 (Low)**: No deadline",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in text, (
            f"email-capture-details.md still contains a local priority definition: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_section(text: str, heading_title: str) -> str | None:
    """Return the body of a level-2 markdown section by title, or None."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading_title)}\b.*?(?=^##\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(0) if match else None
