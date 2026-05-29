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
    """The PKB-gap HALT rule must live inside the Persistence section (not a footnote elsewhere).

    WS1 refactor (three-layer junior.md) relocated this: the heading is now the
    `### Persistence: PKB, not files` subsection under `## Layer 3`, and the HALT
    rule is folded into a bullet (`**PKB gap = HALT.**`) rather than its own
    `### PKB Gap Behaviour` subsection. The invariant this test protects is
    unchanged: the load-bearing HALT text must sit *within* that Persistence
    section, so the section boundary is the next `### ` / `## ` heading.
    """
    content = JUNIOR_MD.read_text()
    persistence_start = content.index("### Persistence: PKB, not files")
    # Section ends at the next subsection (`### `) or top-level (`## `) heading.
    # `\n### ` matches `\n## ` does not, so search both and take the nearer one.
    next_h3 = content.find("\n### ", persistence_start + 1)
    next_h2 = content.find("\n## ", persistence_start + 1)
    candidates = [i for i in (next_h3, next_h2) if i != -1]
    assert candidates, "no section boundary found after the Persistence heading"
    persistence_end = min(candidates)

    # The HALT rule is identified by its two load-bearing literals. Both must sit
    # inside the Persistence section — if either is moved out, this trips.
    halt_emit = content.index("[ATTN] PKB verb missing:")
    halt_prohibition = content.index("Never invent a shell-out")
    assert persistence_start < halt_emit < persistence_end, (
        "The '[ATTN] PKB verb missing:' emit pattern must sit inside the "
        "'Persistence: PKB, not files' section, not elsewhere in junior.md"
    )
    assert persistence_start < halt_prohibition < persistence_end, (
        "The 'Never invent a shell-out' prohibition must sit inside the "
        "'Persistence: PKB, not files' section, not elsewhere in junior.md"
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
