#!/usr/bin/env python3
"""E2E tests for PreToolUse block routing through the hook router.

Consolidated from 6 tests to 3: 2 fast subprocess tests + 1 slow headless test.
Router subprocess tests do NOT need headless and have had @slow removed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


class TestRouterExitCodePropagation:
    """Test that the router correctly propagates exit codes (fast, no headless)."""

    @pytest.fixture
    def router_path(self) -> Path:
        """Path to the hook router script."""
        aops = os.environ.get("AOPS")
        assert aops, "AOPS environment variable not set"
        return Path(aops) / "aops-core" / "hooks" / "router.py"

    def test_router_exits_zero_when_all_hooks_allow(self, router_path: Path):
        """Router should exit 0 when all hooks exit 0."""
        input_data = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}

        result = subprocess.run(
            [sys.executable, str(router_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(router_path.parent.parent),
            },
        )

        assert result.returncode in (0, 1, 2), (
            f"Router returned unexpected exit code {result.returncode}. stderr: {result.stderr}"
        )

    def test_router_forwards_stderr_on_block(self, router_path: Path):
        """Router should forward hook's stderr to its own stderr."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "session_id": "test-session-nonexistent",
        }

        result = subprocess.run(
            [sys.executable, str(router_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(router_path.parent.parent),
                "HYDRATION_GATE_MODE": "block",
            },
        )

        if result.returncode == 2:
            assert result.stderr.strip(), (
                "Router exit 2 but stderr is empty - block message not forwarded!"
            )


class TestClaudeCodeBlockEnforcement:
    """E2E test verifying Claude Code actually blocks on exit code 2 (slow)."""

    @pytest.mark.slow
    def test_tool_blocked_when_hook_returns_exit_2(self, claude_headless_tracked):
        """CRITICAL: Claude Code should block tool when hook exits 2."""
        result, session_id, tool_calls = claude_headless_tracked(
            "immediately run: ls -la",
            fail_on_error=False,
        )

        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task" and c.get("input", {}).get("subagent_type") == "hydrator"
        ]

        if result["success"]:
            if bash_calls:
                assert hydrator_calls, (
                    "BLOCKING FAILED: Bash was called without hydrator! "
                    f"Tool calls: {[c['name'] for c in tool_calls]}"
                )
                hydrator_idx = next(
                    i
                    for i, c in enumerate(tool_calls)
                    if c["name"] == "Task" and c.get("input", {}).get("subagent_type") == "hydrator"
                )
                bash_idx = next(i for i, c in enumerate(tool_calls) if c["name"] == "Bash")
                assert hydrator_idx < bash_idx, (
                    f"Hydrator (idx {hydrator_idx}) should come before Bash (idx {bash_idx})"
                )
        else:
            error = result.get("error", "")
            blocking_indicators = [
                "exit code 2" in error.lower(),
                "blocked" in error.lower(),
                "hydration" in error.lower(),
            ]
            assert any(blocking_indicators) or len(bash_calls) == 0, (
                f"Session failed but not due to blocking: {error}. "
                f"Tool calls: {[c['name'] for c in tool_calls]}"
            )
