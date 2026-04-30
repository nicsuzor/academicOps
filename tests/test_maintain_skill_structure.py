"""Structural tests for the /maintain slash command.

The command file at aops-core/commands/maintain.md exists, declares the
expected anti-inflation acceptance-criteria sections, and links back to
the planner skill where the canonical procedures live.

These are static structural assertions only — no runtime invocation.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAINTAIN_PATH = REPO_ROOT / "aops-core" / "commands" / "maintain.md"
PLANNER_PATH = REPO_ROOT / "aops-core" / "skills" / "planner" / "SKILL.md"


def _read(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


class TestMaintainSkillStructure:
    """Static checks on aops-core/commands/maintain.md."""

    def test_command_file_exists(self) -> None:
        assert MAINTAIN_PATH.exists(), f"/maintain slash command file missing at {MAINTAIN_PATH}"

    def test_frontmatter_declares_command_metadata(self) -> None:
        content = _read(MAINTAIN_PATH)
        # Frontmatter block present
        assert content.startswith("---\n"), "maintain.md must start with YAML frontmatter"
        # Required frontmatter keys
        for key in ("name: maintain", "type: command", "permalink: commands/maintain"):
            assert key in content, f"Frontmatter missing `{key}`"

    def test_links_to_planner_anti_inflation_procedure(self) -> None:
        """AC: /maintain orchestrates the planner's anti-inflation checks
        — it must point at them, not redefine them."""
        content = _read(MAINTAIN_PATH)
        # The command must reference the planner skill explicitly so a
        # reader (or future agent) can find the SSoT.
        assert "planner" in content.lower(), "maintain.md must reference the planner skill"
        assert "SKILL.md" in content, "maintain.md must link to aops-core/skills/planner/SKILL.md"
        assert "anti-inflation" in content.lower(), (
            "maintain.md must reference the Anti-Inflation Surface section by name"
        )

    def test_references_multi_parent_edges_spec(self) -> None:
        """The spec sections that defer to /maintain must be cited so
        the link from spec → command is bidirectional."""
        content = _read(MAINTAIN_PATH)
        assert "multi-parent-edges" in content, (
            "maintain.md must cite projects/aops/specs/pkb/multi-parent-edges.md"
        )
        # All four spec sections that map to ACs.
        for ref in ("§1.5", "§2.3", "§6 Q4"):
            assert ref in content, f"maintain.md must cite spec section {ref}"

    def test_ac1_targets_missing_consequence_prose(self) -> None:
        """AC#1: lists targets missing `consequence` prose."""
        content = _read(MAINTAIN_PATH)
        assert "consequence" in content.lower()
        assert "missing consequence prose" in content.lower(), (
            "AC#1 finding section heading must surface 'missing consequence prose'"
        )

    def test_ac2_edges_missing_justification(self) -> None:
        """AC#2: lists `contributes_to` edges missing `why:` / `justification:`."""
        content = _read(MAINTAIN_PATH)
        assert "contributes_to" in content, "AC#2 must mention contributes_to edges by name"
        # The check should mention either alias.
        assert "why:" in content or "justification" in content.lower(), (
            "AC#2 must cite the why:/justification: edge field"
        )

    def test_ac3_sev4_weak_prose_heuristic(self) -> None:
        """AC#3: flags SEV4 targets with weak consequence prose; this is
        an advisory heuristic, not a blocker."""
        content = _read(MAINTAIN_PATH)
        lower = content.lower()
        assert "sev4" in lower or "severity: 4" in lower or "severity 4" in lower, (
            "AC#3 must reference SEV4 targets"
        )
        assert "heuristic" in lower or "advisory" in lower, (
            "AC#3 must be framed as a heuristic / advisory check"
        )
        # The keyword list itself lives in planner SKILL.md — confirm the link.
        assert "keyword" in lower, (
            "AC#3 must reference the severe-state keyword list (in planner SKILL.md)"
        )

    def test_ac4_sev4_committed_concurrency(self) -> None:
        """AC#4: surfaces the SEV4-committed concurrency cap (mirrors /daily)."""
        content = _read(MAINTAIN_PATH)
        lower = content.lower()
        assert "committed" in lower, "AC#4 must scope concurrency to goal_type: committed targets"
        assert "cap" in lower, "AC#4 must mention the concurrency cap"
        assert "2" in content, "AC#4 cap value is 2"

    def test_surface_only_no_blocking_no_autofix(self) -> None:
        """The whole point: /maintain surfaces, never blocks, never auto-fixes."""
        content = _read(MAINTAIN_PATH)
        lower = content.lower()
        assert "surface" in lower, "Command must declare 'surface-only' framing"
        # Explicit no-block / no-autofix language.
        assert any(phrase in lower for phrase in ("never block", "do not block", "never blocks")), (
            "Command must explicitly state it does not block tool use"
        )
        assert any(
            phrase in lower for phrase in ("no auto-fix", "never auto-fix", "do not auto-fix")
        ), "Command must explicitly state it does not auto-fix"

    def test_planner_anti_inflation_section_still_exists(self) -> None:
        """The planner SKILL.md is the SSoT for these checks. If that
        section is renamed or deleted, /maintain's link is dead — fail
        loudly here so the rename gets propagated."""
        content = _read(PLANNER_PATH)
        assert "Anti-Inflation Surface" in content, (
            "planner SKILL.md must still contain the 'Anti-Inflation Surface' "
            "section that /maintain links to"
        )
