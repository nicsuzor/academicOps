#!/usr/bin/env python3
"""Unit tests for hooks/criteria_gate.py - Criteria Gate PreToolUse hook.

Tests cover:
- Bash allowlist logic (read-only commands bypass gate)
- Gate file validation (existence, expiry)
- Session-specific gate file paths
- Blocking behavior for gated tools
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBashAllowlist:
    """Test is_allowed_bash function."""

    def test_git_status_allowed(self):
        """git status should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("git status") is True

    def test_git_diff_allowed(self):
        """git diff should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("git diff") is True
        assert is_allowed_bash("git diff HEAD~1") is True

    def test_git_log_allowed(self):
        """git log should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("git log") is True
        assert is_allowed_bash("git log --oneline -5") is True

    def test_ls_allowed(self):
        """ls command should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("ls") is True
        assert is_allowed_bash("ls -la") is True
        assert is_allowed_bash("ls /tmp") is True

    def test_cat_allowed(self):
        """cat command should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("cat file.txt") is True

    def test_grep_allowed(self):
        """grep command should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("grep pattern file.txt") is True

    def test_rg_allowed(self):
        """rg (ripgrep) command should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("rg pattern") is True

    def test_pwd_allowed(self):
        """pwd command should be allowed without gate."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("pwd") is True

    def test_gate_file_creation_allowed(self):
        """echo date command for gate file creation should be allowed."""
        from hooks.criteria_gate import is_allowed_bash

        # The exact pattern used to create gate files
        assert is_allowed_bash('echo "$(date -Iseconds)" > /tmp/gate') is True

    def test_rm_blocked(self):
        """rm command should be blocked (not in allowlist)."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("rm file.txt") is False
        assert is_allowed_bash("rm -rf /") is False

    def test_mv_blocked(self):
        """mv command should be blocked."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("mv a b") is False

    def test_python_script_blocked(self):
        """Running Python scripts should be blocked."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("python script.py") is False
        assert is_allowed_bash("python3 script.py") is False

    def test_uv_run_python_c_allowed(self):
        """uv run python -c for quick checks should be allowed."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("uv run python -c 'print(1)'") is True

    def test_chained_commands_blocked(self):
        """Commands with && should be blocked (could hide destructive ops)."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("ls && rm file") is False
        assert is_allowed_bash("git status && git push --force") is False

    def test_semicolon_commands_blocked(self):
        """Commands with ; should be blocked."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("ls; rm file") is False

    def test_or_commands_blocked(self):
        """Commands with || should be blocked."""
        from hooks.criteria_gate import is_allowed_bash

        assert is_allowed_bash("ls || rm file") is False

    def test_pipe_allowed(self):
        """Pipes should be allowed for read-only command chains."""
        from hooks.criteria_gate import is_allowed_bash

        # Pipes are OK because they don't execute multiple commands sequentially
        # They just stream output - git diff | head is fine
        assert is_allowed_bash("git diff | head") is True
        assert is_allowed_bash("ls | grep pattern") is True


class TestGateFilePath:
    """Test get_gate_file function."""

    def test_gate_file_uses_session_id(self):
        """Gate file path should include session ID."""
        from hooks.criteria_gate import get_gate_file

        path = get_gate_file("abc123")
        assert "abc123" in str(path)
        assert path.name == "claude-criteria-gate-abc123"

    def test_gate_file_in_tmp(self):
        """Gate file should be in /tmp directory."""
        from hooks.criteria_gate import get_gate_file

        path = get_gate_file("test-session")
        assert str(path).startswith("/tmp")


class TestGateValidation:
    """Test is_gate_valid function."""

    def test_missing_gate_file_invalid(self):
        """Non-existent gate file should be invalid."""
        from hooks.criteria_gate import is_gate_valid

        assert is_gate_valid("nonexistent-session-12345") is False

    def test_valid_gate_file(self):
        """Gate file with recent timestamp should be valid."""
        from hooks.criteria_gate import GATE_PREFIX, is_gate_valid

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create gate file with current timestamp
            session_id = "test-valid-gate"
            gate_file = Path(tmpdir) / f"{GATE_PREFIX}{session_id}"
            now = datetime.now(timezone.utc)
            gate_file.write_text(now.isoformat())

            # Patch GATE_DIR to use temp directory
            with patch("hooks.criteria_gate.GATE_DIR", Path(tmpdir)):
                assert is_gate_valid(session_id) is True

    def test_expired_gate_file_invalid(self):
        """Gate file older than 30 minutes should be invalid."""
        from hooks.criteria_gate import GATE_PREFIX, is_gate_valid

        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-expired-gate"
            gate_file = Path(tmpdir) / f"{GATE_PREFIX}{session_id}"

            # Create gate file with timestamp 31 minutes ago
            old_time = datetime.now(timezone.utc) - timedelta(minutes=31)
            gate_file.write_text(old_time.isoformat())

            with patch("hooks.criteria_gate.GATE_DIR", Path(tmpdir)):
                assert is_gate_valid(session_id) is False

    def test_corrupted_gate_file_invalid(self):
        """Gate file with invalid content should be invalid."""
        from hooks.criteria_gate import GATE_PREFIX, is_gate_valid

        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-corrupted-gate"
            gate_file = Path(tmpdir) / f"{GATE_PREFIX}{session_id}"
            gate_file.write_text("not a valid timestamp")

            with patch("hooks.criteria_gate.GATE_DIR", Path(tmpdir)):
                assert is_gate_valid(session_id) is False

    def test_empty_gate_file_invalid(self):
        """Empty gate file should be invalid."""
        from hooks.criteria_gate import GATE_PREFIX, is_gate_valid

        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test-empty-gate"
            gate_file = Path(tmpdir) / f"{GATE_PREFIX}{session_id}"
            gate_file.write_text("")

            with patch("hooks.criteria_gate.GATE_DIR", Path(tmpdir)):
                assert is_gate_valid(session_id) is False


class TestHookBehavior:
    """Test main hook behavior via subprocess."""

    def test_blocks_edit_without_gate(self):
        """Edit tool should be blocked when no gate file exists."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Edit",
            "tool_input": {},
            "session_id": "test-no-gate-edit",
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        # Exit code 2 = block
        assert result.returncode == 2
        assert "BLOCKED" in result.stderr

    def test_blocks_write_without_gate(self):
        """Write tool should be blocked when no gate file exists."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Write",
            "tool_input": {},
            "session_id": "test-no-gate-write",
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        assert result.returncode == 2
        assert "BLOCKED" in result.stderr

    def test_blocks_destructive_bash_without_gate(self):
        """Destructive Bash commands should be blocked when no gate file exists."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /tmp/foo"},
            "session_id": "test-no-gate-bash",
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        assert result.returncode == 2
        assert "BLOCKED" in result.stderr

    def test_allows_read_tool_without_gate(self):
        """Read tool should be allowed (not a gated tool)."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
            "session_id": "test-read-allowed",
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        # Exit code 0 = allow
        assert result.returncode == 0
        # Output should be empty JSON (no modification)
        assert json.loads(result.stdout) == {}

    def test_allows_git_status_without_gate(self):
        """git status should be allowed even without gate (in allowlist)."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
            "session_id": "test-git-status-allowed",
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_allows_edit_with_valid_gate(self):
        """Edit should be allowed when valid gate file exists."""
        import subprocess

        from hooks.criteria_gate import GATE_PREFIX
        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        session_id = "test-edit-with-gate"

        # Create valid gate file
        gate_file = Path("/tmp") / f"{GATE_PREFIX}{session_id}"
        now = datetime.now(timezone.utc)
        gate_file.write_text(now.isoformat())

        try:
            input_data = {
                "tool_name": "Edit",
                "tool_input": {},
                "session_id": session_id,
            }

            result = subprocess.run(
                ["python", str(hooks_dir / "criteria_gate.py")],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd=hooks_dir,
            )

            assert result.returncode == 0
            assert json.loads(result.stdout) == {}
        finally:
            gate_file.unlink(missing_ok=True)

    def test_fail_closed_no_session_id(self):
        """Hook should block (fail-closed) when session_id is missing."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()
        input_data = {
            "tool_name": "Edit",
            "tool_input": {},
            # No session_id
        }

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        # Should block (fail-closed)
        assert result.returncode == 2
        assert "BLOCKED" in result.stderr
        assert "session_id" in result.stderr.lower()

    def test_fail_closed_invalid_json(self):
        """Hook should block (fail-closed) on invalid JSON input."""
        import subprocess

        from tests.paths import get_hooks_dir

        hooks_dir = get_hooks_dir()

        result = subprocess.run(
            ["python", str(hooks_dir / "criteria_gate.py")],
            input="not valid json",
            capture_output=True,
            text=True,
            cwd=hooks_dir,
        )

        # Should block (fail-closed)
        assert result.returncode == 2
        assert "BLOCKED" in result.stderr
