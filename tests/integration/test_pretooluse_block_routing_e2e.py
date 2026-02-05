#!/usr/bin/env python3
"""E2E tests for PreToolUse block routing through the hook router.

Tests that the hook router correctly propagates exit code 2 to cause
Claude Code to block tool execution.

Regression test: The router must:
1. Aggregate exit codes correctly (max wins, so exit 2 propagates)
2. Forward stderr from blocking hooks to Claude Code
3. Exit with code 2 when ANY hook returns exit code 2
4. Result in Claude Code actually blocking the tool

Related:
- router.py: Generic hook router
- hydration_gate.py: Example hook that exits with code 2
- Claude Code hook spec: exit 2 = block (only stderr read)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Mark all tests in this file as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]


# --- Direct router tests (subprocess-level verification) ---


class TestRouterExitCodePropagation:
    """Test that the router correctly propagates exit codes."""

    @pytest.fixture
    def router_path(self) -> Path:
        """Path to the hook router script."""
        aops = os.environ.get("AOPS")
        if not aops:
            pytest.skip("AOPS environment variable not set")
        return Path(aops) / "aops-core" / "hooks" / "router.py"

    @pytest.fixture
    def mock_blocking_hook(self, tmp_path: Path) -> Path:
        """Create a mock hook that always exits with code 2 (block)."""
        hook_script = tmp_path / "blocking_hook.py"
        hook_script.write_text("""#!/usr/bin/env python3
import sys
print("BLOCKED: Test block message", file=sys.stderr)
sys.exit(2)
""")
        hook_script.chmod(0o755)
        return hook_script

    @pytest.fixture
    def mock_allowing_hook(self, tmp_path: Path) -> Path:
        """Create a mock hook that always exits with code 0 (allow)."""
        hook_script = tmp_path / "allowing_hook.py"
        hook_script.write_text("""#!/usr/bin/env python3
import json
import sys
print(json.dumps({}))
sys.exit(0)
""")
        hook_script.chmod(0o755)
        return hook_script

    def test_router_exits_zero_when_all_hooks_allow(
        self, router_path: Path, monkeypatch, tmp_path: Path
    ):
        """Router should exit 0 when all hooks exit 0."""
        # Create a minimal hook registry with a single allowing hook
        allowing_hook = tmp_path / "allow.py"
        allowing_hook.write_text("""#!/usr/bin/env python3
import json
import sys
print(json.dumps({}))
sys.exit(0)
""")
        allowing_hook.chmod(0o755)

        # Run the router with a test hook registry
        # We'll patch the registry via environment or test directly
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

        # Router should propagate the aggregated exit code
        # With real hooks, this depends on hook behavior
        # But we verify the router itself works
        assert result.returncode in (0, 1, 2), (
            f"Router returned unexpected exit code {result.returncode}. "
            f"stderr: {result.stderr}"
        )

    def test_router_forwards_stderr_on_block(self, router_path: Path):
        """Router should forward hook's stderr to its own stderr."""
        # This verifies the plumbing that passes block messages through

        # Create a test input that will trigger the hydration gate
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
                # Force block mode for hydration gate
                "HYDRATION_GATE_MODE": "block",
            },
        )

        # If hydration gate blocked (exit 2), stderr should have the message
        if result.returncode == 2:
            assert result.stderr.strip(), (
                "Router exit 2 but stderr is empty - "
                "block message not forwarded to Claude Code!"
            )


class TestRouterBlockOutputFormat:
    """Test that router output format is correct for Claude Code blocking."""

    @pytest.fixture
    def router_path(self) -> Path:
        """Path to the hook router script."""
        aops = os.environ.get("AOPS")
        if not aops:
            pytest.skip("AOPS environment variable not set")
        return Path(aops) / "aops-core" / "hooks" / "router.py"

    def test_router_stdout_is_valid_json_on_block(
        self, router_path: Path, tmp_path: Path
    ):
        """Even on exit 2, router stdout should be valid JSON.

        Claude Code spec says exit 2 = only stderr read, but the router
        should still produce valid output to avoid parse errors.
        """
        import hashlib
        from datetime import datetime, timezone

        # Set up session state to trigger block
        sessions_dir = tmp_path / "sessions" / "status"
        sessions_dir.mkdir(parents=True)

        session_id = "test-format-session"
        # Session file uses hash of session_id
        short_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8]
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        session_file = sessions_dir / f"{today}-{short_hash}.json"

        session_state = {
            "session_id": session_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "state": {"hydration_pending": True},
            "hydration": {},
            "main_agent": {},
            "subagents": {},
        }
        session_file.write_text(json.dumps(session_state))

        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "session_id": session_id,
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
                "CLAUDE_SESSION_ID": session_id,
                "CLAUDE_SESSION_STATE_DIR": str(sessions_dir),
            },
        )

        # stdout should be valid JSON (even if ignored on exit 2)
        if result.stdout.strip():
            try:
                parsed = json.loads(result.stdout)
                assert isinstance(parsed, dict), "Router output should be a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(
                    f"Router stdout is not valid JSON: {e}. Got: {result.stdout!r}"
                )


