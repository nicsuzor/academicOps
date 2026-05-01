"""Structural tests for the /daily SEV4 concurrency-cap warning.

AC#4 of task-b4831821: /daily warns when active SEV4-committed target
count exceeds 2. The warning is a surface — it does not block.

These are static text assertions on aops-core/skills/daily/SKILL.md;
runtime invocation is covered by other daily-skill tests.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_SKILL_PATH = REPO_ROOT / "aops-core" / "skills" / "daily" / "SKILL.md"


def _read(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


class TestDailySev4Warning:
    """Static checks that the daily skill describes the SEV4-committed
    concurrency-cap warning per task-b4831821 AC#4."""

    def test_daily_skill_file_exists(self) -> None:
        assert DAILY_SKILL_PATH.exists(), f"daily SKILL.md missing at {DAILY_SKILL_PATH}"

    def test_warning_present(self) -> None:
        """The Status section's bullet list must mention the SEV4 cap warning."""
        content = _read(DAILY_SKILL_PATH)
        lower = content.lower()
        assert "sev4 cap warning" in lower, (
            "daily SKILL.md must declare a 'SEV4 cap warning' bullet "
            "in the Status section per task-b4831821 AC#4"
        )

    def test_warning_scoped_to_committed_targets(self) -> None:
        """Per AC#4, the cap applies to active SEV4-committed *targets*,
        not arbitrary SEV4 tasks."""
        content = _read(DAILY_SKILL_PATH)
        lower = content.lower()
        assert "committed" in lower, "SEV4 warning must reference goal_type: committed"
        assert "target" in lower, "SEV4 warning must reference target nodes (type: target)"

    def test_warning_states_cap_value(self) -> None:
        """The cap is 2; it must be stated explicitly."""
        content = _read(DAILY_SKILL_PATH)
        # Find the SEV4 line and check the cap=2 lives there.
        sev4_lines = [
            line for line in content.splitlines() if "SEV4" in line and "cap" in line.lower()
        ]
        assert sev4_lines, "Could not locate the SEV4 cap warning line"
        joined = " ".join(sev4_lines).lower()
        assert "2" in joined, "SEV4 warning must state the cap value (2)"

    def test_warning_is_surface_not_blocking(self) -> None:
        """AC: surface only — must not block tool use."""
        content = _read(DAILY_SKILL_PATH)
        lower = content.lower()
        # The warning bullet should explicitly mark itself as non-blocking
        # (either 'surface only' or by referencing /maintain's surface
        # framing). Find the bullet text and check the no-block framing
        # appears nearby.
        assert "sev4" in lower
        # Search for surface framing within the bullet/sentence containing
        # the warning. We accept either the literal bullet line or the
        # surrounding paragraph.
        sev4_paragraph = ""
        for paragraph in content.split("\n\n"):
            if "SEV4 cap warning" in paragraph:
                sev4_paragraph = paragraph.lower()
                break
        assert sev4_paragraph, "Could not isolate the SEV4 warning paragraph"
        assert any(
            phrase in sev4_paragraph for phrase in ("surface", "never block", "do not block")
        ), "SEV4 warning must be framed as surface-only / non-blocking"

    def test_warning_references_spec_or_maintain(self) -> None:
        """The warning should be discoverable: either by linking to the
        multi-parent-edges spec or by naming the /maintain counterpart."""
        content = _read(DAILY_SKILL_PATH)
        lower = content.lower()
        assert ("multi-parent-edges" in lower) or ("/maintain" in lower), (
            "SEV4 warning bullet should link to the spec or /maintain "
            "so a reader can trace the rationale"
        )
