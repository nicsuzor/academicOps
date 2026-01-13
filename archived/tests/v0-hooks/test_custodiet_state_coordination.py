"""Tests for custodiet_gate.py state coordination.

TDD Phase 6: Custodiet State Coordination
Tests that custodiet uses shared state files for cross-gate coordination.
"""

from __future__ import annotations

from pathlib import Path


class TestCustodietStateIncrement:
    """Test tool call counter increment."""

    def test_increments_tool_calls_counter(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet increments tool_calls_since_compliance counter."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        # Set initial state
        initial_state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 3,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, initial_state)

        from hooks.custodiet_gate import increment_tool_count

        new_count = increment_tool_count(cwd)

        assert new_count == 4
        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert loaded["tool_calls_since_compliance"] == 4

    def test_creates_state_if_missing(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet creates state if none exists."""
        from lib.session_state import load_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/new/project"

        from hooks.custodiet_gate import increment_tool_count

        new_count = increment_tool_count(cwd)

        assert new_count == 1
        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert loaded["tool_calls_since_compliance"] == 1


class TestCustodietStateReset:
    """Test counter reset after compliance check."""

    def test_resets_counter_on_compliance(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet resets counter after running compliance check."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        # Set state at threshold
        initial_state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, initial_state)

        from hooks.custodiet_gate import reset_compliance_state

        reset_compliance_state(cwd)

        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert loaded["tool_calls_since_compliance"] == 0
        assert loaded["last_compliance_ts"] > 0

    def test_reset_updates_timestamp(self, tmp_path: Path, monkeypatch) -> None:
        """Reset updates last_compliance_ts to current time."""
        import time

        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        initial_state: CustodietState = {
            "last_compliance_ts": 1000.0,  # Old timestamp
            "tool_calls_since_compliance": 5,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, initial_state)

        before = time.time()

        from hooks.custodiet_gate import reset_compliance_state

        reset_compliance_state(cwd)
        after = time.time()

        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert before <= loaded["last_compliance_ts"] <= after


class TestCustodietReadsHydratorState:
    """Test reading intent from hydrator state."""

    def test_reads_intent_envelope(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet reads intent_envelope from hydrator state."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        hydrator_state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "framework",
            "intent_envelope": "Fix the parser bug in module X",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        from hooks.custodiet_gate import get_intent_from_hydrator

        intent = get_intent_from_hydrator(cwd)

        assert intent == "Fix the parser bug in module X"

    def test_returns_none_if_no_hydrator_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Returns None if hydrator state doesn't exist."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/nonexistent/project"

        from hooks.custodiet_gate import get_intent_from_hydrator

        intent = get_intent_from_hydrator(cwd)

        assert intent is None

    def test_returns_workflow_from_hydrator(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet can read workflow from hydrator state."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        hydrator_state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "plan-mode",
                "pre_work": "verify",
                "approach": "tdd",
            },
            "active_skill": "framework",
            "intent_envelope": "test",
            "guardrails": ["verify_before_complete"],
        }
        save_hydrator_state(cwd, hydrator_state)

        from hooks.custodiet_gate import get_workflow_from_hydrator

        workflow = get_workflow_from_hydrator(cwd)

        assert workflow is not None
        assert workflow["approach"] == "tdd"


class TestCustodietDriftWarning:
    """Test drift warning storage."""

    def test_stores_drift_warning(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet stores drift warning in state."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        initial_state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, initial_state)

        from hooks.custodiet_gate import set_drift_warning

        set_drift_warning(cwd, "Detected drift from original intent")

        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert loaded["last_drift_warning"] == "Detected drift from original intent"

    def test_clears_drift_warning_on_reset(self, tmp_path: Path, monkeypatch) -> None:
        """Drift warning cleared on compliance reset."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        initial_state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 5,
            "last_drift_warning": "Old warning",
        }
        save_custodiet_state(cwd, initial_state)

        from hooks.custodiet_gate import reset_compliance_state

        reset_compliance_state(cwd)

        loaded = load_custodiet_state(cwd)
        assert loaded is not None
        assert loaded["last_drift_warning"] is None


class TestCustodietUsesSharedState:
    """Test that custodiet uses the shared state API."""

    def test_uses_session_state_api(self, tmp_path: Path, monkeypatch) -> None:
        """Verify custodiet uses lib/session_state.py, not its own state files."""
        from lib.session_state import (
            CustodietState,
            get_custodiet_state_path,
            save_custodiet_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        # Save using shared API
        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 2,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        # Increment should read from shared state
        from hooks.custodiet_gate import increment_tool_count

        new_count = increment_tool_count(cwd)

        # Should increment from 2 to 3 (proving it read shared state)
        assert new_count == 3

        # Verify it wrote to shared state path
        shared_path = get_custodiet_state_path(cwd)
        assert shared_path.exists()
