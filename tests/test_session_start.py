"""Test SessionStart gate functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hooks.gate_registry import check_session_start_gate
from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict


@patch("hooks.gate_registry.session_state.save_session_state")
@patch("hooks.gate_registry.session_state.get_or_create_session_state")
@patch("hooks.gate_registry.session_paths.get_session_file_path")
@patch("hooks.gate_registry.session_paths.get_session_status_dir")
@patch("hooks.gate_registry.session_paths.get_session_short_hash")
def test_session_start_message_generation(
    mock_get_hash,
    mock_get_status_dir,
    mock_get_file_path,
    mock_get_or_create,
    mock_save_state,
):
    """Verify SessionStart gate generates the correct info message."""
    mock_get_hash.return_value = "abc12345"
    mock_get_status_dir.return_value = "/tmp/gemini/sessions"

    # Create a mock Path that has exists() return True
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.__str__ = lambda self: "/tmp/gemini/sessions/20260201-16-abc12345.json"
    mock_get_file_path.return_value = mock_path

    # Mock session state functions
    mock_get_or_create.return_value = {"session_id": "session-123", "state": {}}
    mock_save_state.return_value = None

    ctx = HookContext(
        session_id="session-123",
        hook_event="SessionStart",
        raw_input={"session_id": "session-123"},
    )

    result = check_session_start_gate(ctx)

    assert result is not None
    assert isinstance(result, GateResult)
    assert result.verdict == GateVerdict.ALLOW

    # Check message content (now in system_message, not context_injection)
    msg = result.system_message
    assert "Session Started: session-123" in msg
    assert "State File:" in msg
    assert "abc12345" in msg

    # Verify state file was created
    mock_get_or_create.assert_called_once_with("session-123")
    mock_save_state.assert_called_once()


def test_session_start_ignored_for_other_events():
    """Verify gate ignores non-SessionStart events."""
    ctx = HookContext(session_id="session-123", hook_event="PreToolUse", raw_input={})

    result = check_session_start_gate(ctx)
    assert result is None


@patch("hooks.gate_registry.session_state.get_or_create_session_state")
@patch("hooks.gate_registry.session_paths.get_session_file_path")
@patch("hooks.gate_registry.session_paths.get_session_short_hash")
def test_session_start_fails_fast_on_write_error(
    mock_get_hash, mock_get_file_path, mock_get_or_create
):
    """Verify SessionStart gate DENIES session if state file can't be written (P#8 fail-fast)."""
    mock_get_hash.return_value = "abc12345"

    mock_path = MagicMock(spec=Path)
    mock_path.__str__ = lambda self: "/tmp/gemini/sessions/20260201-16-abc12345.json"
    mock_get_file_path.return_value = mock_path

    # Simulate OSError when trying to create state
    mock_get_or_create.side_effect = OSError("Permission denied")

    ctx = HookContext(
        session_id="session-123",
        hook_event="SessionStart",
        raw_input={"session_id": "session-123"},
    )

    result = check_session_start_gate(ctx)

    assert result is not None
    assert result.verdict == GateVerdict.DENY
    assert "FAIL-FAST" in result.system_message
    assert "Permission denied" in result.system_message


@patch("hooks.gate_registry.session_state.save_session_state")
@patch("hooks.gate_registry.session_state.get_or_create_session_state")
@patch("hooks.gate_registry.session_paths.get_session_file_path")
@patch("hooks.gate_registry.session_paths.get_session_short_hash")
def test_session_start_fails_fast_when_file_not_created(
    mock_get_hash, mock_get_file_path, mock_get_or_create, mock_save_state
):
    """Verify SessionStart gate DENIES if file doesn't exist after save."""
    mock_get_hash.return_value = "abc12345"

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False  # File doesn't exist after "save"
    mock_path.__str__ = lambda self: "/tmp/gemini/sessions/20260201-16-abc12345.json"
    mock_get_file_path.return_value = mock_path

    mock_get_or_create.return_value = {"session_id": "session-123", "state": {}}
    mock_save_state.return_value = None

    ctx = HookContext(
        session_id="session-123",
        hook_event="SessionStart",
        raw_input={"session_id": "session-123"},
    )

    result = check_session_start_gate(ctx)

    assert result is not None
    assert result.verdict == GateVerdict.DENY
    assert "FAIL-FAST" in result.system_message
    assert "not created" in result.system_message