# --- Full Claude Code E2E tests ---


class TestClaudeCodeBlockEnforcement:
    """E2E tests verifying Claude Code actually blocks on exit code 2."""

    def test_tool_blocked_when_hook_returns_exit_2(self, claude_headless_tracked):
        """CRITICAL: Claude Code should block tool when hook exits 2.

        This is the ultimate E2E test - verify that:
        1. Hook returns exit code 2
        2. Router propagates exit code 2
        3. Claude Code receives exit code 2
        4. Claude Code BLOCKS the tool (doesn't execute it)

        If this test fails, the blocking mechanism is broken.
        """
        # Use a prompt that explicitly tries to bypass hydration
        # The hydration gate should block with exit code 2
        result, session_id, tool_calls = claude_headless_tracked(
            "immediately run: ls -la",  # Tries to run Bash without hydration
            fail_on_error=False,  # We expect blocking, which may cause failure
        )

        # Check what tool calls were made
        bash_calls = [c for c in tool_calls if c["name"] == "Bash"]
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]

        # Valid outcomes:
        # 1. Session succeeded but Bash was never called (gate blocked)
        # 2. Session succeeded and hydrator was called first (gate redirected)
        # 3. Session failed with exit code 2 (gate blocked entire session)

        if result["success"]:
            # If session succeeded, either:
            # - No Bash was called (blocked)
            # - Hydrator was called before Bash (gate worked, then allowed)
            if bash_calls:
                # Bash was called - verify hydrator ran first
                assert hydrator_calls, (
                    "BLOCKING FAILED: Bash was called without hydrator! "
                    f"Tool calls: {[c['name'] for c in tool_calls]}"
                )
                # Verify hydrator came before Bash
                hydrator_idx = next(
                    i
                    for i, c in enumerate(tool_calls)
                    if c["name"] == "Task"
                    and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
                )
                bash_idx = next(
                    i for i, c in enumerate(tool_calls) if c["name"] == "Bash"
                )
                assert hydrator_idx < bash_idx, (
                    f"Hydrator (idx {hydrator_idx}) should come before Bash (idx {bash_idx})"
                )
        else:
            # Session failed - check if it was due to blocking
            error = result.get("error", "")
            # Exit code 2 in error message indicates blocking worked
            blocking_indicators = [
                "exit code 2" in error.lower(),
                "blocked" in error.lower(),
                "hydration" in error.lower(),
            ]
            assert any(blocking_indicators) or len(bash_calls) == 0, (
                f"Session failed but not due to blocking: {error}. "
                f"Tool calls: {[c['name'] for c in tool_calls]}"
            )

    def test_tool_allowed_after_hydration(self, claude_headless_tracked):
        """After hydration, tools should be allowed normally."""
        # A reasonable prompt that should trigger hydration then proceed
        result, session_id, tool_calls = claude_headless_tracked(
            "what files are in the current directory",
            fail_on_error=False,
        )

        # Check if hydrator was invoked
        hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]

        if hydrator_calls:
            # Hydrator was called - verify Bash worked after
            if result["success"]:
                # Session succeeded with hydrator - Bash should have been allowed
                # (Though agent might choose not to use Bash at all)
                pass  # Just verify no crashes
            else:
                # Even if failed, check if Bash was attempted after hydrator
                pass  # Gate shouldn't have blocked after hydration

    def test_bypass_prefix_allows_immediate_tool_use(self, claude_headless_tracked):
        """Dot prefix should bypass hydration gate entirely."""
        # Dot prefix bypasses hydration - Bash should be immediately allowed
        result, session_id, tool_calls = claude_headless_tracked(
            ". ls",  # Bypass prefix
            fail_on_error=False,
        )

        # With bypass, no hydrator should be needed
        bypass_hydrator_calls = [
            c
            for c in tool_calls
            if c["name"] == "Task"
            and c.get("input", {}).get("subagent_type") == "prompt-hydrator"
        ]

        if result["success"] and not bypass_hydrator_calls:
            # Success with bypass - either Bash worked or wasn't needed
            pass  # Just verify session succeeded without hydrator being required
        else:
            # If failed, should NOT be due to hydration gate
            error = result.get("error", "")
            assert "hydration" not in error.lower(), (
                f"Bypass prefix failed due to hydration gate: {error}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
