#!/usr/bin/env python3
"""Test for Stop hook hydrator check."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hooks directory to path
HOOKS_DIR = Path(__file__).parent.parent.parent / "aops-core" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from unified_logger import handle_stop

TEST_INPUT = {
    "hook_event": "Stop",
    "logged_at": "2026-01-29T14:15:00+10:00",
    "exit_code": 0,
    "session_id": "2e1ef753-e5a4-4c89-b10c-ea69d7ca5cb9",
    "transcript_path": "/home/nic/.gemini/tmp/6143ee4ec3862b6dfa5984a4cf46317de855d1e5d3628e5658eef2776919e205/chats/session-2026-01-29T04-13-2e1ef753.json",
    "cwd": "/home/nic/.aops/polecat/crew/audre",
    "hook_event_name": "Stop",
    "timestamp": "2026-01-29T04:15:00.243Z",
    "prompt": "update my daily note please",
    "prompt_response": "...",
    "stop_hook_active": False
}

class TestStopHookHydratorCheck:
    """Test Stop hook hydrator check logic."""

    @patch("unified_logger.get_or_create_session_state")
    def test_hydrator_check_triggers(self, mock_get_state):
        """Test that Stop hook validates hydration state."""
        # Mock session state WITHOUT hydration
        mock_get_state.return_value = {
            "session_id": "2e1ef753-e5a4-4c89-b10c-ea69d7ca5cb9",
            "state": {
                "current_workflow": "daily",
                "custodiet_blocked": False
            },
            "subagents": {}
        }

        # The unified_logger.handle_stop should raise ValueError
        # because "hydration" is missing from state
        with pytest.raises(ValueError, match="Required field 'hydration' missing"):
            handle_stop(
                TEST_INPUT["session_id"],
                TEST_INPUT
            )

    @patch("unified_logger.get_or_create_session_state")
    def test_hydrator_check_passes_with_data(self, mock_get_state):
        """Test that Stop hook passes when hydration data is present."""
        # Mock session state WITH hydration
        mock_get_state.return_value = {
            "session_id": "2e1ef753-e5a4-4c89-b10c-ea69d7ca5cb9",
            "state": {
                "current_workflow": "daily",
                "custodiet_blocked": False
            },
            "subagents": {},
            "hydration": {
                "acceptance_criteria": ["Criterion 1"]
            }
        }
        
        # Note: input missing "stop_reason", so it will fail on that next
        # This confirms it PASSED the hydration check
        with pytest.raises(ValueError, match="Required field 'stop_reason' missing"):
             handle_stop(
                TEST_INPUT["session_id"],
                TEST_INPUT
            )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
