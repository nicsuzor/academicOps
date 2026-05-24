"""
Regression test: junior.md and CORE.md must carry the PKB-gap HALT instruction.

Failure mode being tested: silent workaround (2026-05-19 incident) where the
orchestrator invented a shell-out when an MCP verb was missing, bypassing the
PKB entirely.  The fix is instruction-enforced: see aops-18572bc0 §5.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
JUNIOR_MD = REPO_ROOT / "aops-core/agents/junior.md"
CORE_MD = REPO_ROOT / ".agents/CORE.md"


def test_junior_md_has_pkb_gap_halt_instruction():
    """junior.md must carry the [ATTN] PKB verb missing halt instruction."""
    content = JUNIOR_MD.read_text()
    assert "[ATTN] PKB verb missing:" in content, (
        "junior.md is missing the '[ATTN] PKB verb missing:' emit pattern "
        "(required by aops-18572bc0 §5)"
    )
    assert "Never invent a shell-out" in content, (
        "junior.md is missing the explicit prohibition on shell-out workarounds"
    )


def test_junior_md_pkb_gap_section_is_load_bearing():
    """The PKB Gap Behaviour section must appear in the Persistence section (not a footnote)."""
    content = JUNIOR_MD.read_text()
    persistence_start = content.index("## Persistence: PKB, Not Files")
    pkb_gap_start = content.index("### PKB Gap Behaviour")
    # Section must appear after the Persistence heading and before the next top-level heading
    next_h2 = content.index("\n## ", persistence_start + 1)
    assert persistence_start < pkb_gap_start < next_h2, (
        "PKB Gap Behaviour section must sit inside 'Persistence: PKB, Not Files', "
        "not elsewhere in junior.md"
    )


def test_core_md_has_pkb_rules_section():
    """CORE.md must carry a PKB Rules section prohibiting shell-outs for MCP gaps."""
    content = CORE_MD.read_text()
    assert "## PKB Rules" in content, (
        "CORE.md is missing the '## PKB Rules' section (required by aops-18572bc0 §5)"
    )
    assert "HALT" in content[content.index("## PKB Rules") :], (
        "CORE.md PKB Rules section must contain 'HALT'"
    )
    assert "shell-out" in content[content.index("## PKB Rules") :], (
        "CORE.md PKB Rules section must prohibit shell-outs"
    )
    assert "[ATTN] PKB verb missing:" in content, (
        "CORE.md must include the '[ATTN] PKB verb missing:' emit pattern"
    )
