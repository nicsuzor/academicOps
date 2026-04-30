#!/usr/bin/env python3
"""
Test for aops-0f2235dc (issue #185): age is not a staleness signal.

Verifies that:
- HEURISTICS.md contains the verbatim P#123 rule
- Sleep skill Phase 4 references P#123 or the heuristic phrase
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HEURISTICS = PROJECT_ROOT / "aops-core" / "HEURISTICS.md"
SLEEP_SKILL = PROJECT_ROOT / "aops-core" / "skills" / "sleep" / "SKILL.md"

VERBATIM = (
    "Age is not a staleness signal. Never cancel based on age alone. "
    "Only cancel when work becomes irrelevant. Garden passes surface "
    "candidates for human review — they do not recommend cancellation."
)


def test_heuristic_added_verbatim():
    """The exact heuristic wording must appear in HEURISTICS.md."""
    text = HEURISTICS.read_text(encoding="utf-8")
    assert VERBATIM in text, "P#123 verbatim wording missing from HEURISTICS.md"


def test_heuristic_has_p_number():
    """The heuristic must be numbered P#123."""
    text = HEURISTICS.read_text(encoding="utf-8")
    assert "P#123" in text, "P#123 identifier missing from HEURISTICS.md"


def test_sleep_phase_4_references_heuristic():
    """Sleep skill Phase 4 must explicitly reference P#123 or the rule phrase."""
    text = SLEEP_SKILL.read_text(encoding="utf-8")

    # Locate Phase 4 section
    phase_4_match = re.search(
        r"^## Phase 4:.*?(?=^## Phase \d+:|^## [A-Z])",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert phase_4_match, "Phase 4 section not found in sleep SKILL.md"
    phase_4 = phase_4_match.group(0)

    has_p_ref = "P#123" in phase_4
    has_phrase = "age is not a staleness signal" in phase_4.lower()
    assert has_p_ref or has_phrase, "Sleep Phase 4 does not reference P#123 or the heuristic phrase"
