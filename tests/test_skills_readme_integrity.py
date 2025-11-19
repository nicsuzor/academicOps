"""
Integration test for skills README documentation integrity.

Tests that skills/README.md properly documents all skills with clear
"when to use" guidance including specific triggers that help agents know
when to invoke each skill.

Following fail-fast principle: Documentation must be complete and accurate.

Run this test to validate skills README integrity:

    uv run pytest tests/test_skills_readme_integrity.py -xvs

This test ensures:
- Skills README exists and documents all skills
- Task skill has clear 'when to use' guidance
- 'When to use' includes specific triggers (not just operations)

When this test fails:
1. Update skills/README.md task skill section
2. Add specific triggers to 'When to use' section
3. Include: completion mentions, urgent/priority queries, status requests
4. Match triggers from task SKILL.md workflow section
"""

from pathlib import Path

import pytest


class TestSkillsReadmeIntegrity:
    """Validate skills README documentation completeness."""

    @pytest.fixture
    def repo_root(self):
        """Get repository root (1 level up from tests/)."""
        return Path(__file__).parents[1]

    @pytest.fixture
    def skills_readme_path(self, repo_root):
        """Get path to skills README (academicOps root)."""
        return repo_root / "skills" / "README.md"

    @pytest.fixture
    def skills_readme_content(self, skills_readme_path):
        """Load skills README content."""
        assert skills_readme_path.exists(), (
            f"Skills README not found at {skills_readme_path}"
        )
        return skills_readme_path.read_text()

    def test_readme_exists(self, skills_readme_path):
        """Verify skills README exists."""
        assert skills_readme_path.exists(), (
            f"Skills README missing at {skills_readme_path}"
        )

    def test_readme_documents_task_skill(self, skills_readme_content):
        """Verify task skill is documented in README."""
        assert "### tasks" in skills_readme_content, (
            "Task skill section not found in README"
        )

        # Should have the basic structure
        assert "**Purpose**:" in skills_readme_content, "README missing Purpose section"
        assert "**When to use**:" in skills_readme_content, (
            "README missing 'When to use' section"
        )

    def _extract_section(self, content: str, section_header: str) -> str:
        """
        Extract a markdown section by header.

        Args:
            content: Full markdown content
            section_header: Section header to find (e.g., "### tasks")

        Returns:
            Content from section header to next same-level header or end
        """
        lines = content.split("\n")
        section_start = None
        section_end = None

        for i, line in enumerate(lines):
            if line.strip() == section_header:
                section_start = i
            elif section_start is not None and line.startswith("###"):
                section_end = i
                break

        if section_end is None:
            section_end = len(lines)

        assert section_start is not None, f"Could not find section: {section_header}"

        return "\n".join(lines[section_start:section_end])

    def _extract_when_to_use(self, section_content: str) -> str:
        """
        Extract 'When to use' subsection content.

        Args:
            section_content: Markdown section containing **When to use**:

        Returns:
            Text content of when-to-use section (lowercase)
        """
        when_to_use_lines = []
        in_when_to_use = False

        for line in section_content.split("\n"):
            if "**When to use**:" in line:
                in_when_to_use = True
                continue
            if in_when_to_use:
                if line.startswith("**") and line.endswith("**:"):
                    # Hit next section
                    break
                when_to_use_lines.append(line)

        return "\n".join(when_to_use_lines).lower()

    def _check_triggers(self, when_to_use_text: str) -> list[str]:
        """
        Check for expected trigger patterns in when-to-use text.

        Args:
            when_to_use_text: Content of when-to-use section

        Returns:
            List of missing trigger descriptions (empty if all present)
        """
        trigger_patterns = [
            ("completion", "user mentions/indicates task completion"),
            ("urgent", "user asks about urgent/priority tasks"),
            ("status", "user requests task list or status"),
        ]

        missing_triggers = []
        for keyword, description in trigger_patterns:
            if keyword not in when_to_use_text:
                missing_triggers.append(description)

        return missing_triggers

    def test_task_skill_when_to_use_includes_triggers(self, skills_readme_content):
        """
        Verify task skill 'when to use' section includes specific triggers.

        The 'when to use' section should include concrete triggers that help
        agents understand WHEN to invoke the skill, not just WHAT it does.

        Expected triggers from task SKILL.md:
        - User mentions task completion
        - User asks about urgent/priority tasks
        - User requests task list/status
        """
        # Find the tasks section
        assert "### tasks" in skills_readme_content, "Task skill section not found"

        task_section = self._extract_section(skills_readme_content, "### tasks")

        # Find "When to use" subsection
        assert "**When to use**:" in task_section, (
            "Task skill missing 'When to use' section"
        )

        when_to_use_text = self._extract_when_to_use(task_section)

        # Check for specific trigger patterns
        missing_triggers = self._check_triggers(when_to_use_text)

        assert not missing_triggers, (
            "Task skill 'when to use' section missing triggers:\n"
            + "\n".join(f"  - {t}" for t in missing_triggers)
            + f"\n\nCurrent 'when to use' content:\n{when_to_use_text}\n\n"
            + "Expected: Specific triggers that indicate WHEN to use the skill, "
            + "not just operations (viewing, archiving, creating)."
        )
