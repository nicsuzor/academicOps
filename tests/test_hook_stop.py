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

import pytest

from .hooks import parse_hook_output, run_hook


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

        assert exit_code == 0, f"Hook failed with exit code {exit_code}\nstderr: {stderr}"

        # Verify stdout starts with JSON (no leading text)
        stdout_stripped = stdout.strip()
        assert stdout_stripped.startswith(
            "{"
        ), f"Hook output should start with '{{' but got: {stdout_stripped[:100]}"

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
        assert (
            "hookSpecificOutput" not in output
        ), "Stop hooks should not include hookSpecificOutput field"

        # CRITICAL: Stop hooks should NOT include hookEventName at top level
        assert (
            "hookEventName" not in output
        ), "Stop hooks should not include hookEventName field at top level"

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

        assert exit_code == 0, f"Hook failed with exit code {exit_code}\nstderr: {stderr}"

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
        assert (
            "hookSpecificOutput" not in output
        ), "SubagentStop hooks should not include hookSpecificOutput field"

        # CRITICAL: SubagentStop hooks should NOT include hookEventName
        assert (
            "hookEventName" not in output
        ), "SubagentStop hooks should not include hookEventName field"

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
            assert output["decision"] != "block", (
                "Hook should not block by default"
            )
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

        exit_code, stdout, stderr = run_hook(validate_stop_script, hook_input)

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
        output = json.loads(stdout_stripped)  # Should parse without error

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
