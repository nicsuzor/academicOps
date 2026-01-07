"""Tests for lib/session_state.py - Session state management.

TDD Phase 1: Foundation - Session State API
Tests atomic CRUD operations for hydrator and custodiet state files.
"""

from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path


class TestProjectHash:
    """Test project hash generation."""

    def test_same_cwd_produces_same_hash(self) -> None:
        """Same cwd should always produce the same hash."""
        from lib.session_state import get_project_hash

        cwd = "/home/user/project"
        hash1 = get_project_hash(cwd)
        hash2 = get_project_hash(cwd)
        assert hash1 == hash2

    def test_different_cwd_produces_different_hash(self) -> None:
        """Different cwds should produce different hashes."""
        from lib.session_state import get_project_hash

        hash1 = get_project_hash("/home/user/project1")
        hash2 = get_project_hash("/home/user/project2")
        assert hash1 != hash2

    def test_hash_is_short_identifier(self) -> None:
        """Hash should be a short identifier (12 chars)."""
        from lib.session_state import get_project_hash

        project_hash = get_project_hash("/home/user/project")
        assert len(project_hash) == 12
        assert project_hash.isalnum()


class TestStatePaths:
    """Test state file path generation."""

    def test_hydrator_state_path_format(self, tmp_path: Path, monkeypatch) -> None:
        """Hydrator state path follows spec format."""
        from lib.session_state import get_hydrator_state_path, get_project_hash

        # Patch state dir to use tmp
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        cwd = "/home/user/project"
        path = get_hydrator_state_path(cwd)
        project_hash = get_project_hash(cwd)

        assert path.name == f"hydrator-{project_hash}.json"
        assert path.parent == tmp_path

    def test_custodiet_state_path_format(self, tmp_path: Path, monkeypatch) -> None:
        """Custodiet state path follows spec format."""
        from lib.session_state import get_custodiet_state_path, get_project_hash

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        cwd = "/home/user/project"
        path = get_custodiet_state_path(cwd)
        project_hash = get_project_hash(cwd)

        assert path.name == f"custodiet-{project_hash}.json"
        assert path.parent == tmp_path


class TestHydratorState:
    """Test hydrator state CRUD operations."""

    def test_load_missing_state_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """Loading non-existent state returns None."""
        from lib.session_state import load_hydrator_state

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        result = load_hydrator_state("/nonexistent/project")
        assert result is None

    def test_save_and_load_state(self, tmp_path: Path, monkeypatch) -> None:
        """Save and load hydrator state roundtrip."""
        from lib.session_state import (
            HydratorState,
            load_hydrator_state,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        cwd = "/home/user/project"
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
        }

        save_hydrator_state(cwd, state)
        loaded = load_hydrator_state(cwd)

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
        }

        save_hydrator_state("/project", state)
        assert state_dir.exists()

    def test_save_is_atomic(self, tmp_path: Path, monkeypatch) -> None:
        """Save uses atomic write-then-rename pattern."""
        from lib.session_state import (
            HydratorState,
            get_hydrator_state_path,
            save_hydrator_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        cwd = "/project"
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
        }

        save_hydrator_state(cwd, state)

        # Verify no .tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Verify final file is valid JSON
        state_path = get_hydrator_state_path(cwd)
        loaded = json.loads(state_path.read_text())
        assert loaded["last_hydration_ts"] == 0.0


class TestCustodietState:
    """Test custodiet state CRUD operations."""

    def test_load_missing_state_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """Loading non-existent state returns None."""
        from lib.session_state import load_custodiet_state

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        result = load_custodiet_state("/nonexistent/project")
        assert result is None

    def test_save_and_load_state(self, tmp_path: Path, monkeypatch) -> None:
        """Save and load custodiet state roundtrip."""
        from lib.session_state import (
            CustodietState,
            load_custodiet_state,
            save_custodiet_state,
        )

        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(tmp_path))

        cwd = "/home/user/project"
        state: CustodietState = {
            "last_compliance_ts": 1234567890.456,
            "tool_calls_since_compliance": 5,
            "last_drift_warning": "drift detected at tool 3",
        }

        save_custodiet_state(cwd, state)
        loaded = load_custodiet_state(cwd)

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

        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
        }

        save_custodiet_state("/project", state)
        loaded = load_custodiet_state("/project")

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

        cwd = "/project"
        num_processes = 10
        writes_per_process = 5

        def writer(process_id: int) -> None:
            """Write state multiple times."""
            for i in range(writes_per_process):
                state: CustodietState = {
                    "last_compliance_ts": float(process_id * 1000 + i),
                    "tool_calls_since_compliance": process_id * 10 + i,
                    "last_drift_warning": f"process_{process_id}_write_{i}",
                }
                save_custodiet_state(cwd, state)
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
        final_state = load_custodiet_state(cwd)
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

        cwd = "/project"

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
        }
        save_hydrator_state(cwd, initial_state)

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
            }
            save_hydrator_state(cwd, new_state)

            # Immediate read - should not crash
            try:
                result = load_hydrator_state(cwd)
                if result is not None:
                    # If we got a result, it should be valid
                    assert isinstance(result["active_skill"], str)
            except json.JSONDecodeError as e:
                errors.append(str(e))

        # Should have zero JSON decode errors (retry logic handles race conditions)
        assert len(errors) == 0, f"Got {len(errors)} JSON errors: {errors[:3]}"


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
