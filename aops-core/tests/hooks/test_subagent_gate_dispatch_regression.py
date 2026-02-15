"""Regression tests for subagent gate dispatch.

Commit 9c8b10bd fixed two related bugs in HookRouter._dispatch_gates():

1. Subagents were completely skipped for gate dispatch (the old code had
   `if ctx.is_subagent: pass`). This meant gate state transitions (triggers)
   never ran for subagent sessions, causing stale gate states.

2. Compliance subagents (hydrator, custodiet, etc.) returned GateResult.allow()
   early, skipping BOTH policies AND triggers. The fix separates these:
   compliance agents skip policy verdicts but still run triggers via
   gate.evaluate_triggers().

Tests construct GenericGate instances directly from inline GateConfig objects
to avoid the dual-module-resolution issue with GATE_CONFIGS import under pytest.
"""

import uuid
from collections import deque
from unittest.mock import patch

import pytest
from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import (
    GateCondition,
    GateConfig,
    GatePolicy,
    GateStatus,
    GateTransition,
    GateTrigger,
)
from lib.gates.engine import GenericGate
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState

# --- Minimal gate configs for testing ---


def _make_custodiet_config(threshold: int = 5) -> GateConfig:
    """Minimal custodiet-like gate config for testing."""
    return GateConfig(
        name="custodiet",
        description="Test compliance gate",
        initial_status=GateStatus.OPEN,
        triggers=[
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="custodiet",
                ),
                transition=GateTransition(
                    reset_ops_counter=True,
                    system_message_template="Compliance verified.",
                ),
            ),
        ],
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="PreToolUse",
                    min_ops_since_open=threshold,
                ),
                verdict="deny",
                message_template="Compliance check required ({ops_since_open} ops).",
            ),
        ],
    )


def _make_critic_config() -> GateConfig:
    """Minimal critic-like gate config for testing."""
    return GateConfig(
        name="critic",
        description="Test critic gate",
        initial_status=GateStatus.OPEN,
        triggers=[
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="critic",
                ),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    reset_ops_counter=True,
                    system_message_template="Critic review complete.",
                ),
            ),
        ],
        policies=[],
    )


@pytest.fixture
def mock_session(tmp_path):
    """Create temporary session state for gate testing."""
    session_id = f"test_dispatch_{uuid.uuid4().hex[:8]}"
    with (
        patch("lib.session_paths.get_session_status_dir", return_value=tmp_path),
        patch("lib.session_state.get_session_status_dir", return_value=tmp_path),
    ):
        state = SessionState.create(session_id)
        state.save()
        yield session_id, state


@pytest.fixture
def test_registry():
    """Set up GateRegistry with test-only gate configs."""
    # Reset registry state
    GateRegistry._gates = {}
    GateRegistry._initialized = False

    gates = [
        GenericGate(_make_custodiet_config()),
        GenericGate(_make_critic_config()),
    ]
    for gate in gates:
        GateRegistry.register(gate)
    GateRegistry._initialized = True

    yield GateRegistry

    # Reset after test
    GateRegistry._gates = {}
    GateRegistry._initialized = False


def _make_router():
    """Create a minimal HookRouter without __init__ side effects."""
    router = HookRouter.__new__(HookRouter)
    router.session_data = {}
    router._execution_timestamps = deque(maxlen=20)
    return router


class TestSubagentGateDispatch:
    """Subagents must have their triggers evaluated (not skipped entirely)."""

    def test_subagent_triggers_run_on_subagent_stop(self, mock_session, test_registry):
        """When a subagent stops, triggers must still fire.

        Before the fix, `if ctx.is_subagent: pass` skipped all gate dispatch
        for subagent sessions. Triggers like critic gate opening on SubagentStop
        never ran.
        """
        session_id, state = mock_session

        # Set up: critic gate has high ops count (should be reset by trigger)
        state.gates["critic"].ops_since_open = 50
        state.gates["critic"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStop",
            subagent_type="critic",
            is_subagent=True,
            raw_input={},
        )

        router = _make_router()

        with (
            patch.object(router, "_run_special_handlers"),
            patch("hooks.router.SessionState.load", return_value=state),
            patch("hooks.router.log_hook_event"),
        ):
            router.execute_hooks(ctx)

        # Critic trigger should have fired and reset ops
        assert state.gates["critic"].ops_since_open == 0

    def test_subagent_triggers_run_on_post_tool_use(self, mock_session, test_registry):
        """PostToolUse in subagent sessions must still increment ops counters."""
        session_id, state = mock_session

        # Ensure gates start with known ops count
        for gs in state.gates.values():
            gs.ops_since_open = 0

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PostToolUse",
            tool_name="Read",
            is_subagent=True,
            raw_input={},
        )

        # Directly test gate method (unit test level)
        for gate in test_registry.get_all_gates():
            gate.on_tool_use(ctx, state)

        # At least one gate should have incremented ops
        total_ops = sum(
            gs.ops_since_open for gs in state.gates.values() if gs.status == GateStatus.OPEN
        )
        assert total_ops > 0


