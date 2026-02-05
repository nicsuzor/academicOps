#!/usr/bin/env python3
"""Unit tests verifying UserPromptSubmit hook fires correctly on first prompt.

Regression test for bug ns-uid: First prompt of session not triggering UserPromptSubmit.

Root cause: Template formatting collision where {content: in TodoWrite examples
was interpreted by Python's .format() as a placeholder, causing KeyError.
Fix: Escape braces with {{ in prompt-hydrator-context.md template.

Related:
- Bug ns-uid: Hydration gate bypassed - first prompt not triggering UserPromptSubmit
- Feature ns-1h65: Block progress until prompt hydrator has run
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.user_prompt_submit import (  # noqa: E402
    build_hydration_instruction,
    load_template,
    load_skills_index,
    CONTEXT_TEMPLATE_FILE,
)


class TestFirstPromptHydration:
    """Test that first prompt correctly triggers hydration pipeline."""

    def test_build_hydration_instruction_returns_instruction(self, tmp_path):
        """Verify build_hydration_instruction returns non-empty instruction.

        Regression: Bug ns-uid - hook was silently catching KeyError and returning
        empty dict when template contained {content: which .format() misinterpreted.
        """
        # Use a realistic first prompt
        prompt = "find the instructions on how to update the bd workflow"
        session_id = "test-session-12345"

        # Mock external dependencies to isolate the test
        with (
            patch("hooks.user_prompt_submit.get_plugin_root") as mock_root,
            patch("hooks.user_prompt_submit.set_hydration_pending") as mock_pending,
            patch(
                "hooks.user_prompt_submit.get_hydration_temp_dir", return_value=tmp_path
            ),
        ):
            # Set up mocks
            mock_root.return_value = AOPS_CORE

            # Call the function under test
            instruction = build_hydration_instruction(session_id, prompt, None)

            # Verify non-empty instruction returned
            assert instruction, (
                "build_hydration_instruction should return non-empty string"
            )
            assert "prompt-hydrator" in instruction.lower(), (
                "Instruction should mention prompt-hydrator"
            )
            assert str(tmp_path) in instruction, (
                "Instruction should contain temp file path"
            )

            # Verify hydration pending was set
            mock_pending.assert_called_once()

    def test_context_template_loads_without_format_error(self):
        """Verify context template can be formatted without KeyError.

        Regression: The template contained {content: which .format() treated
        as an undefined placeholder, causing silent failures.
        """
        template = load_template(CONTEXT_TEMPLATE_FILE)

        # Provide all expected placeholders
        test_values = {
            "prompt": "test user prompt",
            "session_context": "",
            "framework_paths": "## Resolved Paths\n| Path | Value |",
            "mcp_tools": "",
            "env_vars": "",
            "project_paths": "",
            "project_context_index": "",
            "workflows_index": "workflow content",
            "skills_index": "skills content",
            "heuristics": "heuristics content",
            "task_state": "",
            "relevant_files": "",
            "axioms": "",
        }

        # This should NOT raise KeyError
        try:
            result = template.format(**test_values)
        except KeyError as e:
            pytest.fail(
                f"Template format failed with KeyError: {e}. "
                f"This indicates unescaped braces in the template. "
                f"Braces in code examples like {{content: must be doubled."
            )

        # Verify the formatted content contains expected structure
        assert "## User Prompt" in result, "Missing User Prompt section"
        assert "test user prompt" in result, "Prompt not substituted"
        assert "## Your Task" in result, "Missing Your Task section"

    def test_context_template_preserves_structure_after_formatting(self):
        """Verify template structure is preserved after formatting.

        The template should format correctly with all placeholders and preserve
        the expected output structure including sections and code blocks.
        """
        template = load_template(CONTEXT_TEMPLATE_FILE)

        test_values = {
            "prompt": "test",
            "session_context": "",
            "framework_paths": "",
            "mcp_tools": "",
            "env_vars": "",
            "project_paths": "",
            "project_context_index": "",
            "workflows_index": "",
            "skills_index": "",
            "heuristics": "",
            "task_state": "",
            "relevant_files": "",
            "axioms": "",
        }

        result = template.format(**test_values)

        # Template should preserve key sections
        assert "## User Prompt" in result, "Template should contain User Prompt section"
        assert "## Your Task" in result, "Template should contain Your Task section"
        assert "## Return Format" in result, "Template should contain Return Format section"

    def test_hook_does_not_silently_fail(self):
        """Verify hook infrastructure errors propagate, not silently return empty.

        Design principle: Fail-fast (AXIOM #7). Infrastructure errors must be visible.
        """
        # Test with intentionally bad template to verify error propagation
        with patch("hooks.user_prompt_submit.load_template") as mock_load:
            mock_load.side_effect = FileNotFoundError("Template not found")

            with pytest.raises(FileNotFoundError):
                build_hydration_instruction("session", "prompt", None)

    def test_normal_prompt_triggers_hydration_pending(self, tmp_path):
        """Verify normal prompts set hydration_pending=True for gate enforcement.

        The hydration gate (PreToolUse hook) blocks tool use until hydrator runs.
        For this to work, UserPromptSubmit must set hydration_pending=True.
        """
        prompt = "Help me implement a new feature"
        session_id = "test-session-67890"

        with (
            patch("hooks.user_prompt_submit.get_plugin_root") as mock_root,
            patch("hooks.user_prompt_submit.set_hydration_pending") as mock_set,
            patch("hooks.user_prompt_submit.clear_hydration_pending") as mock_clear,
        ):
            mock_root.return_value = AOPS_CORE

            build_hydration_instruction(session_id, prompt, None)

            # Should set pending, not clear
            mock_set.assert_called_once()
            assert session_id in str(mock_set.call_args), (
                "set_hydration_pending should be called with session_id"
            )
            mock_clear.assert_not_called()


class TestTemplateEscaping:
    """Test that template escaping handles edge cases correctly."""

    def test_double_braces_become_single(self):
        """Basic Python format() escaping: {{ becomes {."""
        template = "Example: {{content: 'hello'}}"
        result = template.format()  # No placeholders
        assert result == "Example: {content: 'hello'}"

    def test_mixed_placeholders_and_literals(self):
        """Template with both real placeholders and escaped braces."""
        template = "User said: {prompt}\n\nExample: {{content: 'todo'}}"
        result = template.format(prompt="fix the bug")

        assert "User said: fix the bug" in result, "Placeholder not substituted"
        assert "{content: 'todo'}" in result, "Escaped braces not preserved"

    def test_actual_template_has_valid_placeholders(self):
        """Verify the real template file has valid placeholders that can be formatted."""
        template_path = CONTEXT_TEMPLATE_FILE
        raw_content = template_path.read_text()

        # After the --- separator, find the actual template
        if "\n---\n" in raw_content:
            template_content = raw_content.split("\n---\n", 1)[1]
        else:
            template_content = raw_content

        # Expected placeholders in the template
        expected_placeholders = [
            "{prompt}",
            "{session_context}",
            "{framework_paths}",
            "{project_context_index}",
            "{relevant_files}",
            "{workflows_index}",
            "{skills_index}",
            "{axioms}",
            "{heuristics}",
            "{task_state}",
        ]

        # Verify expected placeholders exist
        for placeholder in expected_placeholders:
            assert placeholder in template_content, (
                f"Template should contain {placeholder} placeholder"
            )


class TestSkillsIndex:
    """Test skills index loading for hydrator context."""

    def test_load_skills_index_returns_content(self, tmp_path):
        """Verify load_skills_index returns non-empty content when SKILLS.md exists."""
        # Create mock SKILLS.md
        mock_skills = tmp_path / "SKILLS.md"
        mock_skills.write_text("""---
name: Skills Index
---
# Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| /daily | Daily note | daily list, daily note |
| /task-viz | Task Viz | task visualization |
""")

        with patch("hooks.user_prompt_submit.get_plugin_root") as mock_root:
            mock_root.return_value = tmp_path

            result = load_skills_index()

            assert result, "load_skills_index should return non-empty string"
            assert "/daily" in result.lower(), (
                "Skills index should include /daily skill"
            )

    def test_skills_index_contains_trigger_phrases(self, tmp_path):
        """Verify skills index includes trigger phrases for routing."""
        mock_skills = tmp_path / "SKILLS.md"
        mock_skills.write_text("""---
name: Skills Index
---
| /daily | Daily note | daily list, daily note |
""")

        with patch("hooks.user_prompt_submit.get_plugin_root") as mock_root:
            mock_root.return_value = tmp_path

            result = load_skills_index()

            # Key trigger phrases that should enable fast routing
            assert "daily list" in result.lower() or "daily note" in result.lower(), (
                "Skills index should include 'daily list' or 'daily note' trigger"
            )

    def test_skills_index_in_hydration_context(self):
        """Verify skills_index is included in hydration context template."""
        template = load_template(CONTEXT_TEMPLATE_FILE)

        # The template should have a {skills_index} placeholder
        assert "{skills_index}" in template or "skills_index" in template, (
            "Hydration context template should include skills_index placeholder"
        )

    def test_build_hydration_includes_skills(self, tmp_path):
        """Verify build_hydration_instruction includes skills index in output."""
        prompt = "update my daily list"
        session_id = "test-session-skills"

        with (
            patch("hooks.user_prompt_submit.get_plugin_root") as mock_root,
            patch("hooks.user_prompt_submit.set_hydration_pending"),
            patch("hooks.user_prompt_submit.get_hydration_temp_dir", return_value=tmp_path),
            patch("hooks.user_prompt_submit.load_skills_index", return_value="/daily - Daily note"),
            patch("hooks.user_prompt_submit.load_axioms", return_value="# Axioms"),
            patch("hooks.user_prompt_submit.load_heuristics", return_value="# Heuristics"),
            patch("hooks.user_prompt_submit.load_workflows_index", return_value="# Workflows"),
            patch("hooks.user_prompt_submit.load_framework_paths", return_value="# Paths"),
            patch("hooks.user_prompt_submit.get_task_work_state", return_value=""),
            patch("hooks.user_prompt_submit.get_formatted_relevant_paths", return_value=""),
            patch("hooks.user_prompt_submit.load_project_context_index", return_value=""),
        ):
            mock_root.return_value = tmp_path

            instruction = build_hydration_instruction(session_id, prompt, None)

            # The temp file should be created with skills content
            # We verify by checking the instruction references the temp file
            assert str(tmp_path) in instruction, (
                "Instruction should reference temp file containing skills index"
            )

    def test_task_viz_skill_has_triggers(self, tmp_path):
        """Verify task-viz skill has trigger phrases for routing."""
        mock_skills = tmp_path / "SKILLS.md"
        mock_skills.write_text("""
| Skill | Description | Triggers |
|-------|-------------|----------|
| /task-viz | Task Viz | task visualization, visualize tasks |
""")

        with patch("hooks.user_prompt_submit.get_plugin_root") as mock_root:
            mock_root.return_value = tmp_path

            result = load_skills_index()

            # task-viz row should have actual triggers, not just "—"
            assert "/task-viz" in result, "Skills index should include /task-viz skill"

            # Find the task-viz row and verify it has triggers
            lines = result.split("\n")
            task_viz_line = next((line for line in lines if "/task-viz" in line), None)
            assert task_viz_line is not None, "Could not find /task-viz line"

            # Should NOT have empty triggers (just "—")
            assert "| — |" not in task_viz_line

            # Should have at least one meaningful trigger
            meaningful_triggers = [
                "task visualization",
                "visualize tasks",
                "bd visualization",
            ]
            has_trigger = any(t in task_viz_line.lower() for t in meaningful_triggers)
            assert has_trigger, (
                f"task-viz should have routing triggers like {meaningful_triggers}"
            )
