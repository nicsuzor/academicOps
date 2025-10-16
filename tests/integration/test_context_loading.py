#!/usr/bin/env python3
"""
Integration tests for context loading via SessionStart hook.

Validates that bot/agents/_CORE.md and docs/agents/INSTRUCTIONS.md
are properly injected and accessible to agents.

Run with: uv run pytest tests/integration/test_context_loading.py -v
"""

import pytest

# Mark all tests in this file as slow (integration tests invoking Claude CLI)
pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]


class TestUserContextLoading:
    """Test that user-specific context from docs/agents/INSTRUCTIONS.md loads."""

    def test_user_identification(self, claude_headless):
        """Verify assistant knows the repository owner without file access."""
        result = claude_headless(
            "Without using any tools, whose repository is this? Just the name."
        )

        assert result["success"], f"Failed: {result['error']}"
        # Check for "Nicolas Suzor" or "Nic"
        result_lower = result["result"].lower()
        assert "nic" in result_lower or "suzor" in result_lower, (
            f"Expected user name in response, got: {result['result']}"
        )

    def test_project_awareness(self, claude_headless):
        """Verify assistant knows about major projects without file access."""
        result = claude_headless(
            "Without using any tools, what is Buttermilk? One sentence."
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention research/academic/framework/python
        assert any(
            word in result_lower
            for word in ["research", "academic", "framework", "python", "computational"]
        ), f"Expected project description, got: {result['result']}"

    def test_workflow_preferences(self, claude_headless):
        """Verify assistant knows user's ADHD accommodations without file access."""
        result = claude_headless(
            "Without using any tools, does this user have any specific communication preferences?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention ADHD or concise communication
        assert (
            "adhd" in result_lower
            or "concise" in result_lower
            or "brief" in result_lower
        ), f"Expected ADHD/communication preferences, got: {result['result']}"

    def test_primary_project_priority(self, claude_headless):
        """Verify assistant knows Buttermilk is P1 infrastructure."""
        result = claude_headless(
            "Without using any tools, what is the highest priority project?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention Buttermilk as critical/P1/infrastructure
        assert "buttermilk" in result_lower, (
            f"Expected Buttermilk mentioned as priority, got: {result['result']}"
        )


class TestCoreInstructionsLoading:
    """Test that core framework instructions from bot/agents/_CORE.md load."""

    def test_fail_fast_philosophy(self, claude_headless):
        """Verify assistant knows about fail-fast philosophy without file access."""
        result = claude_headless(
            "Without using any tools, what is the fail-fast philosophy in this codebase?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention no fallbacks, no defaults, or immediate errors
        assert any(
            phrase in result_lower
            for phrase in [
                "no fallback",
                "no default",
                "immediate",
                "exit",
                "halt",
                ".get(",
            ]
        ), f"Expected fail-fast description, got: {result['result']}"

    def test_axiom_awareness(self, claude_headless):
        """Verify assistant knows about core axioms without file access."""
        result = claude_headless(
            "Without using any tools, name 2-3 core axioms for this framework."
        )

        assert result["success"], f"Failed: {result['error']}"
        # Should mention some axioms from _CORE.md
        result_lower = result["result"].lower()
        # Check for key axiom themes
        axiom_indicators = [
            "data bound",
            "isolation",
            "fail-fast",
            "self-document",
            "dry",
            "explicit",
        ]
        matches = sum(1 for indicator in axiom_indicators if indicator in result_lower)
        assert matches >= 2, (
            f"Expected at least 2 axiom themes mentioned, got: {result['result']}"
        )

    def test_repository_structure_awareness(self, claude_headless):
        """Verify assistant knows about bot/ being public."""
        result = claude_headless(
            "Without using any tools, which directory in this repo is public on GitHub?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention bot/ or academicOps
        assert "bot" in result_lower or "academicops" in result_lower, (
            f"Expected mention of bot/ directory, got: {result['result']}"
        )


class TestContextPriority:
    """Test that user context takes priority over framework context."""

    def test_user_projects_over_framework(self, claude_headless):
        """Verify assistant prioritizes user's actual work over framework development."""
        result = claude_headless(
            "Without using any tools, if I say 'help me with my research', "
            "what would you assume I need help with?"
        )

        assert result["success"], f"Failed: {result['error']}"
        # User context emphasizes actual research projects (Buttermilk, automod, etc.)
        # over framework development (academicOps)
        result_lower = result["result"].lower()

        # Good responses mention research projects or ask for clarification
        # Bad responses assume framework/bot development
        good_indicators = [
            "buttermilk",
            "automod",
            "research",
            "project",
            "ask",
            "which",
            "clarif",
        ]
        bad_indicators = ["academicops", "framework development", "bot"]

        has_good = any(indicator in result_lower for indicator in good_indicators)
        has_only_bad = not has_good and any(
            indicator in result_lower for indicator in bad_indicators
        )

        assert has_good or not has_only_bad, (
            f"Expected research-focused or clarifying response, got: {result['result']}"
        )


class TestContextCompleteness:
    """Test that all expected context sections are loaded."""

    def test_knows_execution_environment(self, claude_headless):
        """Verify assistant knows to use 'uv run python' without file access."""
        result = claude_headless(
            "Without using any tools, how should I run Python scripts in this repo?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention uv run
        assert "uv run" in result_lower or "uv" in result_lower, (
            f"Expected 'uv run' in response, got: {result['result']}"
        )

    def test_knows_project_submodules(self, claude_headless):
        """Verify assistant knows about project structure (submodules)."""
        result = claude_headless(
            "Without using any tools, where are the research projects located in this repo?"
        )

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()
        # Should mention projects/ directory or submodules
        assert "projects/" in result_lower or "submodule" in result_lower, (
            f"Expected mention of projects/ or submodules, got: {result['result']}"
        )


class TestQuickSmokeTest:
    """Single fast test for debugging context loading issues."""

    def test_whose_repository_smoke_test(self, claude_headless):
        """
        Quick smoke test: Can answer basic question about repository owner.

        This is the minimal test to verify context loaded at all.
        If this fails, SessionStart hook likely didn't inject context.
        """
        result = claude_headless("Without using any tools, whose repository is this?")

        assert result["success"], f"Failed: {result['error']}"
        result_lower = result["result"].lower()

        # Must mention user name
        assert "nic" in result_lower or "suzor" in result_lower, (
            f"SMOKE TEST FAILED - Context may not be loaded. Got: {result['result']}"
        )


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