class TestComplianceSubagentBypass:
    """Compliance subagents must bypass policies but still run triggers."""

    def test_compliance_agent_runs_triggers(self, mock_session, test_registry):
        """Compliance agents (hydrator, custodiet) must still run triggers.

        Before the fix, compliance agents got GateResult.allow() immediately
        and triggers never ran.
        """
        session_id, state = mock_session

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="prompt-hydrator",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # The key assertion: compliance agents should NOT be DENIED
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    def test_compliance_agent_cannot_be_denied(self, mock_session, test_registry):
        """Compliance agents must never receive DENY verdicts from policies.

        Even if custodiet's ops threshold is exceeded, a compliance agent
        calling tools should not be blocked.
        """
        session_id, state = mock_session

        # Set up: custodiet gate has exceeded threshold
        state.gates["custodiet"].ops_since_open = 100
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            is_subagent=True,
            subagent_type="aops-core:custodiet",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Compliance agent must never be denied
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    def test_non_compliance_subagent_can_be_denied(self, mock_session, test_registry):
        """Non-compliance subagents should still be subject to policies."""
        session_id, state = mock_session

        # Set up: custodiet gate has exceeded threshold
        state.gates["custodiet"].ops_since_open = 100
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            is_subagent=True,
            subagent_type="Explore",  # NOT a compliance agent
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Non-compliance subagent CAN be denied
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_compliance_check_requires_is_subagent(self, mock_session, test_registry):
        """is_compliance_agent must require ctx.is_subagent=True.

        Before the fix, a main session with hydrator_active could accidentally
        get compliance bypass. The fix adds `ctx.is_subagent and (...)`.
        """
        session_id, state = mock_session

        # Set hydrator_active in state (would have triggered bypass before fix)
        state.state["hydrator_active"] = True
        state.gates["custodiet"].ops_since_open = 100
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            is_subagent=False,  # Main session, NOT a subagent
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Main session MUST be subject to policies (DENY expected)
        assert result is not None
        assert result.verdict == GateVerdict.DENY


class TestEvaluateTriggersMethod:
    """Test the new evaluate_triggers() public method on GenericGate."""

    def test_evaluate_triggers_exists(self):
        """GenericGate must expose evaluate_triggers() as a public method."""
        gate = GenericGate(_make_custodiet_config())
        assert hasattr(gate, "evaluate_triggers")
        assert callable(gate.evaluate_triggers)

    def test_evaluate_triggers_runs_only_triggers(self, mock_session):
        """evaluate_triggers() must run triggers but NOT policies."""
        session_id, state = mock_session

        # Set up high ops so policies WOULD fire
        state.gates["custodiet"].ops_since_open = 100
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            raw_input={},
        )

        gate = GenericGate(_make_custodiet_config())

        # evaluate_triggers should NOT return a DENY (that's policies)
        result = gate.evaluate_triggers(ctx, state)
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    def test_check_evaluates_both_triggers_and_policies(self, mock_session):
        """check() should evaluate BOTH triggers AND policies (contrast with evaluate_triggers)."""
        session_id, state = mock_session

        state.gates["custodiet"].ops_since_open = 100
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            raw_input={},
        )

        gate = GenericGate(_make_custodiet_config())

        # check() evaluates both triggers AND policies -> should DENY
        result = gate.check(ctx, state)
        assert result is not None
        assert result.verdict == GateVerdict.DENY


class TestReadOnlyToolExclusion:
    """read_only tools must be excluded from custodiet threshold."""

    def test_read_only_category_excluded(self, mock_session):
        """Tools in excluded categories should not trigger policies."""
        config = GateConfig(
            name="custodiet_excl",
            description="Test gate with category exclusion",
            initial_status=GateStatus.OPEN,
            triggers=[],
            policies=[
                GatePolicy(
                    condition=GateCondition(
                        hook_event="PreToolUse",
                        min_ops_since_open=5,
                        excluded_tool_categories=["always_available", "read_only"],
                    ),
                    verdict="deny",
                    message_template="Blocked.",
                ),
            ],
        )
        gate = GenericGate(config)
        session_id, state = mock_session

        state.gates["custodiet_excl"] = state.gates["custodiet"].model_copy()
        state.gates["custodiet_excl"].ops_since_open = 100
        state.gates["custodiet_excl"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Read",  # Should be in read_only category
            is_subagent=False,
            raw_input={},
        )

        # Mock get_tool_category to return "read_only" for Read
        with patch("hooks.gate_config.get_tool_category", return_value="read_only"):
            result = gate.check(ctx, state)

        # Read tool should not be denied
        if result is not None:
            assert result.verdict != GateVerdict.DENY


# =============================================================================
# aops-55bcf1a2: Fix gates blocking subagent tool calls (5 interacting bugs)
# =============================================================================


