#!/usr/bin/env python3
"""
Test suite for Stop and SubagentStop hooks (validate_stop.py).

This tests the hooks in headless mode to ensure they work correctly when
invoked by agents, not just in interactive sessions.

Run with: uv run pytest tests/test_hook_stop.py -v
"""

import json
import subprocess
from pathlib import Path

from .hooks import run_hook

# ============================================================================
# Stop Hook Tests (validate_stop.py)
# ============================================================================


class TestStopHook:
    """Tests for Stop/SubagentStop hooks (validate_stop.py)."""

    def test_stop_hook_outputs_valid_json_schema(self, validate_stop_script: Path):
        """
        Test that Stop hook outputs valid JSON matching Claude Code's expected schema.

        Stop hook schema per https://gist.github.com/FrancisBourre/50dca37124ecc43eaf08328cdcccdb34:
        {
          "decision": "block" | null,  // optional
          "reason": "string"           // required if decision = "block"
        }

        Empty {} is valid (allows stop to proceed)
        """
        hook_input = {
            "session_id": "test-session",
            "hook_event": "Stop",
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, (
            f"Hook failed with exit code {exit_code}\nstderr: {stderr}"
        )

        # Verify stdout starts with JSON (no leading text)
        stdout_stripped = stdout.strip()
        assert stdout_stripped.startswith("{"), (
            f"Hook output should start with '{{' but got: {stdout_stripped[:100]}"
        )

        # Verify it's valid JSON
        output = json.loads(stdout_stripped)

        # Validate schema: if decision is present, validate it
        if "decision" in output:
            assert output["decision"] in ["block", None], (
                f"'decision' must be 'block' or null, got: {output['decision']}"
            )
            # If decision is "block", reason must be present
            if output["decision"] == "block":
                assert "reason" in output, "'reason' is required when decision='block'"
                assert isinstance(output["reason"], str), "'reason' must be a string"

        # If reason is present without decision, that's also valid
        if "reason" in output:
            assert isinstance(output["reason"], str), "'reason' must be a string"

        # CRITICAL: Stop hooks should NOT include hookSpecificOutput
        assert "hookSpecificOutput" not in output, (
            "Stop hooks should not include hookSpecificOutput field"
        )

        # CRITICAL: Stop hooks should NOT include hookEventName at top level
        assert "hookEventName" not in output, (
            "Stop hooks should not include hookEventName field at top level"
        )

    def test_subagent_stop_hook_outputs_valid_json_schema(
        self, validate_stop_script: Path
    ):
        """
        Test that SubagentStop hook outputs valid JSON schema.

        SubagentStop uses the same schema as Stop hook.
        """
        hook_input = {
            "session_id": "test-session",
            "hook_event": "SubagentStop",
            "subagent": "test-agent",
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, (
            f"Hook failed with exit code {exit_code}\nstderr: {stderr}"
        )

        # Parse and validate JSON
        stdout_stripped = stdout.strip()
        assert stdout_stripped.startswith("{"), (
            f"Hook output should start with '{{' but got: {stdout_stripped[:100]}"
        )

        output = json.loads(stdout_stripped)

        # Validate schema: same as Stop hook
        if "decision" in output:
            assert output["decision"] in ["block", None], (
                f"'decision' must be 'block' or null, got: {output['decision']}"
            )
            if output["decision"] == "block":
                assert "reason" in output, "'reason' is required when decision='block'"
                assert isinstance(output["reason"], str), "'reason' must be a string"

        if "reason" in output:
            assert isinstance(output["reason"], str), "'reason' must be a string"

        # CRITICAL: SubagentStop hooks should NOT include hookSpecificOutput
        assert "hookSpecificOutput" not in output, (
            "SubagentStop hooks should not include hookSpecificOutput field"
        )

        # CRITICAL: SubagentStop hooks should NOT include hookEventName
        assert "hookEventName" not in output, (
            "SubagentStop hooks should not include hookEventName field"
        )

    def test_stop_hook_allows_by_default(self, validate_stop_script: Path):
        """Test that Stop hook allows execution by default (no block)."""
        hook_input = {"session_id": "test-session", "hook_event": "Stop"}

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"
        output = json.loads(stdout.strip())

        # When valid, hook should either:
        # - Return empty {} (allows by default)
        # - Return {"decision": null} (explicitly allow)
        # - Not include "decision": "block"
        if "decision" in output:
            assert output["decision"] != "block", "Hook should not block by default"
        # If no decision field, that's also valid (allows by default)

    def test_stop_hook_json_is_clean(self, validate_stop_script: Path):
        """
        Test that Stop hook outputs ONLY JSON to stdout, no extra text.

        This catches issues where stderr messages leak into stdout.
        """
        hook_input = {"session_id": "test-session", "hook_event": "Stop"}

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"

        # Verify no extra text before or after JSON
        stdout_stripped = stdout.strip()

        # Should start with {
        assert stdout_stripped.startswith("{"), (
            f"stdout should start with '{{', got: {stdout_stripped[:50]}"
        )

        # Should end with }
        assert stdout_stripped.endswith("}"), (
            f"stdout should end with '}}', got: ...{stdout_stripped[-50:]}"
        )

        # Should be parseable as a single JSON object
        output = json.loads(stdout_stripped)

        # Re-serialize and compare to ensure no extra whitespace/text
        reserialized = json.dumps(output)
        assert len(stdout_stripped) <= len(reserialized) + 100, (
            "stdout contains significantly more characters than expected JSON"
        )

    def test_stop_hook_handles_missing_hook_event(self, validate_stop_script: Path):
        """Test that hook handles missing hook_event field gracefully."""
        hook_input = {
            "session_id": "test-session",
            # Missing hook_event
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        # Should still work - hook defaults to "Unknown"
        assert exit_code == 0, f"Hook should handle missing hook_event: {stderr}"
        output = json.loads(stdout.strip())
        # Output may be empty {} (allows by default)
        # Should not block
        if "decision" in output:
            assert output["decision"] != "block"

    def test_stop_hook_handles_extra_fields(self, validate_stop_script: Path):
        """Test that hook handles extra fields in input gracefully."""
        hook_input = {
            "session_id": "test-session",
            "hook_event": "Stop",
            "extra_field": "should be ignored",
            "another_field": 123,
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook should handle extra fields: {stderr}"
        output = json.loads(stdout.strip())
        # Output may be empty {} (allows by default)
        # Should not block
        if "decision" in output:
            assert output["decision"] != "block"

    def test_stop_hook_logs_to_tmp(self, validate_stop_script: Path):
        """Test that hook creates debug log in /tmp."""
        hook_input = {
            "session_id": "test-session-logging",
            "hook_event": "Stop",
        }

        exit_code, _stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"

        # Check that stderr mentions logging
        assert "hook executed" in stderr.lower() or "log" in stderr.lower(), (
            f"stderr should mention logging, got: {stderr}"
        )

    def test_subagent_stop_hook_with_result(self, validate_stop_script: Path):
        """Test SubagentStop hook with subagent_result field."""
        hook_input = {
            "session_id": "test-session",
            "hook_event": "SubagentStop",
            "subagent": "code-review",
            "subagent_result": {
                "status": "success",
                "output": "Code looks good!",
            },
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"
        output = json.loads(stdout.strip())

        # Output may be empty {} (allows by default)
        # Should not block
        if "decision" in output:
            assert output["decision"] != "block"
        assert "hookSpecificOutput" not in output

    def test_stop_hook_invalid_json_input(self, validate_stop_script: Path):
        """Test that hook handles invalid JSON input gracefully."""
        result = subprocess.run(
            ["uv", "run", "python", str(validate_stop_script)],
            check=False,
            input="not valid json",
            capture_output=True,
            text=True,
        )

        # Should exit with error code 2
        assert result.returncode == 2, (
            f"Hook should exit with code 2 for invalid JSON, got {result.returncode}"
        )
        assert "Invalid JSON" in result.stderr or "JSONDecodeError" in result.stderr, (
            f"stderr should mention JSON error, got: {result.stderr}"
        )


# ============================================================================
# Integration Tests
# ============================================================================


class TestStopHookIntegration:
    """Integration tests for Stop hook system."""

    def test_stop_hook_matches_claude_code_spec(self, validate_stop_script: Path):
        """
        Test that Stop hook output exactly matches Claude Code specification.

        Per https://gist.github.com/FrancisBourre/50dca37124ecc43eaf08328cdcccdb34

        Schema:
        {
          "decision": "block" | null,  // optional
          "reason": "string"           // required if decision = "block"
        }

        NO hookSpecificOutput field!
        """
        hook_input = {"hook_event": "Stop"}

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"
        output = json.loads(stdout.strip())

        # Check all valid fields for Stop hook
        valid_fields = {"decision", "reason"}
        output_fields = set(output.keys())

        # Ensure no invalid fields
        invalid_fields = output_fields - valid_fields
        assert not invalid_fields, (
            f"Stop hook output contains invalid fields: {invalid_fields}. "
            f"Valid fields are: {valid_fields}"
        )

        # All fields are optional - empty {} is valid
        # But if decision="block", reason must be present
        if output.get("decision") == "block":
            assert "reason" in output, "'reason' required when decision='block'"

    def test_multiple_stop_hooks_are_independent(self, validate_stop_script: Path):
        """Test that multiple hook invocations don't interfere with each other."""
        hook_input_1 = {"session_id": "session-1", "hook_event": "Stop"}
        hook_input_2 = {"session_id": "session-2", "hook_event": "SubagentStop"}

        exit_code_1, stdout_1, _ = run_hook(validate_stop_script, hook_input_1)
        exit_code_2, stdout_2, _ = run_hook(validate_stop_script, hook_input_2)

        assert exit_code_1 == 0
        assert exit_code_2 == 0

        output_1 = json.loads(stdout_1.strip())
        output_2 = json.loads(stdout_2.strip())

        # Both should have valid structure (may be empty {})
        # Neither should block by default
        if "decision" in output_1:
            assert output_1["decision"] != "block"
        if "decision" in output_2:
            assert output_2["decision"] != "block"
        assert "hookSpecificOutput" not in output_1
        assert "hookSpecificOutput" not in output_2


# ============================================================================
# Edge Cases
# ============================================================================


class TestStopHookEdgeCases:
    """Test edge cases and error handling for Stop hooks."""

    def test_stop_hook_with_empty_input(self, validate_stop_script: Path):
        """Test that hook handles empty JSON object input."""
        exit_code, stdout, stderr = run_hook(validate_stop_script, {})

        # Should succeed with defaults
        assert exit_code == 0, f"Hook should handle empty input: {stderr}"
        output = json.loads(stdout.strip())
        # Output may be empty {} (allows by default)
        # Should not block
        if "decision" in output:
            assert output["decision"] != "block"

    def test_stop_hook_with_unicode_input(self, validate_stop_script: Path):
        """Test that hook handles unicode in input."""
        hook_input = {
            "session_id": "test-unicode-☃️",
            "hook_event": "Stop",
            "subagent": "agent-名前",
        }

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0, f"Hook should handle unicode: {stderr}"
        output = json.loads(stdout.strip())
        # Output may be empty {} (allows by default)
        # Should not block
        if "decision" in output:
            assert output["decision"] != "block"

    def test_stop_hook_stdout_stderr_separation(self, validate_stop_script: Path):
        """
        Test that JSON goes to stdout and human messages go to stderr.

        This is critical - Claude Code expects ONLY JSON on stdout.
        """
        hook_input = {"hook_event": "Stop"}

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

        assert exit_code == 0

        # stdout should ONLY contain JSON
        stdout_stripped = stdout.strip()
        json.loads(stdout_stripped)  # Should parse without error

        # stderr should contain human-readable messages
        assert stderr.strip(), "stderr should contain debug/status messages"
        assert "hook executed" in stderr.lower() or "✓" in stderr, (
            f"stderr should contain status message, got: {stderr}"
        )

        # Verify stdout doesn't contain status messages
        assert "hook executed" not in stdout.lower(), (
            "stdout should not contain status messages"
        )
        assert "✓" not in stdout, "stdout should not contain status symbols"


# ============================================================================
# Request Scribe Stop Hook Tests (request_scribe_stop.py)
# ============================================================================


class TestRequestScribeStopHook:
    """Tests for request_scribe_stop.py - the actual Stop hook we use."""

    def test_first_stop_blocks_and_creates_flag(self, request_scribe_stop_script: Path):
        """
        Test that first Stop blocks with decision='block' and creates state flag.

        This is the core behavior: on first stop, block and instruct agent
        to invoke end-of-session subagent.
        """
        import time
        from pathlib import Path

        # Use unique session_id to avoid conflicts with other tests
        session_id = f"test-first-stop-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "Stop",
        }

        # Ensure no flag exists before test
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        if state_file.exists():
            state_file.unlink()

        exit_code, stdout, stderr = run_hook(request_scribe_stop_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"

        # Parse output
        output = json.loads(stdout.strip())

        # Verify it blocks
        assert output.get("decision") == "block", (
            f"First stop should block, got: {output}"
        )

        # Verify reason mentions end-of-session
        assert "reason" in output, "Blocked decision must have reason"
        assert "end-of-session" in output["reason"].lower(), (
            f"Reason should mention end-of-session, got: {output['reason']}"
        )

        # Verify state flag was created
        assert state_file.exists(), f"State flag should be created at {state_file}"

        # Cleanup
        if state_file.exists():
            state_file.unlink()

    def test_second_stop_allows_when_flag_exists(
        self, request_scribe_stop_script: Path
    ):
        """
        Test that second Stop allows (returns {}) when flag exists.

        After end-of-session subagent is invoked, the second Stop should allow
        to prevent infinite loop.
        """
        import time
        from pathlib import Path

        session_id = f"test-second-stop-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "Stop",
        }

        # Create flag to simulate first stop already happened
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        state_file.touch()

        try:
            exit_code, stdout, stderr = run_hook(request_scribe_stop_script, hook_input)

            assert exit_code == 0, f"Hook failed: {stderr}"

            # Parse output
            output = json.loads(stdout.strip())

            # Should allow (empty {} or no "block" decision)
            if "decision" in output:
                assert output["decision"] != "block", (
                    f"Second stop should allow, got: {output}"
                )
            # Empty {} is also valid (allows by default)

        finally:
            # Cleanup
            if state_file.exists():
                state_file.unlink()

    def test_third_stop_still_allows(self, request_scribe_stop_script: Path):
        """
        Test that third Stop still allows when flag exists.

        Flag persists until UserPromptSubmit, so multiple stops should all allow.
        """
        import time
        from pathlib import Path

        session_id = f"test-third-stop-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "Stop",
        }

        # Create flag
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        state_file.touch()

        try:
            # Second stop
            exit_code, stdout, stderr = run_hook(request_scribe_stop_script, hook_input)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block"

            # Third stop - flag still exists
            assert state_file.exists(), "Flag should persist across stops"

            exit_code, stdout, _stderr = run_hook(
                request_scribe_stop_script, hook_input
            )
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block", "Third stop should still allow"

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_invalid_json_allows_failsafe(self, request_scribe_stop_script: Path):
        """
        Test that invalid JSON input allows (fail-safe behavior).

        If JSON parsing fails, hook should allow to prevent breaking agent.
        """
        result = subprocess.run(
            ["uv", "run", "python", str(request_scribe_stop_script)],
            check=False,
            input="not valid json",
            capture_output=True,
            text=True,
        )

        # Should exit successfully (fail-safe)
        assert result.returncode == 0, (
            f"Invalid JSON should be handled gracefully, got exit code {result.returncode}"
        )

        # Should output valid empty JSON (allows)
        output = json.loads(result.stdout.strip())
        if "decision" in output:
            assert output["decision"] != "block", (
                "Invalid JSON should allow (fail-safe)"
            )

    def test_subagent_stop_event_works_same_as_stop(
        self, request_scribe_stop_script: Path
    ):
        """
        Test that SubagentStop event uses same logic as Stop.

        Both hooks use request_scribe_stop.py, so behavior should be identical.
        """
        import time
        from pathlib import Path

        session_id = f"test-subagent-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "SubagentStop",
            "subagent": "test-agent",
        }

        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        if state_file.exists():
            state_file.unlink()

        try:
            # First SubagentStop should block
            exit_code, stdout, stderr = run_hook(request_scribe_stop_script, hook_input)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block"
            assert state_file.exists()

            # Second SubagentStop should allow
            exit_code, stdout, _stderr = run_hook(
                request_scribe_stop_script, hook_input
            )
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block"

        finally:
            if state_file.exists():
                state_file.unlink()


# ============================================================================
# UserPromptSubmit Flag Cleanup Tests
# ============================================================================


class TestUserPromptSubmitFlagCleanup:
    """Tests for flag cleanup in log_userpromptsubmit.py."""

    def test_cleanup_removes_flag(self, log_userpromptsubmit_script: Path):
        """
        Test that UserPromptSubmit hook removes end-of-session flag.

        This resets state for next user turn.
        """
        import time
        from pathlib import Path

        session_id = f"test-cleanup-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "UserPromptSubmit",
        }

        # Create flag to simulate previous stop cycle
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        state_file.touch()
        assert state_file.exists(), "Setup: flag should exist before cleanup"

        # Run UserPromptSubmit hook
        exit_code, stdout, stderr = run_hook(log_userpromptsubmit_script, hook_input)

        assert exit_code == 0, f"Hook failed: {stderr}"

        # Verify flag was removed
        assert not state_file.exists(), (
            f"Flag should be removed by UserPromptSubmit, but still exists at {state_file}"
        )

        # Output should be valid JSON (continue execution)
        json.loads(stdout.strip())
        # Empty {} is valid

    def test_cleanup_succeeds_when_flag_missing(
        self, log_userpromptsubmit_script: Path
    ):
        """
        Test that cleanup succeeds silently when flag doesn't exist.

        Should not error if there's no flag to clean up.
        """
        import time
        from pathlib import Path

        session_id = f"test-no-flag-{int(time.time() * 1000)}"
        hook_input = {
            "session_id": session_id,
            "hook_event": "UserPromptSubmit",
        }

        # Ensure no flag exists
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")
        if state_file.exists():
            state_file.unlink()

        # Run UserPromptSubmit hook
        exit_code, stdout, stderr = run_hook(log_userpromptsubmit_script, hook_input)

        # Should succeed silently
        assert exit_code == 0, f"Hook should succeed even when no flag exists: {stderr}"

        # Output should be valid JSON
        json.loads(stdout.strip())

    def test_cleanup_with_missing_session_id(
        self, log_userpromptsubmit_script: Path, request_scribe_stop_script: Path
    ):
        """
        Test cleanup with missing session_id defaults to 'unknown'.

        Combined test that:
        1. Creates flag via stop hook with missing session_id
        2. Verifies flag created with session_id='unknown'
        3. Cleanup via UserPromptSubmit removes the flag

        Combined to avoid race conditions with parallel test execution.
        """
        from pathlib import Path

        # Create flag with 'unknown' session_id via stop hook
        state_file = Path("/tmp/claude_end_of_session_requested_unknown.flag")

        # Cleanup any existing flag
        if state_file.exists():
            state_file.unlink()

        try:
            # Step 1: Stop hook with missing session_id creates flag
            stop_input = {
                "hook_event": "Stop",
                # Missing session_id - should default to 'unknown'
            }

            exit_code, stdout, stderr = run_hook(request_scribe_stop_script, stop_input)
            assert exit_code == 0, f"Stop hook failed: {stderr}"
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block", "First stop should block"
            assert state_file.exists(), (
                "Flag should be created with session_id='unknown'"
            )

            # Step 2: UserPromptSubmit hook removes flag
            cleanup_input = {
                "hook_event": "UserPromptSubmit",
                # Also missing session_id - should default to 'unknown'
            }

            exit_code, stdout, stderr = run_hook(
                log_userpromptsubmit_script, cleanup_input
            )
            assert exit_code == 0, f"UserPromptSubmit hook failed: {stderr}"

            # Verify flag was removed
            assert not state_file.exists(), (
                "Flag with session_id='unknown' should be removed by UserPromptSubmit"
            )
        finally:
            if state_file.exists():
                state_file.unlink()


# ============================================================================
# Full Lifecycle Integration Tests
# ============================================================================


class TestStopHookFullCycle:
    """Integration tests for complete Stop hook lifecycle."""

    def test_full_stop_cycle_with_cleanup(
        self, request_scribe_stop_script: Path, log_userpromptsubmit_script: Path
    ):
        """
        Test complete cycle: Stop → Stop → UserPromptSubmit → Stop.

        Workflow:
        1. First Stop → blocks (creates flag)
        2. Second Stop → allows (flag exists)
        3. UserPromptSubmit → cleanup (removes flag)
        4. Third Stop → blocks again (flag gone, restart cycle)
        """
        import time
        from pathlib import Path

        session_id = f"test-full-cycle-{int(time.time() * 1000)}"
        state_file = Path(f"/tmp/claude_end_of_session_requested_{session_id}.flag")

        # Cleanup any existing flag
        if state_file.exists():
            state_file.unlink()

        try:
            # Step 1: First Stop → blocks
            hook_input = {"session_id": session_id, "hook_event": "Stop"}
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block", "First stop should block"
            assert state_file.exists(), "First stop should create flag"

            # Step 2: Second Stop → allows
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block", "Second stop should allow"
            assert state_file.exists(), "Flag should still exist"

            # Step 3: UserPromptSubmit → cleanup
            hook_input_submit = {
                "session_id": session_id,
                "hook_event": "UserPromptSubmit",
            }
            exit_code, stdout, _ = run_hook(
                log_userpromptsubmit_script, hook_input_submit
            )
            assert exit_code == 0
            assert not state_file.exists(), "UserPromptSubmit should remove flag"

            # Step 4: Third Stop → blocks again (restart cycle)
            hook_input = {"session_id": session_id, "hook_event": "Stop"}
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block", (
                "After cleanup, next stop should block again"
            )
            assert state_file.exists(), "Stop should create flag again"

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_multiple_sessions_independent(self, request_scribe_stop_script: Path):
        """
        Test that different session IDs have independent state.

        One session blocking shouldn't affect another session.
        """
        import time
        from pathlib import Path

        session_1 = f"test-session-1-{int(time.time() * 1000)}"
        session_2 = f"test-session-2-{int(time.time() * 1000)}"

        state_file_1 = Path(f"/tmp/claude_end_of_session_requested_{session_1}.flag")
        state_file_2 = Path(f"/tmp/claude_end_of_session_requested_{session_2}.flag")

        # Cleanup
        for f in [state_file_1, state_file_2]:
            if f.exists():
                f.unlink()

        try:
            # Session 1: First stop blocks
            hook_input_1 = {"session_id": session_1, "hook_event": "Stop"}
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input_1)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block"
            assert state_file_1.exists()

            # Session 2: First stop also blocks (independent)
            hook_input_2 = {"session_id": session_2, "hook_event": "Stop"}
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input_2)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            assert output.get("decision") == "block", (
                "Session 2 should block independently of session 1"
            )
            assert state_file_2.exists()

            # Session 1: Second stop allows
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input_1)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block"

            # Session 2: Second stop allows (independent)
            exit_code, stdout, _ = run_hook(request_scribe_stop_script, hook_input_2)
            assert exit_code == 0
            output = json.loads(stdout.strip())
            if "decision" in output:
                assert output["decision"] != "block"

        finally:
            for f in [state_file_1, state_file_2]:
                if f.exists():
                    f.unlink()
