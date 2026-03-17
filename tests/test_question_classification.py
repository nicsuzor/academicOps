"""Tests for hydration skipping logic in user_prompt_submit hook.

Tests the should_skip_hydration() function which determines whether a prompt
should skip the full hydration process (for notifications, skills, etc.) or
go through full hydration.
"""

import sys
from pathlib import Path

import pytest

# Add hooks directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from user_prompt_submit import should_skip_hydration


class TestSkipHydrationNotifications:
    """Test cases for prompts that should skip hydration (notifications, skills, etc.)."""

    def test_agent_notification(self):
        """Agent completion notifications should skip hydration."""
        assert (
            should_skip_hydration("<agent-notification>Task completed</agent-notification>") is True
        )

    def test_task_notification(self):
        """Task completion notifications should skip hydration."""
        assert (
            should_skip_hydration("<task-notification>aops-123 completed</task-notification>")
            is True
        )

    def test_slash_command_pull(self):
        """Slash commands like /pull should skip hydration."""
        assert should_skip_hydration("/pull aops-123") is True

    def test_slash_command_learn(self):
        """Slash commands like /learn should skip hydration."""
        assert should_skip_hydration("/learn something") is True

    def test_user_ignore_shortcut(self):
        """User ignore shortcuts starting with . should skip hydration."""
        assert should_skip_hydration(".ignore this") is True

    def test_dot_shortcut_various(self):
        """Various dot shortcuts should skip hydration."""
        assert should_skip_hydration(".quick action") is True


class TestDoNotSkipHydrationRegular:
    """Test cases for regular prompts that should NOT skip hydration."""

    def test_regular_question(self):
        """Regular questions should NOT skip hydration."""
        assert should_skip_hydration("What is the hydrator?") is False

    def test_regular_statement(self):
        """Regular statements should NOT skip hydration."""
        assert should_skip_hydration("I need to fix the gate.") is False

    def test_imperative_without_notification(self):
        """Imperative commands without slash should NOT skip hydration."""
        assert should_skip_hydration("Create a test file") is False

    def test_slash_command_not_at_start(self):
        """Slash not at start shouldn't be treated as command."""
        assert should_skip_hydration("Tell me about /commands") is False

    def test_dot_not_at_start(self):
        """Dot not at start shouldn't trigger ignore shortcut."""
        assert should_skip_hydration("This is a sentence. It has a dot.") is False


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_prompt(self):
        """Empty prompts should not skip hydration."""
        assert should_skip_hydration("") is False

    def test_whitespace_only(self):
        """Whitespace-only prompts should not skip hydration."""
        assert should_skip_hydration("   ") is False

    def test_notification_with_whitespace(self):
        """Notification with leading whitespace should still skip hydration."""
        assert should_skip_hydration("  <agent-notification>text</agent-notification>") is True

    def test_slash_with_whitespace(self):
        """Slash command with leading whitespace should still skip."""
        assert should_skip_hydration("  /pull aops-123") is True

    def test_dot_with_whitespace(self):
        """Dot shortcut with leading whitespace should skip."""
        assert should_skip_hydration("  .ignore") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
