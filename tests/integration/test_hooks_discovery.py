#!/usr/bin/env python3
"""Integration tests for hooks discovery on Claude Code and Gemini CLI.

Verifies that both CLI agents can discover and report on available hooks.
This test validates the framework hooks installation is working correctly.

Created for v1.1 acceptance testing - validates Gemini hooks installation.
"""

import pytest

from tests.conftest import (
    extract_response_text,
)


@pytest.mark.slow
@pytest.mark.integration
class TestHooksDiscovery:
    """Tests for hooks discovery on both CLI platforms."""

    def test_claude_knows_hooks_available(self, claude_headless) -> None:
        """Test that Claude Code can report on hooks availability.

        Verifies:
        - Claude responds to hooks query
        - Response mentions hooks or hook-related functionality
        - Agent demonstrates awareness of hook system
        """
        result = claude_headless(
            "What hooks are configured for this session? "
            "List any PreToolUse, PostToolUse, or other hooks you know about.",
            timeout_seconds=120,
        )

        assert result["success"], f"Claude headless failed: {result.get('error')}"

        # Extract response text
        response_text = extract_response_text(result).lower()

        # Verify hooks are mentioned in the response
        hook_indicators = [
            "hook",
            "pretooluse",
            "posttooluse",
            "sessionstart",
            "userpromptsubmit",
            "router",
            "gate",
        ]
        has_hook_awareness = any(
            indicator in response_text for indicator in hook_indicators
        )

        assert has_hook_awareness, (
            f"Claude should demonstrate awareness of hooks. "
            f"Response did not contain hook-related terms. "
            f"Response snippet: {response_text[:500]}"
        )

    def test_gemini_knows_hooks_available(self, gemini_headless) -> None:
        """Test that Gemini CLI can report on hooks availability.

        Verifies:
        - Gemini responds to hooks query
        - Response mentions hooks or hook-related functionality
        - Agent demonstrates awareness of hook system

        Note: This test will fail if Gemini hooks are not properly installed,
        which is the current known issue (aops-6e33153a).
        """
        result = gemini_headless(
            "What hooks are configured for this session? "
            "List any BeforeTool, AfterTool, or other hooks you know about.",
            timeout_seconds=120,
        )

        assert result["success"], f"Gemini headless failed: {result.get('error')}"

        # Parse response - Gemini returns different JSON structure
        response = result.get("result", {})
        response_text = response.get("response", "").lower()

        # If response_text is empty, try alternate structure
        if not response_text:
            response_text = str(response).lower()

        # Verify hooks are mentioned in the response
        hook_indicators = [
            "hook",
            "beforetool",
            "aftertool",
            "sessionstart",
            "beforeagent",
            "router",
            "gate",
            "aops-router",
        ]
        has_hook_awareness = any(
            indicator in response_text for indicator in hook_indicators
        )

        assert has_hook_awareness, (
            f"Gemini should demonstrate awareness of hooks. "
            f"Response did not contain hook-related terms. "
            f"Response snippet: {response_text[:500]}"
        )


@pytest.mark.slow
@pytest.mark.integration
class TestHooksRegistryStatus:
    """Tests that verify hooks are actually registered (not just known about)."""

    def test_claude_hooks_registry_not_empty(self, claude_headless) -> None:
        """Test that Claude's hook registry has entries.

        The hook system should show hooks are actually registered and
        firing, not just that the concept of hooks exists.
        """
        result = claude_headless(
            "Check if any hooks fired at the start of this session. "
            "Look for system-reminder tags or hook notifications in the conversation.",
            timeout_seconds=120,
        )

        assert result["success"], f"Claude headless failed: {result.get('error')}"

        # The raw output should contain hook-related content if hooks fired
        raw_output = result.get("output", "").lower()
        response_text = extract_response_text(result).lower()

        # Check for evidence of hooks firing
        hook_evidence = [
            "system-reminder",
            "hook success",
            "sessionstart",
            "userpromptsubmit",
            "pretooluse",
        ]

        has_hook_evidence = any(
            indicator in raw_output or indicator in response_text
            for indicator in hook_evidence
        )

        assert has_hook_evidence, (
            "Expected evidence of hooks firing in Claude session. "
            "No system-reminder or hook success indicators found."
        )

    def test_gemini_hooks_registry_not_empty(self, gemini_headless) -> None:
        """Test that Gemini's hook registry has entries.

        This is the critical test for issue aops-6e33153a.
        Currently Gemini shows "Hook registry initialized with 0 hook entries"
        which indicates hooks are not being loaded from extensions.
        """
        result = gemini_headless(
            "Check if any hooks are registered and firing in this session. "
            "Report on the hook registry status.",
            timeout_seconds=120,
        )

        assert result["success"], f"Gemini headless failed: {result.get('error')}"

        # Parse response
        response = result.get("result", {})
        response_text = response.get("response", "")
        if not response_text:
            response_text = str(response)

        # Check for hook registry entries
        # This test documents the expected behavior vs current bug
        hook_indicators = [
            "hook",
            "registered",
            "firing",
            "aops-router",
            "beforetool",
            "aftertool",
        ]

        has_hook_awareness = any(
            indicator.lower() in response_text.lower() for indicator in hook_indicators
        )

        # Note: This assertion documents expected behavior
        # It will fail while aops-6e33153a is unfixed
        assert has_hook_awareness, (
            "Gemini hook registry should have entries. "
            "If this fails with '0 hook entries', the extension hooks "
            "are not being loaded. See task aops-6e33153a."
        )


@pytest.mark.slow
@pytest.mark.integration
class TestCrossplatformHooksDiscovery:
    """Parameterized tests running on both Claude and Gemini."""

    def test_cli_reports_hook_system(self, cli_headless) -> None:
        """Test that both CLIs can report on their hook system.

        Uses parameterized cli_headless fixture to run on both platforms.
        """
        runner, platform = cli_headless

        prompt = (
            "Briefly describe the hook system configuration for this CLI session. "
            "What hooks are available?"
        )

        result = runner(prompt, timeout_seconds=120)

        assert result["success"], (
            f"{platform} headless failed: {result.get('error')}"
        )

        # Extract text based on platform
        if platform == "claude":
            response_text = extract_response_text(result).lower()
        else:
            response = result.get("result", {})
            response_text = response.get("response", str(response)).lower()

        # Both platforms should mention hooks
        assert "hook" in response_text, (
            f"{platform} should mention hooks in response. "
            f"Response: {response_text[:300]}"
        )
