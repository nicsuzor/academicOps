"""Test Strict Hydration Gate functionality."""

import pytest
from unittest.mock import MagicMock, patch
from hooks.gate_registry import (
    check_hydration_gate,
    GateContext,
    HYDRATION_TEMP_CATEGORY,
)
from lib.gate_model import GateResult, GateVerdict


@patch("hooks.gate_registry._hydration_is_subagent_session")
@patch("hooks.gate_registry.session_state.is_hydrator_active")
@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
@patch.dict("os.environ", {"HYDRATION_MODE": "block"})
def test_strict_hydration(mock_get_temp_dir, mock_is_pending, mock_is_hydrator_active, mock_is_subagent):
    """Verify hydration block behavior."""
    mock_get_temp_dir.return_value = "/tmp/hydrator"
    mock_is_pending.return_value = True
    mock_is_hydrator_active.return_value = False
    mock_is_subagent.return_value = False

    # 1. Block ReadFile (previously allowed)
    ctx = GateContext(
        "s1",
        "PreToolUse",
        {"tool_name": "read_file", "tool_input": {"file_path": "/etc/hosts"}},
    )
    result = check_hydration_gate(ctx)
    assert result is not None
    assert result.verdict == GateVerdict.DENY  # Should block now

    # 2. Block ListDir
    ctx = GateContext(
        "s1",
        "PreToolUse",
        {"tool_name": "list_dir", "tool_input": {"DirectoryPath": "/"}},
    )
    result = check_hydration_gate(ctx)
    assert result is not None
    assert result.verdict == GateVerdict.DENY

    # 3. Allow Hydrator Activation (activate_skill)
    ctx = GateContext(
        "s1",
        "PreToolUse",
        {"tool_name": "activate_skill", "tool_input": {"name": "prompt-hydrator"}},
    )
    result = check_hydration_gate(ctx)
    assert result is None  # Allowed

    # 4. Allow Writing to Hydration Temp File (Manual creation)
    ctx = GateContext(
        "s1",
        "PreToolUse",
        {
            "tool_name": "write_to_file",
            "tool_input": {"TargetFile": "/tmp/hydrator/plan.md", "CodeContent": "foo"},
        },
    )
    result = check_hydration_gate(ctx)
    assert result is None  # Allowed (Permitted write)

    # 5. Allow Reading from Hydration Temp File (Gemini hydration attempt)
    ctx = GateContext(
        "s1",
        "PreToolUse",
        {
            "tool_name": "read_file",
            "tool_input": {"file_path": "/tmp/hydrator/plan.md"},
        },
    )
    result = check_hydration_gate(ctx)
    assert result is None  # Allowed


@patch("hooks.gate_registry._hydration_is_subagent_session")
@patch("hooks.gate_registry.session_state.is_hydrator_active")
@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
def test_hydration_bypass_when_not_pending(mock_get_temp_dir, mock_is_pending, mock_is_hydrator_active, mock_is_subagent):
    mock_get_temp_dir.return_value = "/tmp/hydrator"
    mock_is_pending.return_value = False
    mock_is_hydrator_active.return_value = False
    mock_is_subagent.return_value = False
    ctx = GateContext("s1", "PreToolUse", {"tool_name": "read_file"})
    result = check_hydration_gate(ctx)
    assert result is None


@patch("hooks.gate_registry._hydration_is_subagent_session")
@patch("hooks.gate_registry.session_state.is_hydrator_active")
@patch("hooks.gate_registry.session_state.load_session_state")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
@patch.dict("os.environ", {"HYDRATION_GATE_MODE": "block"})
def test_fresh_session_no_state_allows_tools(
    mock_get_temp_dir, mock_load_state, mock_is_hydrator_active, mock_is_subagent
):
    """Fresh session (no state file) should NOT error with STATE ERROR.

    After compact/resume or on new sessions, session state may not exist.
    The gate should handle this gracefully instead of blocking with STATE ERROR.

    Regression test for: aops-fed7c6cf
    """
    mock_get_temp_dir.return_value = "/tmp/hydrator"
    mock_load_state.return_value = None  # No session state file exists
    mock_is_hydrator_active.return_value = False
    mock_is_subagent.return_value = False

    ctx = GateContext(
        "fresh-session-123",
        "PreToolUse",
        {"tool_name": "Read", "tool_input": {"file_path": "/some/file.py"}},
    )
    result = check_hydration_gate(ctx)

    # Should NOT return a STATE ERROR
    if result is not None:
        assert "STATE ERROR" not in str(result.context_injection), \
            "Fresh session should not get STATE ERROR"
        # It's okay to block/warn for other reasons, just not STATE ERROR


@patch("hooks.gate_registry._hydration_is_subagent_session")
@patch("hooks.gate_registry.session_state.is_hydrator_active")
@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.session_state.load_session_state")
def test_hydration_bypass_when_turns_since_hydration_zero(
    mock_load_state, mock_is_pending, mock_is_hydrator_active, mock_is_subagent
):
    """Bypass hydration gate if turns_since_hydration == 0.

    When the hydrator has just completed (turns_since_hydration == 0),
    subsequent tool calls in the same turn should be allowed even if
    hydration_pending hasn't been cleared yet due to timing/ordering.

    This addresses UX friction where multiple tool calls after hydration
    were blocked unnecessarily.

    Related: aops-bb33a3b3
    """
    mock_is_pending.return_value = True  # hydration_pending is still True
    mock_is_hydrator_active.return_value = False
    mock_is_subagent.return_value = False
    # Session state indicates hydration just completed (turns_since_hydration == 0)
    mock_load_state.return_value = {
        "hydration": {"turns_since_hydration": 0}
    }

    ctx = GateContext(
        "s1",
        "PreToolUse",
        {"tool_name": "Read", "tool_input": {"file_path": "/some/file.py"}},
    )
    result = check_hydration_gate(ctx)

    # Should bypass gate (return None) because hydration just completed
    assert result is None, "Should bypass gate when turns_since_hydration == 0"


@patch("hooks.gate_registry._hydration_is_subagent_session")
@patch("hooks.gate_registry.session_state.is_hydrator_active")
@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.session_state.load_session_state")
@patch.dict("os.environ", {"HYDRATION_GATE_MODE": "block"})
def test_hydration_blocks_when_turns_since_hydration_negative(
    mock_load_state, mock_is_pending, mock_is_hydrator_active, mock_is_subagent
):
    """Block hydration gate if turns_since_hydration == -1 (never hydrated).

    When the session has never been hydrated (turns_since_hydration == -1),
    the gate should still block tool calls that require hydration.

    Related: aops-bb33a3b3
    """
    mock_is_pending.return_value = True
    mock_is_hydrator_active.return_value = False
    mock_is_subagent.return_value = False
    # Session state indicates never hydrated
    mock_load_state.return_value = {
        "hydration": {"turns_since_hydration": -1},
        "state": {"hydration_pending": True}
    }

    ctx = GateContext(
        "s1",
        "PreToolUse",
        {"tool_name": "Read", "tool_input": {"file_path": "/some/file.py"}},
    )
    result = check_hydration_gate(ctx)

    # Should block because hydration hasn't happened yet
    assert result is not None, "Should block when turns_since_hydration == -1"
    assert result.verdict == GateVerdict.DENY
