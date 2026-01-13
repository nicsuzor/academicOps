#!/usr/bin/env python3
"""End-to-end tests for gate coordination architecture.

TDD Phase 7: Integration E2E
Tests the full gate coordination flow across all phases:
- Session Start: UserPromptSubmit → hydrator state write
- Continuous Enforcement: PreToolUse → skill monitor + overdue check
- Post-Action: PostToolUse → custodiet state coordination

Per H37: Tests verify ACTUAL behavior, not surface patterns.
Per H37b: Use REAL framework patterns, not contrived examples.
"""

from __future__ import annotations

import time
from pathlib import Path


class TestHydratorStatePersistence:
    """Test hydrator state persists and is readable by other gates."""

    def test_hydrator_state_written_on_prompt(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """UserPromptSubmit writes hydrator state that other gates can read."""
        from lib.session_state import get_hydrator_state_path, load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Simulate UserPromptSubmit writing state
        from hooks.user_prompt_submit import write_initial_hydrator_state

        write_initial_hydrator_state("Fix the authentication bug in login.py")

        # Verify state file exists
        state_path = get_hydrator_state_path(cwd)
        assert state_path.exists(), "Hydrator state should be written"

        # Verify other gates can read it
        state = load_hydrator_state(cwd)
        assert state is not None
        assert "intent_envelope" in state
        assert "authentication" in state["intent_envelope"].lower()

    def test_hydrator_state_readable_by_custodiet(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Custodiet gate can read hydrator state for intent checking."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        # Write hydrator state
        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",
            "intent_envelope": "Implement user authentication system",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        # Custodiet can read intent
        from hooks.custodiet_gate import get_intent_from_hydrator

        intent = get_intent_from_hydrator(cwd)
        assert intent == "Implement user authentication system"

    def test_hydrator_state_readable_by_skill_monitor(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Skill monitor can read active_skill from hydrator state."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Write hydrator state with active skill
        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "tdd",
            },
            "active_skill": "framework",
            "intent_envelope": "Fix hooks implementation",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        # Skill monitor can read active skill via hydrator state
        from lib.session_state import load_hydrator_state

        state = load_hydrator_state(cwd)
        assert state is not None
        assert state["active_skill"] == "framework"


class TestCustodietHydratorCoordination:
    """Test custodiet reads hydrator state for compliance checking."""

    def test_custodiet_reads_workflow_from_hydrator(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Custodiet can read declared workflow from hydrator state."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "plan-mode",
                "pre_work": "verify",
                "approach": "tdd",
            },
            "active_skill": "framework",
            "intent_envelope": "Implement new feature",
            "guardrails": ["verify_before_complete"],
        }
        save_hydrator_state(cwd, hydrator_state)

        from hooks.custodiet_gate import get_workflow_from_hydrator

        workflow = get_workflow_from_hydrator(cwd)
        assert workflow is not None
        assert workflow["approach"] == "tdd"
        assert workflow["gate"] == "plan-mode"

    def test_custodiet_handles_missing_hydrator_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Custodiet handles missing hydrator state gracefully."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/nonexistent/project"

        from hooks.custodiet_gate import get_intent_from_hydrator

        intent = get_intent_from_hydrator(cwd)
        assert intent is None


class TestOverdueEnforcementIntegration:
    """Test overdue enforcement reads custodiet state."""

    def test_overdue_reads_custodiet_state(self, tmp_path: Path, monkeypatch) -> None:
        """Overdue enforcement reads tool count from custodiet state."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Set tool count above threshold
        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        # Overdue should block mutating tools
        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert result["decision"] == "block"

    def test_overdue_allows_after_custodiet_reset(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """After custodiet resets counter, overdue allows tools."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Start with high count
        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 10,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        # Reset via custodiet function
        from hooks.custodiet_gate import reset_compliance_state

        reset_compliance_state(cwd)

        # Now overdue should allow
        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is None  # No block


class TestSkillMonitorIntegration:
    """Test skill monitor integration with hydrator state."""

    def test_skill_monitor_detects_drift_from_hydrator_skill(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Skill monitor detects drift from active skill in hydrator state."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Active skill is python-dev
        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",
            "intent_envelope": "Implement feature",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        # Tool call is in framework domain (hooks/)
        from hooks.skill_monitor import check_skill_monitor

        result = check_skill_monitor(
            tool_name="Edit", tool_input={"file_path": "/project/hooks/policy.py"}
        )

        # Should inject framework context due to drift
        assert result is not None
        assert "framework" in result.lower()

    def test_skill_monitor_no_drift_when_matching(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """No injection when tool matches active skill."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Active skill is python-dev
        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",
            "intent_envelope": "Implement feature",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        # Tool call is in python domain
        from hooks.skill_monitor import check_skill_monitor

        result = check_skill_monitor(
            tool_name="Edit", tool_input={"file_path": "/project/src/utils.py"}
        )

        # No drift, no injection
        assert result is None


class TestFullGateFlow:
    """Test complete gate flow: UserPromptSubmit → PreToolUse → PostToolUse."""

    def test_full_flow_state_coordination(self, tmp_path: Path, monkeypatch) -> None:
        """Full gate flow maintains coordinated state."""
        from lib.session_state import load_custodiet_state, load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Phase 1: UserPromptSubmit writes hydrator state
        from hooks.user_prompt_submit import write_initial_hydrator_state

        write_initial_hydrator_state("Fix the bug in authentication module")

        # Verify hydrator state written
        hydrator = load_hydrator_state(cwd)
        assert hydrator is not None
        assert "authentication" in hydrator["intent_envelope"].lower()

        # Phase 2: Simulate multiple tool calls incrementing custodiet counter
        from hooks.custodiet_gate import increment_tool_count

        for i in range(5):
            count = increment_tool_count(cwd)
            assert count == i + 1

        # Verify custodiet state reflects tool counts
        custodiet = load_custodiet_state(cwd)
        assert custodiet is not None
        assert custodiet["tool_calls_since_compliance"] == 5

        # Phase 3: Custodiet reads hydrator state for intent
        from hooks.custodiet_gate import get_intent_from_hydrator

        intent = get_intent_from_hydrator(cwd)
        assert intent is not None
        assert "authentication" in intent.lower()

        # Phase 4: Reset after compliance check
        from hooks.custodiet_gate import reset_compliance_state

        reset_compliance_state(cwd)

        # Verify reset
        custodiet = load_custodiet_state(cwd)
        assert custodiet["tool_calls_since_compliance"] == 0
        assert custodiet["last_compliance_ts"] > 0

    def test_overdue_blocks_after_threshold_without_custodiet(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Overdue blocks mutating tools at threshold 7 if custodiet skipped."""
        from lib.session_state import CustodietState, save_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        # Simulate tool count reaching overdue threshold (7)
        # without custodiet having reset it (threshold is 5)
        state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 7,  # At overdue threshold
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, state)

        # PreToolUse: Overdue should block mutating tools
        from hooks.overdue_enforcement import check_overdue

        result = check_overdue("Edit", {"file_path": "/test.py"})
        assert result is not None
        assert result["decision"] == "block"
        assert "compliance" in result["reason"].lower()

        # But read-only tools still allowed
        result = check_overdue("Read", {"file_path": "/test.py"})
        assert result is None or result.get("decision") != "block"

    def test_concurrent_state_operations_safe(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Concurrent state operations don't corrupt data.

        Note: This tests that concurrent writes don't corrupt the state file.
        Lost updates are acceptable (read-modify-write without locking) because
        in production, hooks execute sequentially, not in parallel threads.
        The key invariant is: state file remains valid JSON with non-negative count.
        """
        import threading

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/concurrent/project"

        errors: list[str] = []
        counts: list[int] = []

        def increment_many():
            """Increment counter multiple times."""
            from hooks.custodiet_gate import increment_tool_count

            for _ in range(10):
                try:
                    count = increment_tool_count(cwd)
                    counts.append(count)
                except Exception as e:
                    errors.append(str(e))

        # Run 5 threads concurrently
        threads = [threading.Thread(target=increment_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors (no corruption, valid JSON)
        assert len(errors) == 0, f"Concurrent operations failed: {errors}"

        # State should be valid and readable (not corrupted)
        from lib.session_state import load_custodiet_state

        final_state = load_custodiet_state(cwd)
        assert final_state is not None, "State file corrupted or missing"
        assert (
            final_state["tool_calls_since_compliance"] > 0
        ), "Counter should be positive"
        # Note: May be < 50 due to lost updates (acceptable for sequential hook usage)


class TestGateIsolation:
    """Test gates don't interfere with each other's state."""

    def test_different_projects_have_isolated_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Different project cwds have completely isolated state."""
        from lib.session_state import load_custodiet_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        # Project A: Increment tool count
        from hooks.custodiet_gate import increment_tool_count

        monkeypatch.setenv("CLAUDE_CWD", "/project/a")
        for _ in range(5):
            increment_tool_count("/project/a")

        # Project B: Separate counter
        for _ in range(3):
            increment_tool_count("/project/b")

        # Verify isolation
        state_a = load_custodiet_state("/project/a")
        state_b = load_custodiet_state("/project/b")

        assert state_a["tool_calls_since_compliance"] == 5
        assert state_b["tool_calls_since_compliance"] == 3

    def test_hydrator_and_custodiet_separate_files(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Hydrator and custodiet use separate state files."""
        from lib.session_state import (
            CustodietState,
            HydratorState,
            get_custodiet_state_path,
            get_hydrator_state_path,
            save_custodiet_state,
            save_hydrator_state,
        )

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"

        # Write both states
        hydrator_state: HydratorState = {
            "last_hydration_ts": time.time(),
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",
            "intent_envelope": "Test",
            "guardrails": [],
        }
        save_hydrator_state(cwd, hydrator_state)

        custodiet_state: CustodietState = {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 5,
            "last_drift_warning": None,
        }
        save_custodiet_state(cwd, custodiet_state)

        # Verify separate files
        hydrator_path = get_hydrator_state_path(cwd)
        custodiet_path = get_custodiet_state_path(cwd)

        assert hydrator_path != custodiet_path
        assert hydrator_path.exists()
        assert custodiet_path.exists()
        assert "hydrator" in hydrator_path.name
        assert "custodiet" in custodiet_path.name
