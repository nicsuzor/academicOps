#!/usr/bin/env python3
"""Tests for new gate registry logic."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "aops-core" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from gate_registry import (
    check_hydration_recency_gate,
    post_hydration_trigger,
    post_critic_trigger,
    GateContext,
)
from lib.gate_model import GateResult, GateVerdict

@pytest.fixture
def mock_session_state():
    with patch("gate_registry.session_state") as mock:
        yield mock

@pytest.fixture
def mock_hook_utils():
    with patch("gate_registry.hook_utils") as mock:
        yield mock

class TestHydrationRecencyGate:
    def test_blocks_if_turns_zero(self, mock_session_state, mock_hook_utils):
        """Test blocking if turns_since_hydration is 0."""
        ctx = GateContext("sess1", "Stop", {})
        
        # Mock state with turns=0
        mock_session_state.get_or_create_session_state.return_value = {
            "hydration": {"turns_since_hydration": 0}
        }
        
        result = check_hydration_recency_gate(ctx)
        
        assert isinstance(result, GateResult)
        assert result.verdict == GateVerdict.DENY
        assert "execute the plan" in result.context_injection

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
        assert check_result.verdict == GateVerdict.ALLOW
        assert "invoke the critic" in check_result.context_injection

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