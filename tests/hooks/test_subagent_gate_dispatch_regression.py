"""Regression tests for subagent gate dispatch.

Architecture: subagent tool-call events (PreToolUse/PostToolUse with
is_subagent=True) are invisible to gates — _dispatch_gates() returns None.
Stop/SessionEnd/SubagentStop AND UserPromptSubmit events are exempt from this
bypass so that session-level gates (e.g. IDA) fire even for Claude Code
background agents which get is_subagent=True despite being independent sessions.
Stop/SessionEnd make the gate FIRE; UserPromptSubmit lets a fire-once gate
RE-ARM for the next turn — without it IDA fired once then went silent in
background sessions (regression covered by TestFireOnceRearmInSubagentSession).

Tests construct GenericGate instances directly from inline GateConfig objects
to avoid the dual-module-resolution issue with GATE_CONFIGS import under pytest.
"""

import uuid
from collections import deque
from unittest.mock import patch

import pytest
from hooks.router import HookRouter
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
from lib.hook_context import HookContext
from lib.session_state import SessionState

# --- Minimal gate configs for testing ---


def _make_enforcer_config(threshold: int = 5) -> GateConfig:
    """Minimal enforcer-like gate config for testing."""
    return GateConfig(
        name="enforcer",
        description="Test compliance gate",
        initial_status=GateStatus.OPEN,
        triggers=[
            GateTrigger(
                condition=GateCondition(
                    hook_event="^(SubagentStart|SubagentStop|PostToolUse)$",
                    subagent_type_pattern="enforcer",
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
        GenericGate(_make_enforcer_config()),
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
    """SubagentStart/SubagentStop events fire in main context and run triggers."""

    def test_subagent_triggers_run_on_subagent_stop(self, mock_session, test_registry):
        """SubagentStop fires in the main agent context (is_subagent=False).

        The main agent receives SubagentStop when a subagent completes.
        Gate triggers matching SubagentStop must fire and reset ops.
        """
        session_id, state = mock_session

        # Set up: gate has high ops count (should be reset by trigger)
        state.get_gate("critic").ops_since_open = 50
        state.get_gate("critic").status = GateStatus.OPEN

        # SubagentStop fires in main context — is_subagent=False
        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStop",
            subagent_type="critic",
            is_subagent=False,
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
        assert state.get_gate("critic").ops_since_open == 0

    def test_subagent_triggers_run_on_post_tool_use(self, mock_session, test_registry):
        """PostToolUse in subagent sessions MUST NOT increment ops counters."""
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

        # Unit test level: subagent tool calls MUST NOT increment ops counters
        # (behavior enforced in GenericGate.on_tool_use)
        total_ops = sum(
            gs.ops_since_open for gs in state.gates.values() if gs.status == GateStatus.OPEN
        )
        assert total_ops == 0


class TestSubagentGateBypass:
    """Subagent tool-call events skip gates — _dispatch_gates returns None for PreToolUse/PostToolUse."""

    def test_subagent_session_returns_none(self, mock_session, test_registry):
        """Any subagent session (compliance or not) returns None from _dispatch_gates.

        Gates only evaluate in the main agent session. Subagent tool calls
        are invisible — the parent's Agent tool call is the only operation
        that counts.
        """
        session_id, state = mock_session

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="enforcer",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        assert result is None

    def test_non_compliance_subagent_also_returns_none(self, mock_session, test_registry):
        """Non-compliance subagents are also invisible to gates.

        Even with enforcer threshold exceeded, subagent tool calls
        return None (gates don't evaluate for subagent sessions).
        """
        session_id, state = mock_session

        state.gates["enforcer"].ops_since_open = 100
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            is_subagent=True,
            subagent_type="Explore",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        assert result is None

    def test_main_session_still_subject_to_policies(self, mock_session, test_registry):
        """Main session (is_subagent=False) must still be subject to gate policies."""
        session_id, state = mock_session

        state.gates["enforcer"].ops_since_open = 100
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            is_subagent=False,
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Main session MUST be subject to policies (DENY expected)
        assert result is not None
        assert result.verdict == GateVerdict.DENY


def _make_ida_like_config() -> GateConfig:
    """Minimal fire-once honesty gate: armed CLOSED, fires once per Stop, re-arms on UPS."""
    return GateConfig(
        name="ida_like",
        description="Test fire-once honesty gate",
        initial_status=GateStatus.CLOSED,
        triggers=[
            # Stop while CLOSED -> OPEN (fire-once: don't re-fire on retried Stop).
            GateTrigger(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                ),
                transition=GateTransition(target_status=GateStatus.OPEN),
            ),
            # UserPromptSubmit -> CLOSED (re-arm for the next turn).
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
        policies=[
            GatePolicy(
                condition=GateCondition(
                    hook_event="Stop",
                    current_status=GateStatus.CLOSED,
                ),
                verdict="warn",
                message_template="Before you stop, be honest.",
            ),
        ],
    )


class TestFireOnceRearmInSubagentSession:
    """Regression: a fire-once Stop gate (IDA) must RE-ARM on UserPromptSubmit
    even when is_subagent=True (Claude Code background jobs).

    Bug observed in session 0ff45f86 (2026-06-27): IDA fired once on the first
    Stop, then every later Stop returned `allow` because the UserPromptSubmit
    re-arm event was dropped by the subagent-bypass in _dispatch_gates. The
    exemption let the gate FIRE but not RE-ARM.
    """

    @pytest.fixture
    def ida_registry(self):
        GateRegistry._gates = {}
        GateRegistry._initialized = False
        GateRegistry.register(GenericGate(_make_ida_like_config()))
        GateRegistry._initialized = True
        yield GateRegistry
        GateRegistry._gates = {}
        GateRegistry._initialized = False

    def test_ups_rearm_not_skipped_for_subagent(self, mock_session, ida_registry):
        """UserPromptSubmit in an is_subagent session must reach the gate and re-arm it."""
        session_id, state = mock_session

        # Gate already OPEN (it fired on a previous Stop this turn).
        state.get_gate("ida_like").status = GateStatus.OPEN

        ups_ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="UserPromptSubmit",
            is_subagent=True,  # background job: everything is flagged is_subagent
            raw_input={"prompt": "show me the table"},
        )

        router = _make_router()
        router._dispatch_gates(ups_ctx, state)

        # Before the fix: _dispatch_gates returned None for UPS, status stayed OPEN.
        # After the fix: the re-arm trigger runs -> CLOSED, ready to fire next Stop.
        assert state.get_gate("ida_like").status == GateStatus.CLOSED

    def test_full_fire_rearm_fire_cycle_in_subagent_session(self, mock_session, ida_registry):
        """End-to-end: fire on Stop -> re-arm on UPS -> fire again on next Stop."""
        session_id, state = mock_session
        router = _make_router()

        def run(hook_event, **kw):
            ctx = HookContext(
                session_id=session_id,
                trace_id=None,
                hook_event=hook_event,
                is_subagent=True,
                raw_input=kw.get("raw_input", {}),
            )
            return router._dispatch_gates(ctx, state)

        # Armed (CLOSED) — in production this comes from initial_status=CLOSED;
        # the minimal unit SessionState doesn't seed config initial_status, so
        # set it explicitly to model the armed-at-session-start state.
        state.get_gate("ida_like").status = GateStatus.CLOSED

        # Turn 1 Stop: fires (warn), then opens (fire-once).
        r1 = run("Stop")
        assert r1 is not None and r1.verdict == GateVerdict.WARN
        assert state.get_gate("ida_like").status == GateStatus.OPEN

        # New user prompt: re-arms (this is the line that was being dropped).
        run("UserPromptSubmit", raw_input={"prompt": "next question"})
        assert state.get_gate("ida_like").status == GateStatus.CLOSED

        # Turn 2 Stop: fires AGAIN (the behaviour that was silently lost).
        r2 = run("Stop")
        assert r2 is not None and r2.verdict == GateVerdict.WARN


class TestEvaluateTriggersMethod:
    """Test the new evaluate_triggers() public method on GenericGate."""

    def test_evaluate_triggers_exists(self):
        """GenericGate must expose evaluate_triggers() as a public method."""
        gate = GenericGate(_make_enforcer_config())
        assert hasattr(gate, "evaluate_triggers")
        assert callable(gate.evaluate_triggers)

    def test_evaluate_triggers_runs_only_triggers(self, mock_session):
        """evaluate_triggers() must run triggers but NOT policies."""
        session_id, state = mock_session

        # Set up high ops so policies WOULD fire
        state.gates["enforcer"].ops_since_open = 100
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            raw_input={},
        )

        gate = GenericGate(_make_enforcer_config())

        # evaluate_triggers should NOT return a DENY (that's policies)
        result = gate.evaluate_triggers(ctx, state)
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    def test_check_evaluates_both_triggers_and_policies(self, mock_session):
        """check() should evaluate BOTH triggers AND policies (contrast with evaluate_triggers)."""
        session_id, state = mock_session

        state.gates["enforcer"].ops_since_open = 100
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Write",
            raw_input={},
        )

        gate = GenericGate(_make_enforcer_config())

        # check() evaluates both triggers AND policies -> should DENY
        result = gate.check(ctx, state)
        assert result is not None
        assert result.verdict == GateVerdict.DENY


class TestReadOnlyToolExclusion:
    """read_only tools must be excluded from enforcer threshold."""

    def test_read_only_category_excluded(self, mock_session):
        """Tools in excluded categories should not trigger policies."""
        config = GateConfig(
            name="enforcer_excl",
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

        state.gates["enforcer_excl"] = state.gates["enforcer"].model_copy()
        state.gates["enforcer_excl"].ops_since_open = 100
        state.gates["enforcer_excl"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PreToolUse",
            tool_name="Read",  # Should be in read_only category
            is_subagent=False,
            raw_input={},
        )

        # Mock get_tool_category to return "read_only" for Read. Patch it where
        # the gate's check() path looks it up (lib.gates.engine) — that binding
        # governs excluded_tool_categories matching, not the gate_config name.
        with patch("lib.gates.engine.get_tool_category", return_value="read_only"):
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

        # Enforcer trigger matches SubagentStart with subagent_type=enforcer
        state.gates["enforcer"].ops_since_open = 50
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStart",
            subagent_type="enforcer",
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
        assert state.gates["enforcer"].ops_since_open == 0

    def test_on_subagent_start_method_exists(self):
        """GenericGate must have on_subagent_start method."""
        gate = GenericGate(_make_enforcer_config())
        assert hasattr(gate, "on_subagent_start")
        assert callable(gate.on_subagent_start)

    def test_on_subagent_start_evaluates_triggers(self, mock_session):
        """on_subagent_start must evaluate triggers (same as on_subagent_stop)."""
        session_id, state = mock_session

        state.gates["enforcer"].ops_since_open = 50
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="SubagentStart",
            subagent_type="enforcer",
            raw_input={},
        )

        gate = GenericGate(_make_enforcer_config())
        result = gate.on_subagent_start(ctx, state)

        # Trigger should fire and reset ops
        assert state.gates["enforcer"].ops_since_open == 0
        assert result is not None


class TestSubagentPostToolUseBypass:
    """Subagent PostToolUse is invisible to gates — ops counters unchanged."""

    def test_subagent_post_tool_use_does_not_change_ops(self, mock_session, test_registry):
        """PostToolUse from any subagent returns None — ops counter unchanged.

        Gates don't evaluate for subagent sessions, so neither compliance
        nor non-compliance subagent tool calls affect ops counters.
        """
        session_id, state = mock_session

        initial_ops = 10
        state.gates["enforcer"].ops_since_open = initial_ops
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PostToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="aops-core:enforcer",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Subagent sessions return None — ops unchanged
        assert result is None
        assert state.gates["enforcer"].ops_since_open == initial_ops

    def test_non_compliance_subagent_post_tool_use_also_unchanged(
        self, mock_session, test_registry
    ):
        """PostToolUse from non-compliance subagents also returns None."""
        session_id, state = mock_session

        initial_ops = 10
        state.gates["enforcer"].ops_since_open = initial_ops
        state.gates["enforcer"].status = GateStatus.OPEN

        ctx = HookContext(
            session_id=session_id,
            trace_id=None,
            hook_event="PostToolUse",
            tool_name="Read",
            is_subagent=True,
            subagent_type="Explore",
            raw_input={},
        )

        router = _make_router()
        result = router._dispatch_gates(ctx, state)

        # Subagent sessions return None — ops unchanged
        assert result is None
        assert state.gates["enforcer"].ops_since_open == initial_ops


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
            "agent_type": "enforcer",
        }

        ctx = router.normalize_input(raw_input)

        assert ctx.hook_event == "SubagentStart"
        assert ctx.is_subagent is False
        assert ctx.subagent_type == "enforcer"

    def test_subagent_stop_not_marked_as_subagent(self):
        """normalize_input must set is_subagent=False for SubagentStop events."""
        router = _make_router()

        raw_input = {
            "hook_event_name": "SubagentStop",
            "session_id": "f4e3f1cb-775c-4aaf-8bf6-4e18a18dad3d",
            "agent_id": "abc1234",
            "agent_type": "enforcer",
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
