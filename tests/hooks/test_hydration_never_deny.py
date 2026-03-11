#!/usr/bin/env python3
"""Tests for hydration gate tool classification and bypass behavior.

Validates that:
1. Tool categories (spawn, always_available, infrastructure) are correctly assigned
2. Compliance agents bypass gate policies regardless of hydration mode
3. Always-available tools bypass all gates
4. Read-only tools ARE subject to hydration gate (mode-dependent verdict)
5. Agent/skill names are not confused with tool names
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))


from hooks.gate_config import COMPLIANCE_SUBAGENT_TYPES, TOOL_CATEGORIES, get_tool_category
from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


def _reinit_gates():
    """Reload gate_config and definitions with current env vars, reinit registry."""
    if "gate_config" in sys.modules:
        importlib.reload(sys.modules["gate_config"])
    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture(autouse=True)
def _pin_non_hydration_gate_modes(monkeypatch):
    """Pin non-hydration gate env vars to prevent leaks from other test files.

    HYDRATION_GATE_MODE defaults to 'warn' here as a safe baseline.
    Tests that need both warn/block modes should use the hydration_mode
    fixture (parameterized across warn/block), which overrides this default.
    """
    monkeypatch.setenv("HYDRATION_GATE_MODE", "warn")
    monkeypatch.setenv("CUSTODIET_GATE_MODE", "block")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    monkeypatch.setenv("CUSTODIET_TOOL_CALL_THRESHOLD", "50")
    _reinit_gates()
    yield
    _reinit_gates()


@pytest.fixture(params=["warn", "block"], ids=["hydration=warn", "hydration=block"])
def hydration_mode(request, monkeypatch):
    """Run hydration gate tests in both warn and block modes."""
    monkeypatch.setenv("HYDRATION_GATE_MODE", request.param)
    _reinit_gates()
    return request.param


@pytest.fixture
def mock_session_state():
    """Create a SessionState with mocked load path."""
    GateRegistry.initialize()

    with patch("lib.session_state.SessionState.load") as mock_load:
        state = SessionState.create("test-session-123")
        mock_load.return_value = state
        yield state, mock_load


class TestActivateSkillInSpawnCategory:
    """Test that spawn tools (Agent, Task, Skill, activate_skill) are in the spawn category."""

    def test_activate_skill_in_spawn(self):
        assert "activate_skill" in TOOL_CATEGORIES["spawn"]

    def test_activate_skill_category(self):
        assert get_tool_category("activate_skill") == "spawn"

    def test_skill_tool_in_spawn(self):
        assert "Skill" in TOOL_CATEGORIES["spawn"]

    def test_task_tool_in_spawn(self):
        assert "Task" in TOOL_CATEGORIES["spawn"]

    def test_agent_tool_in_spawn(self):
        assert "Agent" in TOOL_CATEGORIES["spawn"]


class TestAskUserQuestionAlwaysAvailable:
    """Test that AskUserQuestion is never blocked by the hydration gate."""

    def test_ask_user_question_in_always_available(self):
        assert "AskUserQuestion" in TOOL_CATEGORIES["always_available"]

    def test_ask_user_question_category(self):
        assert get_tool_category("AskUserQuestion") == "always_available"

    def test_ask_user_question_allowed_without_hydration(self, mock_session_state, hydration_mode):
        """AskUserQuestion should be allowed even without hydration, in any mode."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"
        state.state["hydration_pending"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="AskUserQuestion",
            tool_input={
                "questions": [
                    {
                        "question": "Test?",
                        "header": "Test",
                        "options": [],
                        "multiSelect": False,
                    }
                ]
            },
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW


class TestComplianceSpawnBypassesHydration:
    """Compliance agents dispatched via spawn tools bypass hydration gate.

    activate_skill(name='prompt-hydrator') extracts subagent_type='prompt-hydrator'
    which is a compliance type -> bypasses gate policies. This is the compliance
    bypass, NOT a property of activate_skill itself.
    """

    @pytest.fixture
    def mock_context(self):
        return HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="activate_skill",
            tool_input={"name": "prompt-hydrator"},
        )

    def test_compliance_skill_allowed_when_hydration_closed(
        self, mock_context, mock_session_state, hydration_mode
    ):
        """activate_skill(prompt-hydrator) allowed via compliance bypass in any mode."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"
        state.state["hydration_pending"] = True

        router = HookRouter()
        result = router._dispatch_gates(mock_context, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW


class TestHydratorActiveBypass:
    """Test that when hydrator is active, all tools are allowed."""

    def test_read_tool_allowed_when_hydrator_active(self, mock_session_state):
        state, _ = mock_session_state
        state.state["hydrator_active"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW

    def test_write_tool_allowed_when_hydrator_active(self, mock_session_state):
        state, _ = mock_session_state
        state.state["hydrator_active"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Write",
            tool_input={"file_path": "/some/file.py", "content": "test"},
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW


class TestTaskHydratorSpawn:
    """Test that Agent/Task tool with hydrator subagent is allowed and sets active."""

    def test_task_hydrator_allowed_and_sets_active(self, mock_session_state, hydration_mode):
        """Task with hydrator subagent should be allowed in any mode."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Task",
            tool_input={
                "subagent_type": "aops-core:prompt-hydrator",
                "prompt": "Hydrate this task",
            },
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW

    def test_agent_hydrator_allowed(self, mock_session_state, hydration_mode):
        """Agent with hydrator subagent should be allowed in any mode."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "closed"

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={
                "subagent_type": "aops-core:prompt-hydrator",
                "prompt": "Hydrate this task",
            },
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW


class TestReadToolSubjectToHydration:
    """Test that read-only tools ARE subject to the hydration gate.

    Only always_available tools bypass hydration. Read-only tools get
    warned/blocked depending on hydration mode.
    """

    def test_read_verdict_matches_mode_when_hydration_closed(
        self, mock_session_state, hydration_mode
    ):
        """Read should get mode-appropriate verdict when hydration gate is closed.

        warn mode -> WARN (tool allowed, agent warned to hydrate)
        block mode -> DENY (tool blocked until hydration)
        """
        state, _ = mock_session_state
        state.close_gate("hydration")
        state.gates["hydration"].metrics["temp_path"] = "/tmp/fake/instruction.md"
        state.state["hydrator_active"] = False
        state.state["hydration_pending"] = True

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        expected = GateVerdict.WARN if hydration_mode == "warn" else GateVerdict.DENY
        assert result is not None, (
            f"Expected {expected.value} but got None (allow) in {hydration_mode} mode"
        )
        assert result.verdict == expected, (
            f"Read tool should be {expected.value} in {hydration_mode} mode, "
            f"got {result.verdict.value}"
        )

    def test_read_allowed_when_hydration_passed(self, mock_session_state):
        """Read should be allowed when hydration gate is open."""
        state, _ = mock_session_state
        state.gates["hydration"].status = "open"
        state.state["hydrator_active"] = False
        state.state["hydration_pending"] = False

        ctx = HookContext(
            session_id="test-session-123",
            hook_event="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "/some/file.py"},
        )

        router = HookRouter()
        result = router._dispatch_gates(ctx, state)

        if result:
            assert result.verdict == GateVerdict.ALLOW


class TestAgentNamesNotInToolCategories:
    """Agent/skill names must NOT be in TOOL_CATEGORIES.

    Agent names like 'prompt-hydrator' and 'custodiet' are subagent_type
    values, not tool names. They should be in COMPLIANCE_SUBAGENT_TYPES
    instead of any tool category.
    """

    AGENT_NAMES = [
        "prompt-hydrator",
        "aops-core:prompt-hydrator",
        "custodiet",
        "aops-core:custodiet",
        "qa",
        "aops-core:qa",
        "handover",
        "aops-core:handover",
        "dump",
        "aops-core:dump",
    ]

    def test_agent_names_not_in_any_tool_category(self):
        all_tools = set()
        for tools in TOOL_CATEGORIES.values():
            all_tools |= tools
        for name in self.AGENT_NAMES:
            assert name not in all_tools, (
                f"Agent name '{name}' found in TOOL_CATEGORIES. "
                f"Agent names belong in COMPLIANCE_SUBAGENT_TYPES, not tool categories."
            )

    def test_compliance_subagent_types_has_expected_members(self):
        expected = {"prompt-hydrator", "custodiet", "audit", "butler"}
        for name in expected:
            assert (
                name in COMPLIANCE_SUBAGENT_TYPES
                or f"aops-core:{name}" in COMPLIANCE_SUBAGENT_TYPES
            ), f"'{name}' not found in COMPLIANCE_SUBAGENT_TYPES"
