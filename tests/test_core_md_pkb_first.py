"""Test that .agents/CORE.md points agents at the PKB specs first.

This is a content/structure assertion: the framework's CORE.md must tell
agents to consult the brain PKB (`brain/projects/aops/specs/`) before
spelunking source. Source-spelunking is a fallback, not a starting point.

If this test fails because the wording was reorganised, update the
constants — but do NOT remove the assertion. The PKB-first guidance is
the contract; the exact phrasing is the canonical user-facing reminder.
"""

from __future__ import annotations

import re
from pathlib import Path

CORE_MD_PATH = Path(__file__).resolve().parent.parent / ".agents" / "CORE.md"


def _read_core_md() -> str:
    assert CORE_MD_PATH.exists(), f"Missing: {CORE_MD_PATH}"
    return CORE_MD_PATH.read_text(encoding="utf-8")


def test_core_md_says_check_pkb_first() -> None:
    """CORE.md must contain the canonical 'Always check the PKB first' phrase."""
    body = _read_core_md()
    assert re.search(r"always check the pkb first", body, re.IGNORECASE), (
        "CORE.md must contain 'Always check the PKB first' (case-insensitive)"
    )


def test_core_md_links_to_specs_index() -> None:
    """CORE.md must link to the spec INDEX (wikilink or path form)."""
    body = _read_core_md()
    has_wikilink = "[[INDEX|brain/projects/aops/specs/INDEX]]" in body
    has_path = "brain/projects/aops/specs/INDEX" in body
    assert has_wikilink or has_path, (
        "CORE.md must reference brain/projects/aops/specs/INDEX "
        "(either as wikilink [[INDEX|brain/projects/aops/specs/INDEX]] "
        "or as a plain path)"
    )


def test_core_md_has_source_spelunking_fallback_warning() -> None:
    """CORE.md must contain the canonical source-spelunking-is-fallback line."""
    body = _read_core_md()
    needle = "If reading source code is your first move, you've skipped this step."
    assert needle in body, f"CORE.md must contain the verbatim line: {needle!r}"
