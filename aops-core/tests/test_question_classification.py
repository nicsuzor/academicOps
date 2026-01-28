"""Tests for pure question detection in user_prompt_submit hook.

Tests the is_pure_question() function which determines whether a prompt
should fast-track to simple-question workflow (no hydration needed) or
go through full hydration.
"""

import pytest
import sys
from pathlib import Path

# Add hooks directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from user_prompt_submit import is_pure_question


class TestPureQuestions:
    """Test cases for prompts that ARE pure questions (should return True)."""

    def test_what_question(self):
        """'What is X' questions are pure information requests."""
        assert is_pure_question("What is the hydrator?") is True

    def test_how_question(self):
        """'How does X work' questions are pure information requests."""
        assert is_pure_question("How does the task system work?") is True

    def test_where_question(self):
        """'Where is X' questions are pure information requests."""
        assert is_pure_question("Where are errors handled?") is True

    def test_why_question(self):
        """'Why is X' questions without action keywords are pure questions."""
        assert is_pure_question("Why is the gate blocking?") is True

    def test_explain_request(self):
        """'Explain X' requests are pure information requests."""
        assert is_pure_question("Explain the architecture") is True

    def test_describe_request(self):
        """'Describe X' requests are pure information requests."""
        assert is_pure_question("Describe the workflow system") is True

    def test_which_question(self):
        """'Which X' questions are pure information requests."""
        assert is_pure_question("Which workflow handles commits?") is True

    def test_is_question(self):
        """'Is X' questions are pure information requests."""
        assert is_pure_question("Is the memory server running?") is True

    def test_does_question(self):
        """'Does X' questions are pure information requests."""
        assert is_pure_question("Does the hydrator support batching?") is True

    def test_tell_me_about(self):
        """'Tell me about X' is a pure information request."""
        assert is_pure_question("Tell me about the task manager") is True


class TestNotPureQuestions:
    """Test cases for prompts that are NOT pure questions (should return False)."""

    def test_question_with_fix(self):
        """Questions containing 'fix' are action requests."""
        assert is_pure_question("What should I add to fix this?") is False

    def test_question_with_implement(self):
        """Questions containing 'implement' are action requests."""
        assert is_pure_question("How can you help me implement this?") is False

    def test_can_you_create(self):
        """'Can you create' is an action request, not pure question."""
        assert is_pure_question("Can you create a new file?") is False

    def test_please_with_action(self):
        """'Please' indicates a request for action."""
        assert is_pure_question("Please explain and then fix it") is False

    def test_imperative_add(self):
        """Imperatives like 'add' indicate action requests."""
        assert is_pure_question("What needs to be added here?") is False

    def test_help_me(self):
        """'Help me' indicates an action request."""
        assert is_pure_question("How can you help me with this?") is False

    def test_update_keyword(self):
        """Questions with 'update' are action requests."""
        assert is_pure_question("What should I update?") is False

    def test_commit_keyword(self):
        """Questions with 'commit' are action requests."""
        assert is_pure_question("How should I commit these changes?") is False

    def test_non_interrogative_start(self):
        """Prompts not starting with interrogatives are not pure questions."""
        assert is_pure_question("Add a new feature") is False

    def test_imperative_sentence(self):
        """Direct imperative sentences are not questions."""
        assert is_pure_question("Create a test file") is False


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_prompt(self):
        """Empty prompts are not pure questions."""
        assert is_pure_question("") is False

    def test_whitespace_prompt(self):
        """Whitespace-only prompts are not pure questions."""
        assert is_pure_question("   ") is False

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        assert is_pure_question("WHAT IS THE HYDRATOR?") is True
        assert is_pure_question("What Is The Hydrator?") is True

    def test_whats_contraction(self):
        """Contractions like 'what's' should work."""
        assert is_pure_question("What's the difference between X and Y?") is True

    def test_hows_contraction(self):
        """Contractions like 'how's' should work."""
        assert is_pure_question("How's the task system organized?") is True

    def test_question_with_run(self):
        """Questions with 'run' are action requests."""
        assert is_pure_question("How do I run the tests?") is False

    def test_question_with_build(self):
        """Questions with 'build' are action requests."""
        assert is_pure_question("What do I need to build?") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
