"""Tests for aops-core/scripts/compliance_block.py CLI script.

Tests the CLI wrapper that sets compliance block flags via session_state.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Get the script path
SCRIPT_PATH = Path(__file__).parents[2] / "aops-core" / "scripts" / "compliance_block.py"


class TestEnforcerBlockCLI:
    """Test compliance_block.py CLI behavior (enforcer gate block flag)."""

    def test_missing_args_returns_error(self) -> None:
        """Script returns exit code 1 when called without args."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Usage:" in result.stderr

    def test_missing_reason_arg_returns_error(self) -> None:
        """Script returns exit code 1 when called with only session_id."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "test-session"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Usage:" in result.stderr

    def test_valid_args_sets_block(self, tmp_path: Path, monkeypatch) -> None:
        """Script sets enforcer block when called with valid args."""
        # Set up isolated session state directory
        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        # Run the script with isolated state directory
        env = {"CLAUDE_SESSION_STATE_DIR": str(state_dir)}
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "test-session-123",
                "Agent violated policy X",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, **env},
        )

        assert result.returncode == 0
        assert "Block" in result.stdout
        assert "test-session-123" in result.stdout


class TestEnforcerBlockIntegration:
    """Integration tests verifying block is actually persisted."""

    def test_block_is_persisted_to_session_state(self, tmp_path: Path) -> None:
        """Verify the block is written to session state file."""
        import json

        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        # Run from a known directory to get predictable project folder
        env = {**subprocess.os.environ, "AOPS_SESSION_STATE_DIR": str(state_dir)}

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "persist-test-session",
                "Policy violation reason",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(tmp_path),  # Run from tmp_path for predictable project folder
        )

        assert result.returncode == 0

        # Find the session state file (named YYYYMMDD-HH-<hash>.json)
        session_files = list(state_dir.rglob("*.json"))
        assert len(session_files) == 1, (
            f"Expected 1 session file, found {len(session_files)}: {session_files}"
        )

        # Read and verify the state directly
        state = json.loads(session_files[0].read_text())
        # <!-- NS: these tests need to be refactored for the new pydantic objects. -->
        assert state["gates"]["enforcer"]["blocked"] is True
        assert state["gates"]["enforcer"]["block_reason"] == "Policy violation reason"
