"""Structural tests for the rbg pre-response A8 scan rule.

Asserts that rbg.md contains the workaround-offer detection rule with the
verbatim phrase blacklist from issue #720 (general-agent workaround menu)
and the supervisor-specific drift-framing patterns from issue #821.

These tests exercise the *prompt prose* — they do not run the LLM. They
prevent silent regression of the rule surface that closes the A8
composition-time gap on the rbg side.

Replay scenario the rule must catch on a judging agent:

- Drafted general-agent response containing "bypass MCP, hit upstream
  API directly" within 2 turns of a tool failure → pre-response A8 scan
  flags as BLOCK.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RBG = REPO_ROOT / "aops-core" / "agents" / "rbg.md"


@pytest.fixture(scope="module")
def rbg_text() -> str:
    return RBG.read_text(encoding="utf-8")


def test_rbg_has_pre_response_a8_scan_section(rbg_text: str) -> None:
    assert "Pre-Response A8 Scan" in rbg_text, "rbg.md missing Pre-Response A8 Scan section"


def test_rbg_a8_scan_specifies_block_verdict(rbg_text: str) -> None:
    """The scan must produce a BLOCK verdict (not a REVISE/WARN)."""
    section_start = rbg_text.find("Pre-Response A8 Scan")
    assert section_start != -1
    section = rbg_text[section_start:]
    assert "a8-pre-response: BLOCK" in section, (
        "Pre-response A8 scan must emit `a8-pre-response: BLOCK` verdict label"
    )


def test_rbg_a8_scan_recency_window(rbg_text: str) -> None:
    """The scan must define a recency window to a tool failure."""
    section_start = rbg_text.find("Pre-Response A8 Scan")
    section = rbg_text[section_start:]
    # The rule must mention "last N turns" or similar to characterise recency.
    assert "last N turns" in section or "N=2" in section or "within" in section.lower(), (
        "Pre-response A8 scan must define a tool-failure recency window"
    )


@pytest.mark.parametrize(
    "phrase",
    [
        # General-agent workaround patterns (issue #720 verbatim)
        "bypass <tool>, use <other> directly",
        "bypass MCP, hit upstream API directly",
        "still tests <redefined scope>",
        "we note <failure> separately",
        "skip the broken <tool>",
        "route around <broken thing>",
    ],
)
def test_rbg_contains_general_agent_workaround_blacklist(rbg_text: str, phrase: str) -> None:
    """The full verbatim blacklist from issue #720 must appear in rbg.md."""
    assert phrase in rbg_text, f"rbg.md pre-response scan missing general-agent phrase: {phrase!r}"


@pytest.mark.parametrize(
    "phrase",
    [
        # Supervisor-specific drift-framing patterns (issue #821)
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
def test_rbg_contains_supervisor_drift_framing_blacklist(rbg_text: str, phrase: str) -> None:
    """rbg.md must also flag the supervisor drift-framing shapes from #821."""
    assert phrase in rbg_text, (
        f"rbg.md pre-response scan missing supervisor drift-framing phrase: {phrase!r}"
    )


def test_rbg_references_both_source_issues(rbg_text: str) -> None:
    """The rule must cite #720 and #821 so future maintainers find the context."""
    assert "#720" in rbg_text, "rbg.md A8 scan must cite issue #720"
    assert "#821" in rbg_text, "rbg.md A8 scan must cite issue #821"


def test_rbg_describes_structural_patterns(rbg_text: str) -> None:
    """Beyond verbatim phrases, the rule must catch structural workaround menus."""
    section_start = rbg_text.find("Pre-Response A8 Scan")
    section = rbg_text[section_start:]
    assert "Structural patterns" in section, (
        "Pre-response A8 scan must include a Structural patterns subsection"
    )
    # The canonical structural marker from #720: a menu offering debug AND route-around as peers.
    assert "peer" in section.lower(), (
        "Structural pattern section must describe the peer-options menu shape"
    )


def test_rbg_specifies_required_rewrite_shape(rbg_text: str) -> None:
    """The rule must tell the composing agent what shape to rewrite to."""
    section_start = rbg_text.find("Pre-Response A8 Scan")
    section = rbg_text[section_start:]
    assert "halt" in section.lower(), "Pre-response A8 scan must specify a halt-and-report rewrite"
    assert "verbatim" in section.lower(), (
        "Pre-response A8 scan must require the failure be surfaced verbatim"
    )


# ---------------------------------------------------------------------------
# Fixture-style test: a drafted general-agent response with bypass framing must
# match the rule's blacklist.
# ---------------------------------------------------------------------------


DRAFTED_GENERAL_AGENT_RESPONSE_WITH_WORKAROUND = """
The MCP wrapper crashed twice in a row. Two options:

1. Debug the MCP wrapper.
2. Bypass MCP, hit upstream API directly via curl — that still tests
   the upstream behavior, just not the MCP wrapping. We note the
   MCP-instability finding separately.

Option 2 gets us a result in ~30 seconds.
"""


def test_drafted_general_agent_workaround_is_caught_by_rbg_blacklist(rbg_text: str) -> None:
    """A drafted general-agent response with bypass framing must match at
    least one phrase the rbg blacklist defines. If this fails, either the
    fixture or the rbg rule has drifted."""
    drafted = DRAFTED_GENERAL_AGENT_RESPONSE_WITH_WORKAROUND.lower()
    rbg_lower = rbg_text.lower()

    matched = []
    for phrase in [
        "bypass mcp, hit upstream api directly",
        "still tests",
        "we note",
        "route around",
    ]:
        if phrase in drafted and phrase in rbg_lower:
            matched.append(phrase)

    assert matched, (
        "Drafted prohibited response must match at least one rbg blacklist phrase. "
        "Either the fixture or the rule has drifted."
    )
