"""Tests for hooks/overdue_enforcement.py - Overdue compliance enforcement.

TDD Phase 5: Overdue Check (PreToolUse)
Tests hard-blocking of mutating tools when compliance check is overdue.
"""

from __future__ import annotations

from pathlib import Path


class TestOverdueThreshold:
    """Test threshold-based blocking."""

    def test_under_threshold_allows_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Under threshold (< 7 tool calls), mutating tools allowed."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 5,  # Under threshold
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is None  # No block

    def test_at_threshold_blocks_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """At threshold (>= 7 tool calls), mutating tools blocked."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 7,  # At threshold
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert result["decision"] == "block"

    def test_over_threshold_blocks_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Over threshold (> 7 tool calls), mutating tools blocked."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,  # Over threshold
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Write", {"file_path": "/test.py", "content": "test"})
        assert result is not None
        assert result["decision"] == "block"


class TestToolCategories:
    """Test tool categorization (mutating vs read-only)."""

    def test_edit_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Edit tool is mutating and blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert result["decision"] == "block"

    def test_write_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Write tool is mutating and blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Write", {"file_path": "/test.py", "content": "x"})
        assert result is not None
        assert result["decision"] == "block"

    def test_bash_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Bash tool is mutating and blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Bash", {"command": "rm -rf /"})
        assert result is not None
        assert result["decision"] == "block"

    def test_read_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Read tool is read-only and NOT blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Read", {"file_path": "/test.py"})
        # Read-only gets soft reminder, not block
        assert result is None or result.get("decision") != "block"

    def test_glob_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Glob tool is read-only and NOT blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Glob", {"pattern": "**/*.py"})
        assert result is None or result.get("decision") != "block"

    def test_grep_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Grep tool is read-only and NOT blocked when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Grep", {"pattern": "def foo"})
        assert result is None or result.get("decision") != "block"


class TestMissingState:
    """Test behavior when custodiet state is missing."""

    def test_no_state_allows_all(self, tmp_path: Path, monkeypatch) -> None:
        """Missing state allows all tools (first session, no baseline)."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("CLAUDE_CWD", "/nonexistent/project")

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is None  # No enforcement without state


class TestBlockReason:
    """Test block reason messages."""

    def test_block_includes_reason(self, tmp_path: Path, monkeypatch) -> None:
        """Block response includes reason message."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert "reason" in result
        assert (
            "compliance" in result["reason"].lower()
            or "overdue" in result["reason"].lower()
        )

    def test_block_suggests_custodiet(self, tmp_path: Path, monkeypatch) -> None:
        """Block response suggests spawning custodiet."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert "custodiet" in result["reason"].lower()


class TestSoftReminder:
    """Test soft reminder for read-only tools when overdue."""

    def test_readonly_gets_reminder_when_overdue(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Read-only tools get soft reminder (not block) when overdue."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Read", {"file_path": "/test.py"})
        # Should return reminder or None, never block
        if result is not None:
            assert result.get("decision") != "block"
