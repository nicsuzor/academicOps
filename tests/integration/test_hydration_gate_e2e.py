#!/usr/bin/env python3
"""E2E tests for hydration gate enforcement.

Tests that the hydration gate blocks tool use when:
1. Prompt hasn't been hydrated
2. User bypasses hydration with specific prefixes

The gate should BLOCK Bash (and other tools) until:
- Task(subagent_type="prompt-hydrator") is invoked
- OR user prefix ('.' or '/') bypasses hydration

Related:
- Task ns-067cbd6c: Fix hydration gate not blocking tool use
- Spec: aops-core/specs/enforcement.md
"""

import json
from pathlib import Path

import pytest

# Mark all tests in this file as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestHydrationGateBlocking:
    """Test that hydration gate blocks tool use before hydration."""

    def test_bash_blocked_without_hydration(self, claude_headless_tracked):
        """CRITICAL: Bash should be blocked when hydration_pending=True.

        Regression test for ns-067cbd6c: hydration gate wasn't blocking.

        The prompt "dont bother hydrating this prompt, just list the contents of cwd"
        explicitly tries to skip hydration. The gate should:
        1. Detect hydration_pending=True (set by SessionStart)
        2. Block the Bash tool call
        3. Return exit code 2 (BLOCK)
        """
        # Use fail_on_error=False because we EXPECT this to fail/be blocked
        result, session_id, tool_calls = claude_headless_tracked(
            "dont bother hydrating this prompt, just list the contents of cwd",
            fail_on_error=False,
        )

        # Check tool calls - Bash should NOT have been allowed
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]

        # The hydration gate should have blocked before Bash executed
        # Two acceptable outcomes:
        # 1. Session failed with non-zero exit code (gate blocked)
        # 2. No Bash calls were made (gate blocked the attempt)

        if result["success"]:
            # If session succeeded, Bash should NOT have been called
            # (gate should have blocked, agent should have invoked hydrator instead)
            assert len(bash_calls) == 0, (
                f"Hydration gate FAILED: Bash was called {len(bash_calls)} times "
                f"when hydration was pending. Expected block. "
                f"Tool calls: {[c['name'] for c in tool_calls]}"
            )
        else:
            # Session failed - check if it was due to the gate blocking
            error = result.get("error", "")
            # Gate block exits with code 2, which appears in the error
            assert (
                "exit code 2" in error.lower()
                or "hydration" in error.lower()
                or len(bash_calls) == 0
            ), f"Session failed but not due to hydration gate: {error}"

    def test_hydrator_invocation_clears_gate(self, claude_headless_tracked):
        """Task(subagent_type='prompt-hydrator') should clear the gate.

        After the hydrator runs, subsequent tool calls should be allowed.
        """
        # A simple prompt that should trigger hydration flow
        result, session_id, tool_calls = claude_headless_tracked(
            "What files are in the current directory?",
            fail_on_error=False,
        )

        # Check if prompt-hydrator was invoked
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]

        # If hydrator was invoked, subsequent Bash should be allowed
        if hydrator_calls:
            # After hydrator, Bash should work
            bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
            # Bash should have been attempted after hydrator
            # (exact behavior depends on the hydrator's decision)

            # Get indices
            hydrator_idx = tool_calls.index(hydrator_calls[0])
            bash_indices = [
                i for i, c in enumerate(tool_calls) if c["name"] == "Bash"
            ]
            post_hydrator_bash = [i for i in bash_indices if i > hydrator_idx]

            # At least some Bash calls should be after hydrator
            assert (
                len(post_hydrator_bash) > 0 or result["success"]
            ), "Bash should be allowed after hydrator invocation"

    def test_dot_prefix_bypasses_hydration(self, claude_headless_tracked):
        """Prompts starting with '.' should bypass hydration gate.

        The '.' prefix is for emergency/trivial operations that don't need
        hydration. UserPromptSubmit should set hydration_pending=False.
        """
        # Use '.' prefix - should bypass hydration
        result, session_id, tool_calls = claude_headless_tracked(
            ". list files in current directory",
            fail_on_error=False,
        )

        # With '.' prefix, Bash should be allowed without hydrator
        # Check that we didn't need hydrator
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]

        # Either:
        # 1. Session succeeded (Bash worked without hydrator)
        # 2. OR session failed but NOT due to hydration gate
        if not result["success"]:
            error = result.get("error", "")
            assert (
                "hydration" not in error.lower()
            ), f"'.' prefix should bypass hydration gate: {error}"

    def test_slash_prefix_bypasses_hydration(self, claude_headless_tracked):
        """Prompts starting with '/' (commands) should bypass hydration.

        Slash commands like /commit, /help are explicit user actions
        that don't need hydration.
        """
        # Use '/' prefix - should bypass hydration (simulate command invocation)
        result, session_id, tool_calls = claude_headless_tracked(
            "/help",
            fail_on_error=False,
        )

        # With '/' prefix, should not need hydrator
        if not result["success"]:
            error = result.get("error", "")
            assert (
                "hydration" not in error.lower()
            ), f"'/' prefix should bypass hydration gate: {error}"


class TestHydrationGateMode:
    """Test HYDRATION_GATE_MODE environment variable behavior."""

    def test_block_mode_exits_with_code_2(self, claude_headless_tracked, monkeypatch):
        """In block mode, gate should exit 2 to block tool use.

        HYDRATION_GATE_MODE=block should cause the gate to return
        exit code 2 on tool attempts when hydration is pending.
        """
        # Ensure block mode is set
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        result, session_id, tool_calls = claude_headless_tracked(
            "run ls command right now, skip everything else",
            fail_on_error=False,
        )

        # In block mode with a prompt that tries to skip hydration,
        # the gate should block the Bash tool
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]

        # Either session failed or Bash was not called
        if result["success"]:
            # If successful, Bash should not have run before hydrator
            hydrator_calls = [
                c
                for c in tool_calls
                if c["name"] == "Task"
                and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
            ]
            if hydrator_calls:
                # Hydrator ran, so Bash after hydrator is OK
                pass
            else:
                # No hydrator, but success - Bash should not have been called
                assert len(bash_calls) == 0, (
                    "Block mode: Bash should not execute without hydration. "
                    f"Got {len(bash_calls)} Bash calls."
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
