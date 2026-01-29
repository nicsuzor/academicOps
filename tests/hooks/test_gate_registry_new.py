#!/usr/bin/env python3
"""Tests for new gate registry logic."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "aops-core" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from gate_registry import (
    check_custodiet_gate,
    check_hydration_recency_gate,
    post_hydration_trigger,
    post_critic_trigger,
    GateContext,
)

@pytest.fixture
def mock_session_state():
    with patch("gate_registry.session_state") as mock:
        yield mock

@pytest.fixture
def mock_hook_utils():
    with patch("gate_registry.hook_utils") as mock:
        yield mock

@pytest.fixture
def mock_is_mutating():
    with patch("gate_registry.is_mutating_tool") as mock:
        yield mock

class TestCustodietGateDRY:
    def test_uses_shared_is_mutating_tool(self, mock_session_state, mock_is_mutating):
        """Test that check_custodiet_gate uses shared is_mutating_tool."""
        ctx = GateContext("sess1", "PostToolUse", {"tool_name": "write_file"})
        
        # Setup mocks
        mock_is_mutating.return_value = True
        mock_session_state.load_custodiet_state.return_value = {
            "tool_calls_since_compliance": 0
        }
        
        # Run
        check_custodiet_gate(ctx)
        
        # Verify
        mock_is_mutating.assert_called_with("write_file")

    def test_ignores_non_mutating_tool(self, mock_session_state, mock_is_mutating):
        """Test that non-mutating tools are ignored."""
        ctx = GateContext("sess1", "PostToolUse", {"tool_name": "read_file"})
        mock_is_mutating.return_value = False
        
        result = check_custodiet_gate(ctx)
        
        assert result is None
        mock_session_state.save_custodiet_state.assert_not_called()

class TestHydrationRecencyGate:
    def test_blocks_if_turns_zero(self, mock_session_state, mock_hook_utils):
        """Test blocking if turns_since_hydration is 0."""
        ctx = GateContext("sess1", "Stop", {})
        
        # Mock state with turns=0
        mock_session_state.get_or_create_session_state.return_value = {
            "hydration": {"turns_since_hydration": 0}
        }
        mock_hook_utils.make_deny_output.return_value = {"decision": "deny"}
        
        result = check_hydration_recency_gate(ctx)
        
        assert result == {"decision": "deny"}
        mock_hook_utils.make_deny_output.assert_called_with("Plan approved, start execution now")

    def test_allows_if_turns_nonzero(self, mock_session_state):
        """Test allowing if turns_since_hydration is not 0."""
        ctx = GateContext("sess1", "Stop", {})
        
        mock_session_state.get_or_create_session_state.return_value = {
            "hydration": {"turns_since_hydration": 1}
        }
        
        result = check_hydration_recency_gate(ctx)
        assert result is None

    def test_allows_if_not_tracked(self, mock_session_state):
        """Test allowing if metric is missing."""
        ctx = GateContext("sess1", "Stop", {})
        
        mock_session_state.get_or_create_session_state.return_value = {
            "hydration": {}
        }
        
        result = check_hydration_recency_gate(ctx)
        assert result is None

class TestPostHydrationTrigger:
    def test_detects_task_hydrator(self, mock_session_state, mock_hook_utils):
        """Test detecting hydrator via Task tool."""
        ctx = GateContext("sess1", "PostToolUse", {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "prompt-hydrator"}
        })
        
        check_result = post_hydration_trigger(ctx)
        
        mock_session_state.update_hydration_metrics.assert_called_with("sess1", turns_since_hydration=0)
        mock_session_state.clear_hydration_pending.assert_called_with("sess1")
        mock_hook_utils.make_context_output.assert_called()

    def test_detects_delegate_hydrator(self, mock_session_state):
        """Test detecting hydrator via delegate_to_agent."""
        ctx = GateContext("sess1", "PostToolUse", {
            "tool_name": "delegate_to_agent",
            "tool_input": {"agent_name": "prompt-hydrator"}
        })
        
        post_hydration_trigger(ctx)
        
        mock_session_state.update_hydration_metrics.assert_called_with("sess1", turns_since_hydration=0)

    def test_ignores_other_tools(self, mock_session_state):
        """Test ignoring other tools."""
        ctx = GateContext("sess1", "PostToolUse", {
            "tool_name": "read_file"
        })
        
        result = post_hydration_trigger(ctx)
        assert result is None
        mock_session_state.update_hydration_metrics.assert_not_called()

class TestPostCriticTrigger:
    def test_detects_critic_delegate(self, mock_session_state):
        """Test detecting critic via delegate_to_agent."""
        ctx = GateContext("sess1", "PostToolUse", {
            "tool_name": "delegate_to_agent",
            "tool_input": {"agent_name": "critic"}
        })
        
        post_critic_trigger(ctx)
        
        mock_session_state.set_critic_invoked.assert_called_with("sess1", "INVOKED")
        mock_session_state.update_hydration_metrics.assert_called_with("sess1", turns_since_critic=0)

    def test_detects_critic_task(self, mock_session_state):
        """Test detecting critic via Task tool."""
        ctx = GateContext("sess1", "PostToolUse", {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "critic"}
        })
        
        post_critic_trigger(ctx)
        
        mock_session_state.set_critic_invoked.assert_called_with("sess1", "INVOKED")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
