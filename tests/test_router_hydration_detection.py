"""
Reproduction test for hydration detection in router.py.

Verifies that router.py correctly detects hydration as completed
given the specific input provided by the user.
"""

import json
from unittest.mock import MagicMock, patch

from hooks.router import HookRouter
from lib.gate_model import GateVerdict


@patch("lib.session_state.clear_hydration_pending")
@patch("lib.session_state.load_session_state")
@patch("lib.session_state.get_or_create_session_state")
def test_router_detects_hydration_completion_from_gemini_input(
    mock_get_state, mock_load_state, mock_clear_pending
):
    """
    Verify that invoking router.py with Gemini AfterTool input
    successfully detects hydration as completed.
    """
    router = HookRouter()

    # User's provided input
    raw_input = {
        "session_id": "7f786eb0-2bd7-4820-b71a-a1c83d11a886",
        "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-02-08T23-31-7f786eb0.json",
        "cwd": "/home/nic/src/academicOps",
        "hook_event_name": "AfterTool",
        "timestamp": "2026-02-08T23:32:10.445Z",
        "tool_name": "prompt-hydrator",
        "tool_input": {
            "query": "Analyze context in /home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/hydrator/hydrate__cev13c9.md"
        },
        "tool_response": {
            "llmContent": [
                {
                    "text": "Subagent 'prompt-hydrator' finished.\nTermination Reason: GOAL\nResult:\n## HYDRATION RESULT\n\n**Intent**: Answer the user's factual question about the current time.\n**Task binding**: No task needed\n\n### Acceptance Criteria\n\n1. The current local time is accurately provided to the user.\n\n### Relevant Context\n\n- The user has posed a direct, factual question requiring a simple answer.\n\n### Execution Plan\n\n1. Retrieve the current local time.\n2. Present the current local time to the user.\n3. Mark the interaction as complete."
                }
            ],
            "returnDisplay": "\nSubagent prompt-hydrator Finished\n\nTermination Reason:\n GOAL\n\nResult:\n## HYDRATION RESULT\n\n**Intent**: Answer the user's factual question about the current time.\n**Task binding**: No task needed\n\n### Acceptance Criteria\n\n1. The current local time is accurately provided to the user.\n\n### Relevant Context\n\n- The user has posed a direct, factual question requiring a simple answer.\n\n### Execution Plan\n\n1. Retrieve the current local time.\n2. Present the current local time to the user.\n3. Mark the interaction as complete.\n"
        }
    }

    # Setup mock session state
    mock_load_state.return_value = {
        "state": {"hydration_pending": True},
        "hydration": {}
    }
    mock_get_state.return_value = {
        "state": {"hydration_pending": True},
        "hydration": {}
    }

    # Normalize input
    ctx = router.normalize_input(raw_input)

    # Execute hooks
    # This should trigger gate_update -> update_gate_state -> _open_gate("hydration")
    # which calls session_state.clear_hydration_pending
    result = router.execute_hooks(ctx)

    # Verify hydration_pending was cleared
    mock_clear_pending.assert_called_once_with(
        "7f786eb0-2bd7-4820-b71a-a1c83d11a886"
    )
    
    # Verify the result message indicates opening
    assert "'hydration' opened" in result.context_injection
