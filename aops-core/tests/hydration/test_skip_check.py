"""Tests for hydration skip check logic.

Covers should_skip_hydration() including the is_subagent parameter
that fixes Gemini CLI sidechain detection (where session_id alone
was insufficient to detect subagent context).
"""

from unittest.mock import patch

from lib.hydration.skip_check import should_skip_hydration


class TestSubagentSkip:
    """Test subagent detection in skip check."""

    def test_explicit_is_subagent_true_skips(self):
        """When is_subagent=True is passed, hydration is skipped."""
        result = should_skip_hydration("normal prompt", is_subagent=True)
        assert result is True

    def test_explicit_is_subagent_false_does_not_skip(self):
        """When is_subagent=False, prompt content determines skip."""
        # Normal prompt with is_subagent=False should NOT skip
        result = should_skip_hydration("normal prompt", is_subagent=False)
        assert result is False

    def test_is_subagent_none_falls_back_to_detection(self):
        """When is_subagent=None (default), uses is_subagent_session()."""
        # Without session_id, is_subagent_session returns False
        result = should_skip_hydration("normal prompt", is_subagent=None)
        assert result is False

    def test_gemini_sidechain_with_explicit_flag(self):
        """Gemini sidechains work when is_subagent flag is passed.

        This is the key fix: Gemini session IDs don't match the short hex
        pattern used by is_subagent_session(), but when the router passes
        is_subagent=True (computed from is_sidechain flag), hydration skips.
        """
        gemini_session_id = "gemini-20260213-143000-abc12345"
        # Patch os.getcwd() to a neutral path so is_subagent_session() path-based
        # detection doesn't fire in CI/agent environments (e.g. paths with /agent-).
        with patch("lib.hook_utils.os.getcwd", return_value="/home/runner/work"):
            # Without is_subagent flag, would NOT skip (Gemini session ID doesn't match pattern)
            result_without = should_skip_hydration(
                "normal prompt", session_id=gemini_session_id, is_subagent=None
            )
            assert result_without is False

        # With is_subagent=True, DOES skip (no need to patch - flag short-circuits)
        result_with = should_skip_hydration(
            "normal prompt", session_id=gemini_session_id, is_subagent=True
        )
        assert result_with is True


class TestPromptPatternSkip:
    """Test skip conditions based on prompt content."""

    def test_slash_command_skips(self):
        """Prompts starting with / skip hydration."""
        assert should_skip_hydration("/commit") is True
        assert should_skip_hydration("/pull task-123") is True

    def test_expanded_slash_command_skips(self):
        """Expanded slash commands with <command-name> tag skip."""
        prompt = "# /commit\n<command-name>/commit</command-name>"
        assert should_skip_hydration(prompt) is True

    def test_agent_notification_skips(self):
        """Agent notifications skip hydration."""
        assert (
            should_skip_hydration("<agent-notification>Task complete</agent-notification>") is True
        )

    def test_task_notification_skips(self):
        """Task notifications skip hydration."""
        assert should_skip_hydration("<task-notification>Done</task-notification>") is True

    def test_dot_prefix_skips(self):
        """Prompts starting with . (ignore shortcut) skip."""
        assert should_skip_hydration(".just do it without hydration") is True

    def test_hash_slash_skips(self):
        """Prompts starting with # / (expanded skill) skip."""
        assert should_skip_hydration("# /pull task-123") is True

    def test_normal_prompt_does_not_skip(self):
        """Normal prompts do not skip hydration."""
        assert should_skip_hydration("Please fix the bug in auth.py") is False
        assert should_skip_hydration("Add a new feature") is False


class TestCommandArgsHydration:
    """Test that slash commands with multi-word args trigger hydration."""

    def test_expanded_command_with_multi_word_args_does_not_skip(self):
        """Slash commands with NL args should NOT skip hydration.

        Regression: /pull task-id and deconstruct was treated as two task IDs
        instead of being hydrated for intent parsing.
        """
        prompt = (
            "<command-message>pull</command-message>\n"
            "<command-name>/pull</command-name>\n"
            "<command-args>buttermilk-27315753 and deconstruct</command-args>\n"
            "# /pull - Pull, Claim, and Complete a Task\n"
            "ARGUMENTS: buttermilk-27315753 and deconstruct"
        )
        assert should_skip_hydration(prompt) is False

    def test_expanded_command_with_single_arg_skips(self):
        """Slash commands with a single task ID arg should still skip."""
        prompt = (
            "<command-message>pull</command-message>\n"
            "<command-name>/pull</command-name>\n"
            "<command-args>buttermilk-27315753</command-args>\n"
            "# /pull - Pull, Claim, and Complete a Task\n"
            "ARGUMENTS: buttermilk-27315753"
        )
        assert should_skip_hydration(prompt) is True

    def test_expanded_command_with_no_args_skips(self):
        """Bare slash commands (no args) should still skip."""
        prompt = (
            "<command-message>pull</command-message>\n"
            "<command-name>/pull</command-name>\n"
            "# /pull - Pull, Claim, and Complete a Task"
        )
        assert should_skip_hydration(prompt) is True

    def test_expanded_command_with_empty_args_skips(self):
        """Commands with empty <command-args> tag should skip."""
        prompt = (
            "<command-message>commit</command-message>\n"
            "<command-name>/commit</command-name>\n"
            "<command-args></command-args>\n"
            "# /commit"
        )
        assert should_skip_hydration(prompt) is True

    def test_learn_with_multi_word_args_does_not_skip(self):
        """Other commands with NL args also trigger hydration."""
        prompt = (
            "<command-message>learn</command-message>\n"
            "<command-name>/learn</command-name>\n"
            "<command-args>this is why hydrator should block everything</command-args>\n"
            "# /learn - Graduated Framework Improvement"
        )
        assert should_skip_hydration(prompt) is False


class TestEdgeCases:
    """Edge cases and whitespace handling."""

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is handled."""
        assert should_skip_hydration("  /commit  ") is True
        assert should_skip_hydration("\n.ignore\n") is True

    def test_empty_prompt(self):
        """Empty prompt does not crash."""
        assert should_skip_hydration("") is False
        assert should_skip_hydration("   ") is False
