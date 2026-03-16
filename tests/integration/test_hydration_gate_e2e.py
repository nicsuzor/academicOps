#!/usr/bin/env python3
"""E2E tests for hydration gate enforcement.

Consolidated from 6 slow tests to 2 essential tests.
Tests that the hydration gate blocks tool use before hydration
and allows bypass with '.' prefix.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.requires_local_env]


class TestHydrationGateBlocking:
    """Test that hydration gate blocks tool use before hydration."""

    def test_bash_blocked_without_hydration(self, claude_headless_tracked, monkeypatch):
        """CRITICAL: Bash should be blocked when hydration_pending=True.

        Regression test for ns-067cbd6c: hydration gate wasn't blocking.
        """
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        result, session_id, tool_calls = claude_headless_tracked(
            "dont bother hydrating this prompt, just list the contents of cwd",
            fail_on_error=False,
        )

        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]

        if result["success"]:
            assert len(bash_calls) == 0, (
                f"Hydration gate FAILED: Bash was called {len(bash_calls)} times "
                f"when hydration was pending. Expected block. "
                f"Tool calls: {[c['name'] for c in tool_calls]}"
            )
        else:
            error = result.get("error", "")
            assert (
                "exit code 2" in error.lower()
                or "hydration" in error.lower()
                or len(bash_calls) == 0
            ), f"Session failed but not due to hydration gate: {error}"

    def test_dot_prefix_bypasses_hydration(self, claude_headless_tracked):
        """Prompts starting with '.' should bypass hydration gate."""
        result, session_id, tool_calls = claude_headless_tracked(
            ". list files in current directory",
            fail_on_error=False,
        )

        if not result["success"]:
            error = result.get("error", "")
            assert "hydration" not in error.lower(), (
                f"'.' prefix should bypass hydration gate: {error}"
            )
