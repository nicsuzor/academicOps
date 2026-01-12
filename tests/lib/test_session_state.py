"""Tests for lib/session_state.py - Session state management.

TDD Phase 1: Foundation - Session State API
Tests atomic CRUD operations for hydrator and custodiet state files.

Note: State is keyed by session_id (UUID-like string), NOT project cwd.
"""

from __future__ import annotations

import json
import multiprocessing
import time
import uuid
from pathlib import Path


def make_session_id() -> str:
    """Generate a test session ID (UUID format)."""
    return str(uuid.uuid4())


class TestStatePaths:
    """Test state file path generation."""

    def test_hydrator_state_path_format(self, tmp_path: Path, monkeypatch) -> None:
        """Hydrator state path follows spec format."""
        from lib.session_state import get_hydrator_state_path

        # Patch state dir to use tmp
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = "abc123-def456-789"
        path = get_hydrator_state_path(session_id)

        assert path.name == f"hydrator-{session_id}.json"
        assert path.parent == tmp_path

    def test_custodiet_state_path_format(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet state path follows spec format."""
        from lib.session_state import get_custodiet_state_path

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = "abc123-def456-789"
        path = get_custodiet_state_path(session_id)

        assert path.name == f"custodiet-{session_id}.json"
        assert path.parent == tmp_path


class TestSessionIsolation:
    """Test that different sessions have isolated state."""

    def test_different_sessions_have_different_state_files(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Different session IDs should produce different state file paths."""
        from lib.session_state import get_hydrator_state_path

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session1 = make_session_id()
        session2 = make_session_id()

        path1 = get_hydrator_state_path(session1)
        path2 = get_hydrator_state_path(session2)

        assert path1 != path2
        assert session1 in str(path1)
        assert session2 in str(path2)

    def test_sessions_dont_share_state(self, tmp_path: Path, monkeypatch) -> None:
        """State saved for one session should not be visible to another."""
        from lib.session_state import (
            HydratorState,
            load_hydrator_state,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session1 = make_session_id()
        session2 = make_session_id()

        state1: HydratorState = {
            "last_hydration_ts": 1.0,
            "declared_workflow": {
                "gate": "plan",
                "pre_work": "none",
                "approach": "tdd",
            },
            "active_skill": "skill1",
            "intent_envelope": "session 1 intent",
            "guardrails": ["g1"],
            "hydration_pending": False,
        }

        save_hydrator_state(session1, state1)

        # Session 2 should not see session 1's state
        assert load_hydrator_state(session2) is None

        # Session 1 should see its own state
        loaded = load_hydrator_state(session1)
        assert loaded is not None
        assert loaded["active_skill"] == "skill1"


class TestHydratorState:
    """Test hydrator state CRUD operations."""

    def test_load_missing_state_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """Loading non-existent state returns None."""
        from lib.session_state import load_hydrator_state

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        result = load_hydrator_state(make_session_id())
        assert result is None

    def test_save_and_load_state(self, tmp_path: Path, monkeypatch) -> None:
        """Save and load hydrator state roundtrip."""
        from lib.session_state import (
            HydratorState,
            load_hydrator_state,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: HydratorState = {
            "last_hydration_ts": 1234567890.123,
            "declared_workflow": {
                "gate": "plan-mode",
                "pre_work": "verify-first",
                "approach": "tdd",
            },
            "active_skill": "framework",
            "intent_envelope": "implement gate architecture",
            "guardrails": ["verify_before_complete", "require_acceptance_test"],
            "hydration_pending": True,
        }

        save_hydrator_state(session_id, state)
        loaded = load_hydrator_state(session_id)

        assert loaded is not None
        assert loaded["last_hydration_ts"] == state["last_hydration_ts"]
        assert loaded["declared_workflow"] == state["declared_workflow"]
        assert loaded["active_skill"] == state["active_skill"]
        assert loaded["intent_envelope"] == state["intent_envelope"]
        assert loaded["guardrails"] == state["guardrails"]

    def test_save_creates_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Save creates state directory if missing."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "subdir" / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "",
            "intent_envelope": "",
            "guardrails": [],
            "hydration_pending": False,
        }

        save_hydrator_state(make_session_id(), state)
        assert state_dir.exists()

    def test_save_is_atomic(self, tmp_path: Path, monkeypatch) -> None:
        """Save uses atomic write-then-rename pattern."""
        from lib.session_state import (
            HydratorState,
            get_hydrator_state_path,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "",
            "intent_envelope": "",
            "guardrails": [],
            "hydration_pending": False,
        }

        save_hydrator_state(session_id, state)

        # Verify no .tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Verify final file is valid JSON
        state_path = get_hydrator_state_path(session_id)
        loaded = json.loads(state_path.read_text())
        assert loaded["last_hydration_ts"] == 0.0


class TestCustodietState:
    """Test custodiet state CRUD operations."""

    def test_load_missing_state_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """Loading non-existent state returns None."""
        from lib.session_state import load_custodiet_state

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        result = load_custodiet_state(make_session_id())
        assert result is None

    def test_save_and_load_state(self, tmp_path: Path, monkeypatch) -> None:
        """Save and load custodiet state roundtrip."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: CustodietState = {
            "last_compliance_ts": 1234567890.456,
            "tool_calls_since_compliance": 5,
            "last_drift_warning": "drift detected at tool 3",
            "error_flag": None,
        }

        save_custodiet_state(session_id, state)
        loaded = load_custodiet_state(session_id)

        assert loaded is not None
        assert loaded["last_compliance_ts"] == state["last_compliance_ts"]
        assert (
            loaded["tool_calls_since_compliance"]
            == state["tool_calls_since_compliance"]
        )
        assert loaded["last_drift_warning"] == state["last_drift_warning"]

    def test_null_drift_warning(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet state handles null drift warning."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
            "error_flag": None,
        }

        save_custodiet_state(session_id, state)
        loaded = load_custodiet_state(session_id)

        assert loaded is not None
        assert loaded["last_drift_warning"] is None


class TestConcurrentAccess:
    """Test concurrent access safety."""

    def test_concurrent_writes_dont_corrupt(self, tmp_path: Path, monkeypatch) -> None:
        """Multiple concurrent writers should not corrupt state."""
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        # Import here to use patched env
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        session_id = make_session_id()
        num_processes = 10
        writes_per_process = 5

        def writer(process_id: int) -> None:
            """Write state multiple times."""
            for i in range(writes_per_process):
                state: CustodietState = {
                    "last_compliance_ts": float(process_id * 1000 + i),
                    "tool_calls_since_compliance": process_id * 10 + i,
                    "last_drift_warning": f"process_{process_id}_write_{i}",
                    "error_flag": None,
                }
                save_custodiet_state(session_id, state)
                time.sleep(0.001)  # Small delay to interleave writes

        # Run concurrent writers
        processes = []
        for pid in range(num_processes):
            p = multiprocessing.Process(target=writer, args=(pid,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        # Final state should be valid JSON
        final_state = load_custodiet_state(session_id)
        assert final_state is not None
        assert isinstance(final_state["tool_calls_since_compliance"], int)
        assert isinstance(final_state["last_compliance_ts"], float)

    def test_read_during_write_returns_valid_or_none(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Read during write should return valid state or None, not crash."""
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        from lib.session_state import (
            HydratorState,
            load_hydrator_state,
            save_hydrator_state,
        )

        session_id = make_session_id()

        # Create initial state
        initial_state: HydratorState = {
            "last_hydration_ts": 1.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "initial",
            "intent_envelope": "test",
            "guardrails": [],
            "hydration_pending": False,
        }
        save_hydrator_state(session_id, initial_state)

        # Rapid read/write cycles
        errors = []
        for i in range(50):
            # Write
            new_state: HydratorState = {
                "last_hydration_ts": float(i),
                "declared_workflow": {
                    "gate": "none",
                    "pre_work": "none",
                    "approach": "direct",
                },
                "active_skill": f"skill_{i}",
                "intent_envelope": f"intent_{i}",
                "guardrails": [],
                "hydration_pending": False,
            }
            save_hydrator_state(session_id, new_state)

            # Immediate read - should not crash
            try:
                result = load_hydrator_state(session_id)
                if result is not None:
                    # If we got a result, it should be valid
                    assert isinstance(result["active_skill"], str)
            except json.JSONDecodeError as e:
                errors.append(str(e))

        # Should have zero JSON decode errors (retry logic handles race conditions)
        assert len(errors) == 0, f"Got {len(errors)} JSON errors: {errors[:3]}"


class TestErrorFlag:
    """Test error flag operations for cross-hook coordination."""

    def test_set_error_flag_creates_flag(self, tmp_path: Path, monkeypatch) -> None:
        """set_error_flag should create error_flag in custodiet state."""
        from lib.session_state import get_error_flag, set_error_flag

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        set_error_flag(session_id, "compliance_failure", "Agent violated H2")

        flag = get_error_flag(session_id)
        assert flag is not None
        assert flag["error_type"] == "compliance_failure"
        assert flag["message"] == "Agent violated H2"
        assert "timestamp" in flag
        assert isinstance(flag["timestamp"], float)

    def test_get_error_flag_returns_none_when_not_set(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """get_error_flag should return None when no flag exists."""
        from lib.session_state import get_error_flag

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        flag = get_error_flag(make_session_id())
        assert flag is None

    def test_get_error_flag_returns_none_after_clear(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """get_error_flag should return None after flag is cleared."""
        from lib.session_state import clear_error_flag, get_error_flag, set_error_flag

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        set_error_flag(session_id, "intervention_required", "Test message")
        assert get_error_flag(session_id) is not None

        clear_error_flag(session_id)
        assert get_error_flag(session_id) is None

    def test_clear_error_flag_preserves_other_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """clear_error_flag should not affect other custodiet state fields."""
        from lib.session_state import (
            clear_error_flag,
            load_custodiet_state,
            save_custodiet_state,
            set_error_flag,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        # Set up initial state with other fields
        initial_state = {
            "last_compliance_ts": 1234567890.0,
            "tool_calls_since_compliance": 5,
            "last_drift_warning": "some warning",
            "error_flag": None,
        }
        save_custodiet_state(session_id, initial_state)

        # Set error flag
        set_error_flag(session_id, "cannot_assess", "Missing context")

        # Clear error flag
        clear_error_flag(session_id)

        # Other fields should be preserved
        state = load_custodiet_state(session_id)
        assert state is not None
        assert state["last_compliance_ts"] == 1234567890.0
        assert state["tool_calls_since_compliance"] == 5
        assert state["last_drift_warning"] == "some warning"

    def test_set_error_flag_on_fresh_state(self, tmp_path: Path, monkeypatch) -> None:
        """set_error_flag should work when no prior state exists."""
        from lib.session_state import (
            get_error_flag,
            load_custodiet_state,
            set_error_flag,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        set_error_flag(session_id, "compliance_failure", "First flag")

        # Flag should be set
        flag = get_error_flag(session_id)
        assert flag is not None
        assert flag["error_type"] == "compliance_failure"

        # State should have been initialized
        state = load_custodiet_state(session_id)
        assert state is not None

    def test_error_flag_types(self, tmp_path: Path, monkeypatch) -> None:
        """Error flag supports documented error types."""
        from lib.session_state import get_error_flag, set_error_flag

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()

        # Test each documented error type
        for error_type in [
            "compliance_failure",
            "intervention_required",
            "cannot_assess",
        ]:
            set_error_flag(session_id, error_type, f"Test {error_type}")
            flag = get_error_flag(session_id)
            assert flag["error_type"] == error_type

    def test_error_flag_overwrites_previous(self, tmp_path: Path, monkeypatch) -> None:
        """Setting error flag should overwrite any previous flag."""
        from lib.session_state import get_error_flag, set_error_flag

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        set_error_flag(session_id, "compliance_failure", "First error")
        set_error_flag(session_id, "intervention_required", "Second error")

        flag = get_error_flag(session_id)
        assert flag["error_type"] == "intervention_required"
        assert flag["message"] == "Second error"


class TestStateDirectory:
    """Test state directory management."""

    def test_default_state_dir(self) -> None:
        """Default state directory is /tmp/claude-session."""
        from lib.session_state import get_state_dir

        # Without override, should use default
        state_dir = get_state_dir()
        assert state_dir == Path("/tmp/claude-session")

    def test_override_state_dir(self, tmp_path: Path, monkeypatch) -> None:
        """State directory can be overridden via env var."""
        from lib.session_state import get_state_dir

        custom_dir = tmp_path / "custom-state"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(custom_dir))

        state_dir = get_state_dir()
        assert state_dir == custom_dir


class TestHydrationGate:
    """Test hydration gate API."""

    def test_is_hydration_pending_false_when_no_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """is_hydration_pending returns False when no state exists."""
        from lib.session_state import is_hydration_pending

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        assert is_hydration_pending(make_session_id()) is False

    def test_is_hydration_pending_true(self, tmp_path: Path, monkeypatch) -> None:
        """is_hydration_pending returns True when flag is set."""
        from lib.session_state import (
            HydratorState,
            is_hydration_pending,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "",
            "intent_envelope": "",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(session_id, state)

        assert is_hydration_pending(session_id) is True

    def test_clear_hydration_pending(self, tmp_path: Path, monkeypatch) -> None:
        """clear_hydration_pending clears the flag."""
        from lib.session_state import (
            HydratorState,
            clear_hydration_pending,
            is_hydration_pending,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        session_id = make_session_id()
        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "",
            "intent_envelope": "",
            "guardrails": [],
            "hydration_pending": True,
        }
        save_hydrator_state(session_id, state)

        assert is_hydration_pending(session_id) is True
        clear_hydration_pending(session_id)
        assert is_hydration_pending(session_id) is False
