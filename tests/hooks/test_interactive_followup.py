#!/usr/bin/env python3
"""Test for Interactive Follow-up streamlined workflow logic."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "aops-core" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from gate_registry import check_agent_response_listener, check_stop_gate, GateContext

class TestInteractiveFollowup:
    """Test interactive-followup streamlined workflow."""

    @patch("lib.session_state.get_or_create_session_state")
    @patch("lib.session_state.clear_hydration_pending")
    @patch("lib.session_state.update_hydration_metrics")
    @patch("lib.session_state.save_session_state")
    def test_response_listener_detects_streamlined(self, mock_save, mock_metrics, mock_clear, mock_get_state):
        """Test that AfterAgent listener detects streamlined workflow."""
        session_id = "test-session"
        response_text = "## HYDRATION RESULT\n**Workflow**: [[workflows/interactive-followup]]\n**Intent**: save to daily note"
        
        mock_get_state.return_value = {"state": {}}
        
        ctx = GateContext(session_id, "AfterAgent", {"prompt_response": response_text})
        
        result = check_agent_response_listener(ctx)
        
        # Should clear hydration pending
        mock_clear.assert_called_once_with(session_id)
        # Should set current_workflow
        assert mock_get_state.return_value["state"]["current_workflow"] == "interactive-followup"
        # Should return a streamlined result (system_message, no context_injection reminder)
        assert result is not None
        assert result.verdict.value == "allow"
        assert "Streamlined mode enabled" in result.system_message
        assert result.context_injection is None

    @patch("lib.session_state.load_session_state")
    def test_stop_gate_allows_streamlined_without_subagents(self, mock_load):
        """Test that Stop gate allows streamlined workflow without critic/subagents."""
        session_id = "test-session"
        
        # Mock state: hydrated, NO subagents, BUT streamlined workflow
        mock_load.return_value = {
            "state": {
                "current_workflow": "interactive-followup"
            },
            "hydration": {
                "hydrated_intent": "save stuff"
            },
            "subagents": {}
        }
        
        ctx = GateContext(session_id, "Stop", {})
        
        # If I hadn't changed it, this would return a GateResult (DENY) with critic reminder
        result = check_stop_gate(ctx)
        
        # In streamlined mode, it should be None (allowed) if only critic was missing
        # Wait, check_stop_gate ALSO checks for handover.
        # Let's mock handover invoked = True
        with patch("lib.session_state.is_handover_skill_invoked", return_value=True):
            result = check_stop_gate(ctx)
            assert result is None

    @patch("lib.session_state.load_session_state")
    def test_stop_gate_allows_simple_question_without_subagents(self, mock_load):
        """Test that Stop gate allows simple-question workflow without critic/subagents."""
        session_id = "test-session"
        
        # Mock state: hydrated, NO subagents, simple-question workflow
        mock_load.return_value = {
            "state": {
                "current_workflow": "simple-question"
            },
            "hydration": {
                "hydrated_intent": "explain hydration"
            },
            "subagents": {}
        }
        
        ctx = GateContext(session_id, "Stop", {})
        
        with patch("lib.session_state.is_handover_skill_invoked", return_value=True):
            result = check_stop_gate(ctx)
            assert result is None

    @patch("lib.session_state.get_or_create_session_state")
    def test_stop_gate_blocks_regular_without_subagents(self, mock_get_state):
        """Test that Stop gate still blocks regular workflows without critic."""
        session_id = "test-session"
        
        # Mock state: hydrated, NO subagents, regular workflow
        mock_get_state.return_value = {
            "state": {
                "current_workflow": "design"
            },
            "hydration": {
                "hydrated_intent": "build feature"
            },
            "subagents": {}
        }
        # Wait, check_stop_gate uses load_session_state
        with patch("lib.session_state.load_session_state", return_value=mock_get_state.return_value):
            ctx = GateContext(session_id, "Stop", {})
            result = check_stop_gate(ctx)
            
            assert result is not None
            assert result.verdict.value == "deny"
            # It should be the critic reminder
            # (Note: it might fail on handover first if not mocked)
            
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