class TestSubagentStartHandler:
    """Bug 1: _call_gate_method must route SubagentStart to gate.on_subagent_start()."""

    def test_call_gate_method_routes_subagent_start(self, mock_session, test_registry):
        """SubagentStart must be dispatched to gate.on_subagent_start(), not return None."""
        session_id, state = mock_session

        # Custodiet trigger matches SubagentStart with subagent_type=custodiet
        state.gates["custodiet"].ops_since_open = 50
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStart",
            subagent_type="custodiet",
            is_subagent=False,  # Main agent context
            raw_input={},
        )

        router = _make_router()
        with (
            patch.object(router, "_run_special_handlers"),
            patch("hooks.router.SessionState.load", return_value=state),
            patch("hooks.router.log_hook_event"),
        ):
            router.execute_hooks(ctx)

        # Trigger should have fired and reset ops counter
        assert state.gates["custodiet"].ops_since_open == 0

    def test_on_subagent_start_method_exists(self):
        """GenericGate must have on_subagent_start method."""
        gate = GenericGate(_make_custodiet_config())
        assert hasattr(gate, "on_subagent_start")
        assert callable(gate.on_subagent_start)

    def test_on_subagent_start_evaluates_triggers(self, mock_session):
        """on_subagent_start must evaluate triggers (same as on_subagent_stop)."""
        session_id, state = mock_session

        state.gates["custodiet"].ops_since_open = 50
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStart",
            subagent_type="custodiet",
            raw_input={},
        )

        gate = GenericGate(_make_custodiet_config())
        result = gate.on_subagent_start(ctx, state)

        # Trigger should fire and reset ops
        assert state.gates["custodiet"].ops_since_open == 0
        assert result is not None


class TestCompliancePostToolUseBypass:
    """Bug 2: Compliance bypass must cover PostToolUse to prevent ops inflation."""

    def test_compliance_agent_post_tool_use_does_not_increment_ops(
        self, mock_session, test_registry
    ):
        """PostToolUse from compliance subagents must not increment ops_since_open.

        Before the fix, custodiet's own Read/Grep calls went through
        gate.on_tool_use() which incremented ops_since_open, inflating the
        counter the custodiet was supposed to reset.
        """
        session_id, state = mock_session

        initial_ops = 10
        state.gates["custodiet"].ops_since_open = initial_ops
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PostToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="aops-core:custodiet",
            raw_input={},
        )

        router = _make_router()
        router._dispatch_gates(ctx, state)

        # Compliance agent's PostToolUse must NOT inflate the ops counter.
        # evaluate_triggers runs but the custodiet trigger resets the counter.
        # Either way, ops should not be higher than initial.
        assert state.gates["custodiet"].ops_since_open <= initial_ops

    def test_non_compliance_agent_post_tool_use_increments_ops(
        self, mock_session, test_registry
    ):
        """PostToolUse from non-compliance subagents should still increment ops."""
        session_id, state = mock_session

        state.gates["custodiet"].ops_since_open = 10
        state.gates["custodiet"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PostToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="Explore",  # NOT a compliance agent
            raw_input={},
        )

        router = _make_router()
        router._dispatch_gates(ctx, state)

        # Non-compliance agent's PostToolUse SHOULD increment ops
        assert state.gates["custodiet"].ops_since_open == 11


class TestSubagentStartStopIsNotSubagent:
    """Bug 3: SubagentStart/SubagentStop must not set is_subagent=True.

    These events fire in the main agent's context ABOUT a subagent.
    They carry agent_id/agent_type metadata which previously caused
    false positive subagent detection.
    """

    def test_subagent_start_not_marked_as_subagent(self):
        """normalize_input must set is_subagent=False for SubagentStart events."""
        router = _make_router()

        raw_input = {
            "hook_event_name": "SubagentStart",
            "session_id": "f4e3f1cb-775c-4aaf-8bf6-4e18a18dad3d",
            "agent_id": "abc1234",
            "agent_type": "custodiet",
        }

        ctx = router.normalize_input(raw_input)

        assert ctx.hook_event == "SubagentStart"
        assert ctx.is_subagent is False
        assert ctx.subagent_type == "custodiet"

    def test_subagent_stop_not_marked_as_subagent(self):
        """normalize_input must set is_subagent=False for SubagentStop events."""
        router = _make_router()

        raw_input = {
            "hook_event_name": "SubagentStop",
            "session_id": "f4e3f1cb-775c-4aaf-8bf6-4e18a18dad3d",
            "agent_id": "abc1234",
            "agent_type": "custodiet",
        }

        ctx = router.normalize_input(raw_input)

        assert ctx.hook_event == "SubagentStop"
        assert ctx.is_subagent is False

    def test_actual_subagent_session_still_detected(self):
        """Regular subagent sessions (short hex IDs) must still be detected."""
        router = _make_router()

        raw_input = {
            "hook_event_name": "PreToolUse",
            "session_id": "aafdeee",  # Short hex = subagent
            "tool_name": "Read",
        }

        ctx = router.normalize_input(raw_input)

        assert ctx.hook_event == "PreToolUse"
        assert ctx.is_subagent is True
