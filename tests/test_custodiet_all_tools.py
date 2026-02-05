"""Unit tests for custodiet gate counting ALL tool calls.

Tests that:
1. run_accountant increments counter for ALL tools (not just MUTATING_TOOLS)
2. check_custodiet_gate still only blocks MUTATING_TOOLS at threshold
3. Read-only sessions can accumulate high counts without being blocked
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from hooks.gate_registry import (
    run_accountant,
    check_custodiet_gate,
    GateVerdict,
)
from hooks.schemas import HookContext


class MockSessionState:
    """Mock for session_state module that tracks state in memory."""

    def __init__(self):
        self.sessions = {}

    def get_or_create_session_state(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"state": {}}
        return self.sessions[session_id]

    def save_session_state(self, session_id, state):
        self.sessions[session_id] = state

    def record_file_read(self, session_id, file_path):
        pass  # Not relevant for these tests


def make_context(tool_name: str, event_name: str = "PostToolUse", session_id: str = "test-session"):
    """Create a HookContext for testing."""
    return HookContext(
        session_id=session_id,
        hook_event=event_name,
        raw_input={
            "tool_name": tool_name,
            "tool_input": {},
        },
        tool_name=tool_name,
        tool_input={},
    )


class TestRunAccountantCountsAllTools:
    """Tests that run_accountant counts ALL tool calls, not just mutating ones."""

    @pytest.fixture
    def mock_session_state(self):
        mock = MockSessionState()
        with patch("hooks.gate_registry.session_state", mock):
            yield mock

    def test_read_tool_increments_counter(self, mock_session_state):
        """Read tool should increment tool_calls_since_compliance."""
        ctx = make_context("Read", "PostToolUse")
        run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 1

    def test_glob_tool_increments_counter(self, mock_session_state):
        """Glob tool should increment tool_calls_since_compliance."""
        ctx = make_context("Glob", "PostToolUse")
        run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 1

    def test_grep_tool_increments_counter(self, mock_session_state):
        """Grep tool should increment tool_calls_since_compliance."""
        ctx = make_context("Grep", "PostToolUse")
        run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 1

    def test_edit_tool_increments_counter(self, mock_session_state):
        """Edit (mutating) tool should increment tool_calls_since_compliance."""
        ctx = make_context("Edit", "PostToolUse")
        run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 1

    def test_multiple_read_tools_increment(self, mock_session_state):
        """Multiple read-only tools should accumulate counter."""
        for _ in range(5):
            ctx = make_context("Read", "PostToolUse")
            run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 5

    def test_mixed_tools_all_counted(self, mock_session_state):
        """Mix of read-only and mutating tools should all be counted."""
        tools = ["Read", "Glob", "Edit", "Read", "Write", "Grep"]
        for tool in tools:
            ctx = make_context(tool, "PostToolUse")
            run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 6


class TestCheckCustodietGateOnlyBlocksMutating:
    """Tests that check_custodiet_gate only blocks MUTATING_TOOLS at threshold."""

    @pytest.fixture
    def mock_session_state_over_threshold(self):
        """Set up session state with counter over threshold."""
        mock = MockSessionState()
        mock.sessions["test-session"] = {
            "state": {
                "tool_calls_since_compliance": 20,  # Over default threshold of 15
                "last_compliance_ts": 0.0,
            }
        }
        with patch("hooks.gate_registry.session_state", mock):
            with patch("hooks.gate_registry.get_custodiet_threshold", return_value=15):
                yield mock

    def test_read_tool_allowed_over_threshold(self, mock_session_state_over_threshold):
        """Read tool should be allowed even when counter is over threshold."""
        ctx = make_context("Read", "PreToolUse")
        result = check_custodiet_gate(ctx)
        assert result is None  # None means allowed

    def test_glob_tool_allowed_over_threshold(self, mock_session_state_over_threshold):
        """Glob tool should be allowed even when counter is over threshold."""
        ctx = make_context("Glob", "PreToolUse")
        result = check_custodiet_gate(ctx)
        assert result is None

    def test_grep_tool_allowed_over_threshold(self, mock_session_state_over_threshold):
        """Grep tool should be allowed even when counter is over threshold."""
        ctx = make_context("Grep", "PreToolUse")
        result = check_custodiet_gate(ctx)
        assert result is None

    def test_edit_tool_blocked_over_threshold(self, mock_session_state_over_threshold):
        """Edit (mutating) tool should be blocked when counter is over threshold."""
        # Need to mock the template loading for the block message
        with patch("hooks.gate_registry._custodiet_build_audit_instruction", return_value="blocked"):
            ctx = make_context("Edit", "PreToolUse")
            result = check_custodiet_gate(ctx)
            assert result is not None
            assert result.verdict == GateVerdict.DENY

    def test_write_tool_blocked_over_threshold(self, mock_session_state_over_threshold):
        """Write (mutating) tool should be blocked when counter is over threshold."""
        with patch("hooks.gate_registry._custodiet_build_audit_instruction", return_value="blocked"):
            ctx = make_context("Write", "PreToolUse")
            result = check_custodiet_gate(ctx)
            assert result is not None
            assert result.verdict == GateVerdict.DENY


class TestReadOnlySessionScenario:
    """Integration-style test for read-only session behavior."""

    @pytest.fixture
    def mock_session_state(self):
        mock = MockSessionState()
        with patch("hooks.gate_registry.session_state", mock):
            with patch("hooks.gate_registry.get_custodiet_threshold", return_value=15):
                yield mock

    def test_read_only_session_not_blocked_at_25_calls(self, mock_session_state):
        """A read-only session with 25 tool calls should not be blocked."""
        # Simulate 25 Read calls via run_accountant
        for _ in range(25):
            ctx = make_context("Read", "PostToolUse")
            run_accountant(ctx)

        # Counter should be 25
        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 25

        # But a Read tool should still be allowed (not blocked)
        ctx = make_context("Read", "PreToolUse")
        result = check_custodiet_gate(ctx)
        assert result is None  # Allowed

    def test_read_only_session_blocks_first_edit_after_threshold(self, mock_session_state):
        """After 20 reads, the FIRST Edit should be blocked."""
        # Simulate 20 Read calls
        for _ in range(20):
            ctx = make_context("Read", "PostToolUse")
            run_accountant(ctx)

        state = mock_session_state.sessions["test-session"]["state"]
        assert state["tool_calls_since_compliance"] == 20

        # Now an Edit should be blocked
        with patch("hooks.gate_registry._custodiet_build_audit_instruction", return_value="blocked"):
            ctx = make_context("Edit", "PreToolUse")
            result = check_custodiet_gate(ctx)
            assert result is not None
            assert result.verdict == GateVerdict.DENY
