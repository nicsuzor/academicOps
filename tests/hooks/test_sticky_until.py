#!/usr/bin/env python3
"""Unit tests for the sticky_until engine mechanism.

Tests the engine's sticky latch behavior in isolation using minimal
GateConfig objects, independent of the production gate definitions.
"""

import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.gate_types import (  # noqa: E402
    GateCondition,
    GateConfig,
    GateState,
    GateStatus,
    GateTransition,
    GateTrigger,
)
from lib.gates.engine import GenericGate  # noqa: E402
from lib.hook_context import HookContext  # noqa: E402
from lib.session_state import SessionState  # noqa: E402


def _make_sticky_gate() -> GateConfig:
    """Gate that opens with sticky_until on SubagentStop, closes on PostToolUse."""
    return GateConfig(
        name="test_sticky",
        description="Test gate for sticky_until",
        initial_status=GateStatus.CLOSED,
        triggers=[
            # Close on any PostToolUse
            GateTrigger(
                condition=GateCondition(hook_event="PostToolUse"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
            # Open on SubagentStop with sticky_until
            GateTrigger(
                condition=GateCondition(hook_event="SubagentStop"),
                transition=GateTransition(
                    target_status=GateStatus.OPEN,
                    sticky_until=["UserPromptSubmit"],
                ),
            ),
            # Re-arm on UserPromptSubmit
            GateTrigger(
                condition=GateCondition(hook_event="UserPromptSubmit"),
                transition=GateTransition(target_status=GateStatus.CLOSED),
            ),
        ],
    )


@pytest.fixture
def gate():
    return GenericGate(_make_sticky_gate())


@pytest.fixture
def session_state():
    return SessionState.create("test-sticky")


def _ctx(hook_event: str, **kwargs) -> HookContext:
    return HookContext(
        session_id="test-sticky",
        hook_event=hook_event,
        tool_name=kwargs.get("tool_name"),
        tool_input=kwargs.get("tool_input", {}),
    )


class TestStickyUntilBasic:
    def test_transition_sets_sticky(self, gate, session_state):
        """A transition with sticky_until should set gate.sticky=True."""
        state = gate._get_state(session_state)
        assert state.sticky is False

        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)

        assert state.status == GateStatus.OPEN
        assert state.sticky is True
        assert state.sticky_until_events == ["UserPromptSubmit"]

    def test_sticky_suppresses_different_status(self, gate, session_state):
        """While sticky, transitions to a different status are suppressed."""
        state = gate._get_state(session_state)

        # Open with sticky
        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.status == GateStatus.OPEN
        assert state.sticky is True

        # PostToolUse would normally close, but sticky suppresses
        gate.on_tool_use(_ctx("PostToolUse", tool_name="Edit"), session_state)
        assert state.status == GateStatus.OPEN, "Sticky must suppress close transition"
        assert state.sticky is True

    def test_unstick_event_clears_sticky(self, gate, session_state):
        """The designated unstick event should clear the sticky latch."""
        state = gate._get_state(session_state)

        # Open with sticky
        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.sticky is True

        # UPS unsticks
        gate.on_user_prompt(_ctx("UserPromptSubmit"), session_state)
        assert state.sticky is False
        assert state.sticky_until_events == []

    def test_unstick_then_rearm(self, gate, session_state):
        """After unstick, the re-arm trigger should fire normally."""
        state = gate._get_state(session_state)

        # Open with sticky
        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.status == GateStatus.OPEN
        assert state.sticky is True

        # UPS: unstick + re-arm to CLOSED
        gate.on_user_prompt(_ctx("UserPromptSubmit"), session_state)
        assert state.sticky is False
        assert state.status == GateStatus.CLOSED

    def test_multiple_suppressed_transitions(self, gate, session_state):
        """Multiple transitions targeting different status are all suppressed."""
        state = gate._get_state(session_state)

        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.status == GateStatus.OPEN

        # Three close attempts — all suppressed
        for _ in range(3):
            gate.on_tool_use(_ctx("PostToolUse", tool_name="Edit"), session_state)
            assert state.status == GateStatus.OPEN

        # Unstick + re-arm
        gate.on_user_prompt(_ctx("UserPromptSubmit"), session_state)
        assert state.status == GateStatus.CLOSED


class TestStickyUntilEdgeCases:
    def test_same_status_transition_not_suppressed(self, session_state):
        """Transitions to the SAME status should not be suppressed by sticky."""
        config = GateConfig(
            name="test_same",
            description="Test same-status under sticky",
            initial_status=GateStatus.OPEN,
            triggers=[
                GateTrigger(
                    condition=GateCondition(hook_event="SubagentStop"),
                    transition=GateTransition(
                        target_status=GateStatus.OPEN,
                        sticky_until=["UserPromptSubmit"],
                        set_metrics={"marker": True},
                    ),
                ),
                GateTrigger(
                    condition=GateCondition(hook_event="PostToolUse"),
                    transition=GateTransition(
                        target_status=GateStatus.OPEN,
                        set_metrics={"reopened": True},
                    ),
                ),
            ],
        )
        gate = GenericGate(config)
        state = gate._get_state(session_state)

        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.sticky is True
        assert state.metrics.get("marker") is True

        # Same-status transition (OPEN->OPEN) should not be suppressed
        gate.on_tool_use(_ctx("PostToolUse", tool_name="Read"), session_state)
        assert state.metrics.get("reopened") is True
        assert state.status == GateStatus.OPEN

    def test_no_target_status_not_suppressed(self, session_state):
        """Transitions with target_status=None are not suppressed by sticky."""
        config = GateConfig(
            name="test_none",
            description="Test None target under sticky",
            initial_status=GateStatus.OPEN,
            triggers=[
                GateTrigger(
                    condition=GateCondition(hook_event="SubagentStop"),
                    transition=GateTransition(
                        target_status=GateStatus.OPEN,
                        sticky_until=["UserPromptSubmit"],
                    ),
                ),
                GateTrigger(
                    condition=GateCondition(hook_event="PostToolUse"),
                    transition=GateTransition(
                        target_status=None,
                        set_metrics={"side_effect": True},
                    ),
                ),
            ],
        )
        gate = GenericGate(config)
        state = gate._get_state(session_state)

        gate.on_subagent_stop(_ctx("SubagentStop"), session_state)
        assert state.sticky is True

        # None target -> not suppressed, side effect runs
        gate.on_tool_use(_ctx("PostToolUse", tool_name="Read"), session_state)
        assert state.metrics.get("side_effect") is True

    def test_sticky_persists_in_state(self):
        """Sticky fields are part of GateState and survive serialization."""
        state = GateState(
            status=GateStatus.OPEN,
            sticky=True,
            sticky_until_events=["UserPromptSubmit"],
        )
        dumped = state.model_dump()
        restored = GateState(**dumped)
        assert restored.sticky is True
        assert restored.sticky_until_events == ["UserPromptSubmit"]

    def test_default_state_not_sticky(self):
        """New GateState instances default to non-sticky."""
        state = GateState()
        assert state.sticky is False
        assert state.sticky_until_events == []
