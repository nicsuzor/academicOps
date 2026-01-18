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

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.user_prompt_submit import (
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
        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root, \
             patch("hooks.user_prompt_submit.get_bd_path") as mock_bd, \
             patch("hooks.user_prompt_submit.set_hydration_pending") as mock_pending:

            # Set up mocks
            mock_root.return_value = AOPS_CORE.parent
            mock_bd.return_value = None  # Skip bd queries

            # Call the function under test
            instruction = build_hydration_instruction(session_id, prompt, None)

            # Verify non-empty instruction returned
            assert instruction, "build_hydration_instruction should return non-empty string"
            assert "prompt-hydrator" in instruction.lower(), \
                "Instruction should mention prompt-hydrator"
            assert "/tmp/claude-hydrator/hydrate_" in instruction, \
                "Instruction should contain temp file path"

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
            "workflows_index": "workflow content",
            "skills_index": "skills content",
            "heuristics": "heuristics content",
            "bd_state": "",
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

    def test_context_template_preserves_todowrite_braces(self):
        """Verify TodoWrite examples in template keep their braces after formatting.

        The template contains TodoWrite examples with {content: "..."} syntax.
        These must appear in the output (with single braces) for the hydrator
        to understand the expected format.
        """
        template = load_template(CONTEXT_TEMPLATE_FILE)

        test_values = {
            "prompt": "test",
            "session_context": "",
            "framework_paths": "",
            "workflows_index": "",
            "skills_index": "",
            "heuristics": "",
            "bd_state": "",
        }

        result = template.format(**test_values)

        # After formatting, {{content: should become {content:
        assert "{content:" in result, \
            "Template should contain {content: in TodoWrite examples (escaped as {{content:)"
        assert "status:" in result, \
            "Template should contain TodoWrite status field"

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

        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root, \
             patch("hooks.user_prompt_submit.get_bd_path") as mock_bd, \
             patch("hooks.user_prompt_submit.set_hydration_pending") as mock_set, \
             patch("hooks.user_prompt_submit.clear_hydration_pending") as mock_clear:

            mock_root.return_value = AOPS_CORE.parent
            mock_bd.return_value = None

            build_hydration_instruction(session_id, prompt, None)

            # Should set pending, not clear
            mock_set.assert_called_once()
            assert session_id in str(mock_set.call_args), \
                "set_hydration_pending should be called with session_id"
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

    def test_actual_template_has_correct_escaping(self):
        """Verify the real template file has {{ escaping where needed."""
        template_path = CONTEXT_TEMPLATE_FILE
        raw_content = template_path.read_text()

        # After the --- separator, find the actual template
        if "\n---\n" in raw_content:
            template_content = raw_content.split("\n---\n", 1)[1]
        else:
            template_content = raw_content

        # Check that TodoWrite examples use {{ escaping
        assert "{{content:" in template_content, \
            "Template must escape {content: as {{content: in TodoWrite examples"

        # Verify no unescaped {content: outside of comments
        # (Single brace would cause format() to fail)
        lines = template_content.split("\n")
        for i, line in enumerate(lines):
            # Skip if it's the escaped version
            if "{{content:" in line:
                continue
            # Fail if unescaped {content: found
            if "{content:" in line:
                pytest.fail(
                    f"Line {i+1} has unescaped {{content:}} which will cause "
                    f"KeyError during formatting:\n{line}"
                )


class TestSkillsIndex:
    """Test skills index loading for hydrator context.

    Regression test for ns-rk48: Hydrator slow for known workflows - missing skill awareness.
    Root cause: Hydrator had no pre-loaded skills index, requiring memory search to
    recognize skill invocations like "daily list" -> /daily.

    Fix: Added SKILLS.md index and load_skills_index() to pre-load into hydrator context.
    """

    def test_load_skills_index_returns_content(self):
        """Verify load_skills_index returns non-empty content when SKILLS.md exists."""
        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root:
            mock_root.return_value = AOPS_CORE.parent

            result = load_skills_index()

            assert result, "load_skills_index should return non-empty string"
            assert "daily" in result.lower(), "Skills index should include /daily skill"

    def test_skills_index_contains_trigger_phrases(self):
        """Verify skills index includes trigger phrases for routing."""
        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root:
            mock_root.return_value = AOPS_CORE.parent

            result = load_skills_index()

            # Key trigger phrases that should enable fast routing
            assert "daily list" in result.lower() or "daily note" in result.lower(), \
                "Skills index should include 'daily list' or 'daily note' trigger"

    def test_skills_index_in_hydration_context(self):
        """Verify skills_index is included in hydration context template."""
        template = load_template(CONTEXT_TEMPLATE_FILE)

        # The template should have a {skills_index} placeholder
        assert "{skills_index}" in template or "skills_index" in template, \
            "Hydration context template should include skills_index placeholder"

    def test_build_hydration_includes_skills(self):
        """Verify build_hydration_instruction includes skills index in output."""
        prompt = "update my daily list"
        session_id = "test-session-skills"

        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root, \
             patch("hooks.user_prompt_submit.get_bd_path") as mock_bd, \
             patch("hooks.user_prompt_submit.set_hydration_pending"):

            mock_root.return_value = AOPS_CORE.parent
            mock_bd.return_value = None

            instruction = build_hydration_instruction(session_id, prompt, None)

            # The temp file should be created with skills content
            # We verify by checking the instruction references the temp file
            assert "/tmp/claude-hydrator/hydrate_" in instruction, \
                "Instruction should reference temp file containing skills index"

    def test_task_viz_skill_has_triggers(self):
        """Verify task-viz skill has trigger phrases for routing.

        Regression test for aops-ec9n: User asked 'run the task viz script' but
        hydrator routed to raw script execution instead of /task-viz skill because
        the skill had no triggers in SKILLS.md.

        Fix: Added triggers 'task visualization', 'visualize tasks', etc.
        """
        with patch("hooks.user_prompt_submit.get_aops_root") as mock_root:
            mock_root.return_value = AOPS_CORE.parent

            result = load_skills_index()

            # task-viz row should have actual triggers, not just "—"
            assert "/task-viz" in result, "Skills index should include /task-viz skill"

            # Find the task-viz row and verify it has triggers
            lines = result.split("\n")
            task_viz_line = next((l for l in lines if "/task-viz" in l), None)
            assert task_viz_line is not None, "Could not find /task-viz line"

            # Should NOT have empty triggers (just "—")
            assert "| — |" not in task_viz_line, \
                "task-viz skill must have trigger phrases, not empty triggers"

            # Should have at least one meaningful trigger
            meaningful_triggers = ["task visualization", "visualize tasks", "bd visualization"]
            has_trigger = any(t in task_viz_line.lower() for t in meaningful_triggers)
            assert has_trigger, \
                f"task-viz should have routing triggers like {meaningful_triggers}"
