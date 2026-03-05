"""Tests for custodiet countdown warning feature.

Tests the subtle countdown warning that appears before the custodiet
threshold is reached, giving agents advance notice to run compliance checks.
"""

from __future__ import annotations

import pytest
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gate_types import CountdownConfig, GateConfig
from lib.gates.engine import GenericGate
from lib.session_state import SessionState


class TestCountdownConfig:
    """Test CountdownConfig data model."""

    def test_default_values(self) -> None:
        """CountdownConfig has sensible defaults."""
        config = CountdownConfig(threshold=15)
        assert config.start_before == 5
        assert config.metric == "ops_since_open"
        assert config.threshold == 15
        assert "remaining" in config.message_template
        assert "threshold" in config.message_template or "operations" in config.message_template

    def test_custom_values(self) -> None:
        """CountdownConfig accepts custom values."""
        config = CountdownConfig(
            start_before=3,
            threshold=10,
            message_template="Only {remaining} left!",
            metric="custom_metric",
        )
        assert config.start_before == 3
        assert config.threshold == 10
        assert config.message_template == "Only {remaining} left!"
        assert config.metric == "custom_metric"


class TestCountdownEvaluation:
    """Test countdown evaluation in GenericGate."""

    @pytest.fixture
    def gate_with_countdown(self) -> GenericGate:
        """Create a gate with countdown config."""
        config = GateConfig(
            name="test_gate",
            description="Test gate with countdown",
            countdown=CountdownConfig(
                start_before=5,
                threshold=15,
                message_template="◇ {remaining} turns left before check required.",
            ),
        )
        return GenericGate(config)

    @pytest.fixture
    def session_state(self) -> SessionState:
        """Create a mock session state."""
        return SessionState.create("test-session-countdown")

    @pytest.fixture
    def hook_context(self) -> HookContext:
        """Create a mock hook context for PreToolUse."""
        return HookContext(
            session_id="test-session-countdown",
            hook_event="PreToolUse",
            tool_name="Edit",
        )

    def test_no_countdown_before_window(
        self,
        gate_with_countdown: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """No countdown message when ops_since_open < start_at (threshold - start_before)."""
        # Set ops to 5 (threshold=15, start_before=5, so window starts at 10)
        gate_state = session_state.get_gate("test_gate")
        gate_state.ops_since_open = 5

        result = gate_with_countdown._evaluate_countdown(hook_context, session_state)
        assert result is None

    def test_countdown_in_window(
        self,
        gate_with_countdown: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """Countdown message appears when in the window (start_at <= ops < threshold)."""
        gate_state = session_state.get_gate("test_gate")
        gate_state.ops_since_open = 12  # In window: 10 <= 12 < 15

        result = gate_with_countdown._evaluate_countdown(hook_context, session_state)
        assert result is not None
        assert result.verdict == GateVerdict.ALLOW  # Informational, not blocking
        assert "3 turns left" in result.system_message

    def test_countdown_at_threshold_boundary(
        self,
        gate_with_countdown: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """Countdown at exact start of window (ops == threshold - start_before)."""
        gate_state = session_state.get_gate("test_gate")
        gate_state.ops_since_open = 10  # Exactly at window start

        result = gate_with_countdown._evaluate_countdown(hook_context, session_state)
        assert result is not None
        assert "5 turns left" in result.system_message

    def test_no_countdown_at_threshold(
        self,
        gate_with_countdown: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """No countdown when at or past threshold (policy handles this)."""
        gate_state = session_state.get_gate("test_gate")
        gate_state.ops_since_open = 15  # At threshold

        result = gate_with_countdown._evaluate_countdown(hook_context, session_state)
        assert result is None

    def test_no_countdown_without_config(
        self, session_state: SessionState, hook_context: HookContext
    ) -> None:
        """No countdown when gate has no countdown config."""
        config = GateConfig(
            name="no_countdown_gate",
            description="Gate without countdown",
        )
        gate = GenericGate(config)

        gate_state = session_state.get_gate("no_countdown_gate")
        gate_state.ops_since_open = 12

        result = gate._evaluate_countdown(hook_context, session_state)
        assert result is None


class TestCountdownIntegration:
    """Integration tests for countdown with full gate check flow."""

    @pytest.fixture
    def custodiet_like_gate(self) -> GenericGate:
        """Create a gate similar to custodiet with countdown."""
        from lib.gate_types import GateCondition, GatePolicy

        config = GateConfig(
            name="custodiet_test",
            description="Custodiet-like gate for testing",
            countdown=CountdownConfig(
                start_before=5,
                threshold=15,
                message_template="◇ {remaining} turns until check required.",
            ),
            policies=[
                GatePolicy(
                    condition=GateCondition(
                        hook_event="PreToolUse",
                        min_ops_since_open=15,
                    ),
                    verdict="deny",
                    message_template="Blocked: threshold reached",
                ),
            ],
        )
        return GenericGate(config)

    @pytest.fixture
    def session_state(self) -> SessionState:
        """Create a mock session state."""
        return SessionState.create("test-session-integration")

    @pytest.fixture
    def hook_context(self) -> HookContext:
        """Create a mock hook context for PreToolUse."""
        return HookContext(
            session_id="test-session-integration",
            hook_event="PreToolUse",
            tool_name="Edit",
        )

    def test_countdown_appears_before_block(
        self,
        custodiet_like_gate: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """Countdown message appears in check() result before threshold."""
        gate_state = session_state.get_gate("custodiet_test")
        gate_state.ops_since_open = 12

        result = custodiet_like_gate.check(hook_context, session_state)
        assert result is not None
        assert result.verdict == GateVerdict.ALLOW
        assert "3 turns until check required" in result.system_message

    def test_policy_blocks_at_threshold(
        self,
        custodiet_like_gate: GenericGate,
        session_state: SessionState,
        hook_context: HookContext,
    ) -> None:
        """Policy blocks at threshold, no countdown (not needed)."""
        gate_state = session_state.get_gate("custodiet_test")
        gate_state.ops_since_open = 15

        result = custodiet_like_gate.check(hook_context, session_state)
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        # Policy message, not countdown
        assert "Blocked: threshold reached" in result.system_message

    def test_countdown_includes_temp_path_when_available(
        self, session_state: SessionState, hook_context: HookContext
    ) -> None:
        """Countdown message includes temp_path when configured and available."""
        from lib.gate_types import GateCondition, GatePolicy

        # Create gate with template that includes temp_path
        config = GateConfig(
            name="path_test_gate",
            description="Gate with temp_path in countdown",
            countdown=CountdownConfig(
                start_before=5,
                threshold=15,
                message_template="◇ {remaining} turns left. File: `{temp_path}`",
            ),
            policies=[
                GatePolicy(
                    condition=GateCondition(
                        hook_event="PreToolUse",
                        min_ops_since_open=15,
                    ),
                    verdict="deny",
                    message_template="Blocked",
                ),
            ],
        )
        gate = GenericGate(config)

        # Set ops to be in countdown window
        gate_state = session_state.get_gate("path_test_gate")
        gate_state.ops_since_open = 12
        gate_state.metrics["temp_path"] = "/tmp/test_compliance.json"

        result = gate.check(hook_context, session_state)
        assert result is not None
        assert result.verdict == GateVerdict.ALLOW
        assert "3 turns left" in result.system_message
        assert "/tmp/test_compliance.json" in result.system_message

    def test_countdown_computes_temp_path_deterministically(
        self, session_state: SessionState, hook_context: HookContext
    ) -> None:
        """Countdown should compute temp_path using get_gate_file_path when not in metrics.

        Bug: aops-d3b46a51
        Previously, countdown showed "(not available)" because temp_path was only
        set when the policy fired (at threshold). The countdown fires BEFORE
        threshold, so temp_path was never set.

        Fix: Compute temp_path deterministically using get_gate_file_path() so
        agents know the compliance file path in advance.
        """
        from lib.gate_types import GateCondition, GatePolicy

        # Create gate with temp_path in countdown template (like custodiet)
        config = GateConfig(
            name="custodiet",  # Use actual gate name for path computation
            description="Gate with temp_path in countdown",
            countdown=CountdownConfig(
                start_before=5,
                threshold=15,
                message_template="◇ {remaining} turns left. Run check with: `{temp_path}`",
            ),
            policies=[
                GatePolicy(
                    condition=GateCondition(
                        hook_event="PreToolUse",
                        min_ops_since_open=15,
                    ),
                    verdict="deny",
                    message_template="Blocked",
                ),
            ],
        )
        gate = GenericGate(config)

        # Set ops to be in countdown window
        gate_state = session_state.get_gate("custodiet")
        gate_state.ops_since_open = 12
        # NOTE: temp_path is NOT set in metrics - this is the bug condition

        result = gate.check(hook_context, session_state)
        assert result is not None
        assert result.verdict == GateVerdict.ALLOW
        assert "3 turns left" in result.system_message
        # Should NOT show "(not available)" - should compute path deterministically
        assert "(not available)" not in result.system_message
        # Should show a valid file path (contains session hash and gate name)
        assert "custodiet.md" in result.system_message
