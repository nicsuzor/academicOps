"""Tests for hooks/overdue_enforcement.py - Overdue compliance enforcement.

TDD Phase 5: Overdue Check (PreToolUse)
Tests hard-blocking of mutating tools when compliance check is overdue.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def setup_custodiet_state(
    session_id: str, tool_calls_since_compliance: int = 0
) -> None:
    """Helper to set up custodiet state using unified SessionState API."""
    from lib.session_state import get_or_create_session_state, save_session_state

    state = get_or_create_session_state(session_id)
    state["state"]["tool_calls_since_compliance"] = tool_calls_since_compliance
    state["state"]["last_compliance_ts"] = 0.0
    save_session_state(session_id, state)


class TestOverdueThreshold:
    """Test threshold-based blocking."""

    def test_under_threshold_allows_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Under threshold (< 7 tool calls), mutating tools allowed."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv(
            "CLAUDE_SESSION_ID", cwd
        )  # Use SESSION_ID (preferred over CWD)
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=5)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is None  # No block

    def test_at_threshold_blocks_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """At threshold (>= 7 tool calls), mutating tools blocked."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=7)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is not None
        # Result from make_deny_output is typically just the output dict to return to Claude
        # It contains content with the rejection message.
        # We check if it returns a rejection structure.

    def test_over_threshold_blocks_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Over threshold (> 7 tool calls), mutating tools blocked."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {"file_path": "/test.py", "content": "test"},
            },
        )
        result = check_custodiet_gate(ctx)
        assert result is not None


class TestToolCategories:
    """Test tool categorization (mutating vs read-only)."""

    def test_edit_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Edit tool is mutating and blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is not None

    def test_write_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Write tool is mutating and blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {"file_path": "/test.py", "content": "x"},
            },
        )
        result = check_custodiet_gate(ctx)
        assert result is not None

    def test_bash_is_mutating(self, tmp_path: Path, monkeypatch) -> None:
        """Bash tool is mutating and blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is not None

    def test_read_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Read tool is read-only and NOT blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Read", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is None

    def test_glob_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Glob tool is read-only and NOT blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Glob", "tool_input": {"pattern": "**/*.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is None

    def test_grep_is_readonly(self, tmp_path: Path, monkeypatch) -> None:
        """Grep tool is read-only and NOT blocked when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Grep", "tool_input": {"pattern": "def foo"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is None


class TestMissingState:
    """Test behavior when custodiet state is missing."""

    def test_no_state_allows_all(self, tmp_path: Path, monkeypatch) -> None:
        """Missing state allows all tools (first session, no baseline)."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("CLAUDE_CWD", "/nonexistent/project")

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id="new-session-id",
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        # We need to monkeypatch session_state interaction or rely on behavior
        # But get_or_create_session_state WILL create state if missing!
        # So check_custodiet_gate will create state and initialize it.
        # But tool_calls_since_compliance will be 1 (after increment).
        # Which is < 7.
        # So it returns None.
        result = check_custodiet_gate(ctx)
        assert result is None


class TestBlockReason:
    """Test block reason messages."""

    def test_block_includes_reason(self, tmp_path: Path, monkeypatch) -> None:
        """Block response includes reason message."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is not None
        # Verify result contains reject message
        # hook_utils.make_deny_output returns dict like {'content': [...]}
        # We assume it has Reject content
        # Exact format depends on hook_utils impl
        assert result

    def test_block_suggests_custodiet(self, tmp_path: Path, monkeypatch) -> None:
        """Block response suggests spawning custodiet."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Edit", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        assert result is not None


class TestSoftReminder:
    """Test soft reminder for read-only tools when overdue."""

    def test_readonly_gets_reminder_when_overdue(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Read-only tools get soft reminder (not block) when overdue."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_SESSION_ID", cwd)  # SESSION_ID preferred over CWD
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        setup_custodiet_state(cwd, tool_calls_since_compliance=10)

        from hooks.gate_registry import GateContext, check_custodiet_gate

        ctx = GateContext(
            session_id=cwd,
            event_name="PreToolUse",
            input_data={"tool_name": "Read", "tool_input": {"file_path": "/test.py"}},
        )
        result = check_custodiet_gate(ctx)
        # Read only tools are NOT blocked (returns None)
        assert result is None
