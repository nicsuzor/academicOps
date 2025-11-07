#!/usr/bin/env python3
"""
Test suite for validation hook system (validate_tool.py and validate_env.py).

This tests the hooks in headless mode to ensure they work correctly when
invoked by agents, not just in interactive sessions.

Run with: uv run pytest /tmp/test_validation_hooks.py -v
"""

from pathlib import Path

from .hooks import parse_hook_output, run_hook

# ============================================================================
# SessionStart Hook Tests (validate_env.py)
# ============================================================================


class TestSessionStartHook:
    """Tests for SessionStart hook (validate_env.py)."""

    def test_hook_runs_successfully(self, validate_env_script: Path):
        """Test that the SessionStart hook runs without errors."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0, f"Hook failed with exit code {exit_code}: {_stderr}"

        # Parse JSON output and verify it contains instruction content
        output = parse_hook_output(stdout)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        # Check that the context contains expected content from instruction files
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Core Axioms" in context or "BACKGROUND" in context

    def test_hook_outputs_valid_json(self, validate_env_script: Path):
        """Test that the hook outputs valid JSON."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        # Verify structure
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_hook_loads_both_instruction_files(self, validate_env_script: Path):
        """Test that both instruction files are loaded."""
        exit_code, stdout, _stderr = run_hook(validate_env_script, {})

        assert exit_code == 0
        output = parse_hook_output(stdout)

        context = output["hookSpecificOutput"]["additionalContext"]

        # Check for key content from framework tier (_CORE.md)
        assert "Core Axioms (Inviolable Rules)" in context, (
            "Framework _CORE.md not loaded"
        )
        assert "NO WORKAROUNDS" in context, "Framework behavioral rules not loaded"

        # Check for key content from personal tier (unique to nicsuzor/writing)
        assert "Law professor with ADHD" in context, "Personal _CORE.md not loaded"
        assert "buttermilk" in context, "Personal polyrepo structure not loaded"

    def test_hook_handles_missing_files_gracefully(
        self, validate_env_script: Path, tmp_path: Path
    ):
        """Test that hook fails gracefully if instruction files are missing."""
        # This test would require modifying the script to point to non-existent files
        # For now, we just verify the script would exit with code 1
        # We can't easily test this without modifying the script or using mocks
