"""Test Strict Hydration Gate functionality."""

import pytest
from unittest.mock import MagicMock, patch
from hooks.gate_registry import (
    check_hydration_gate,
    GateContext,
    HYDRATION_TEMP_CATEGORY,
)
from lib.gate_model import GateResult, GateVerdict


@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
def test_strict_hydration(mock_get_temp_dir, mock_is_pending):
    """Verify hydration block behavior."""
    mock_is_pending.return_value = True
    mock_get_temp_dir.return_value = "/tmp/hydrator"

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


@patch("hooks.gate_registry.session_state.is_hydration_pending")
@patch("hooks.gate_registry.hook_utils.get_hook_temp_dir")
def test_hydration_bypass_when_not_pending(mock_get_temp_dir, mock_is_pending):
    mock_is_pending.return_value = False
    ctx = GateContext("s1", "PreToolUse", {"tool_name": "read_file"})
    result = check_hydration_gate(ctx)
    assert result is None
