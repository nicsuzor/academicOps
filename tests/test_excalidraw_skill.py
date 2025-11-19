"""
Integration test for excalidraw skill.

Tests that the excalidraw skill exists, has proper structure, and contains
comprehensive visual design guidance.

Following fail-fast principle: Skill must be properly structured and complete.
"""

from pathlib import Path

import pytest


class TestExcalidrawSkill:
    """Validate excalidraw skill structure and content."""

    @pytest.fixture
    def aops_root(self):
        """Get AOPS repository root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def skill_path(self, aops_root):
        """Get path to excalidraw skill."""
        return aops_root / "skills" / "excalidraw" / "SKILL.md"

    @pytest.fixture
    def skill_content(self, skill_path):
        """Load excalidraw skill content."""
        assert skill_path.exists(), f"Excalidraw skill not found at {skill_path}"
        return skill_path.read_text()

    def test_skill_file_exists(self, skill_path):
        """Verify excalidraw skill file exists."""
        assert skill_path.exists(), f"Excalidraw skill missing at {skill_path}"

    def test_skill_has_required_sections(self, skill_content):
        """Verify skill contains all required sections."""
        required_sections = [
            "# Excalidraw: Creating Visually Compelling Diagrams",
            "## When to Use This Skill",
            "## Core Visual Design Principles",
            "## Color Strategy",
            "## Typography & Text",
            "## Shape Selection & Usage",
            "## Arrows & Connectors",
            "## Layout & Spatial Organization",
            "## Quality Checklist",
        ]

        for section in required_sections:
            assert section in skill_content, f"Missing required section: {section}"

    def test_skill_emphasizes_visual_design(self, skill_content):
        """Verify skill focuses on visual design, not just technical details."""
        # Check for visual design keywords
        visual_keywords = [
            "visual hierarchy",
            "whitespace",
            "alignment",
            "color contrast",
            "beautiful",
            "professional",
        ]

        for keyword in visual_keywords:
            assert (
                keyword.lower() in skill_content.lower()
            ), f"Missing visual design keyword: {keyword}"

    def test_skill_de_emphasizes_mermaid(self, skill_content):
        """Verify Mermaid is de-emphasized (mentioned but not primary method)."""
        # Mermaid should appear, but not in main sections
        assert "mermaid" in skill_content.lower(), "Should mention Mermaid as option"

        # But it shouldn't be in the core visual design sections
        core_sections = skill_content.split("## Technical Integration")[0]
        mermaid_count_in_core = core_sections.lower().count("mermaid")

        # Should be mentioned minimally in core content
        assert (
            mermaid_count_in_core <= 3
        ), "Mermaid too prominent in core skill content"

    def test_skill_has_anti_patterns(self, skill_content):
        """Verify skill includes anti-patterns to avoid."""
        assert (
            "## Anti-Patterns to Avoid" in skill_content
        ), "Missing anti-patterns section"
        assert "boring diagram" in skill_content.lower(), "Should call out boring diagrams"

    def test_references_directory_exists(self, aops_root):
        """Verify references directory exists."""
        references_dir = aops_root / "skills" / "excalidraw" / "references"
        assert references_dir.exists(), f"References directory missing at {references_dir}"

    def test_mcp_reference_exists(self, aops_root):
        """Verify MCP server setup reference exists."""
        mcp_ref = aops_root / "skills" / "excalidraw" / "references" / "mcp-server-setup.md"
        assert mcp_ref.exists(), f"MCP reference missing at {mcp_ref}"

    def test_json_reference_exists(self, aops_root):
        """Verify JSON format reference exists."""
        json_ref = aops_root / "skills" / "excalidraw" / "references" / "json-format.md"
        assert json_ref.exists(), f"JSON reference missing at {json_ref}"

    def test_skill_provides_actionable_guidance(self, skill_content):
        """Verify skill provides clear, actionable guidance."""
        # Should have specific instructions, not just theory
        actionable_markers = [
            "checklist",
            "step ",
            "rule",
        ]

        found_markers = sum(
            1 for marker in actionable_markers if marker.lower() in skill_content.lower()
        )

        assert (
            found_markers >= 2
        ), "Skill should provide actionable guidance with steps, rules, or checklists"
