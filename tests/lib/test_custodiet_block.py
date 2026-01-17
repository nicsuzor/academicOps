"""Tests for aops-core/scripts/custodiet_block.py CLI script.

Tests the CLI wrapper that sets custodiet block flags via session_state.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


# Get the script path
SCRIPT_PATH = Path(__file__).parents[2] / "aops-core" / "scripts" / "custodiet_block.py"


class TestCustodietBlockCLI:
    """Test custodiet_block.py CLI behavior."""

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
        """Script sets custodiet block when called with valid args."""
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

    def test_custodiet_disabled_message(self, tmp_path: Path) -> None:
        """Script shows 'not enforced' message when CUSTODIET_DISABLED=1."""
        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        env = {
            "CLAUDE_SESSION_STATE_DIR": str(state_dir),
            "CUSTODIET_DISABLED": "1",
        }
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "test-session-456",
                "Test violation",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, **env},
        )

        assert result.returncode == 0
        assert "not enforced" in result.stdout.lower() or "CUSTODIET_DISABLED" in result.stdout

    def test_custodiet_enabled_message(self, tmp_path: Path) -> None:
        """Script shows standard message when custodiet is enabled."""
        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        # Explicitly unset CUSTODIET_DISABLED
        env = subprocess.os.environ.copy()
        env["CLAUDE_SESSION_STATE_DIR"] = str(state_dir)
        env.pop("CUSTODIET_DISABLED", None)

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "test-session-789",
                "Test violation",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        # Should NOT say "not enforced"
        assert "not enforced" not in result.stdout.lower()


class TestCustodietBlockIntegration:
    """Integration tests verifying block is actually persisted."""

    def test_block_is_persisted_to_session_state(self, tmp_path: Path) -> None:
        """Verify the block is written to session state file."""
        import json

        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        # Run from a known directory to get predictable project folder
        env = {**subprocess.os.environ, "CLAUDE_SESSION_STATE_DIR": str(state_dir)}

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

        # Find the session state file (it's in a subdirectory structure)
        session_files = list(state_dir.rglob("session-state.json"))
        assert len(session_files) == 1, f"Expected 1 session file, found {len(session_files)}: {session_files}"

        # Read and verify the state directly
        state = json.loads(session_files[0].read_text())
        assert state["state"]["custodiet_blocked"] is True
        assert state["state"]["custodiet_block_reason"] == "Policy violation reason"

    def test_block_recorded_even_when_disabled(self, tmp_path: Path) -> None:
        """Block is recorded even when CUSTODIET_DISABLED=1 (just not enforced)."""
        import json

        state_dir = tmp_path / "claude-session"
        state_dir.mkdir()

        env = {
            **subprocess.os.environ,
            "CLAUDE_SESSION_STATE_DIR": str(state_dir),
            "CUSTODIET_DISABLED": "1",
        }

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "disabled-test-session",
                "Recorded but not enforced",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0

        # Find and verify the session state file
        session_files = list(state_dir.rglob("session-state.json"))
        assert len(session_files) == 1

        state = json.loads(session_files[0].read_text())
        assert state["state"]["custodiet_blocked"] is True
        assert state["state"]["custodiet_block_reason"] == "Recorded but not enforced"
