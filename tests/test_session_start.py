"""Test SessionStart gate functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from session_env_setup import run_session_env_setup


@patch("hooks.gates.session_paths.get_session_short_hash")
@patch("hooks.gates.get_hook_log_path")
@patch("hooks.gates.session_paths.get_session_file_path")
@patch("hooks.gates.GateRegistry.get_all_gates")
def test_session_start_message_generation(
    mock_get_all_gates,
    mock_get_file_path,
    mock_get_log_path,
    mock_get_hash,
):
    """Verify SessionStart gate generates the correct info message."""
    mock_get_hash.return_value = "abc12345"
    mock_get_log_path.return_value = "/tmp/gemini/sessions/hooks.log"

    # Create a mock Path that has exists() return True
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.__str__ = lambda self: "/tmp/gemini/sessions/20260201-16-abc12345.json"
    mock_get_file_path.return_value = mock_path

    # Mock gates to return None (no gate messages)
    mock_get_all_gates.return_value = []

    # Create mock SessionState
    from datetime import datetime

    from lib.session_state import SessionState

    state = SessionState(
        session_id="session-123",
        date=datetime.now().strftime("%Y-%m-%d"),
        started_at=datetime.now().isoformat(),
    )

    ctx = HookContext(
        session_id="session-123",
        hook_event="SessionStart",
        raw_input={"session_id": "session-123"},
    )

    result = run_session_env_setup(ctx, state)

    assert result is not None
    assert isinstance(result, GateResult)
    assert result.verdict == GateVerdict.ALLOW

    # Check system_message has brief user-facing summary
    assert "Session Started: session-123" in result.system_message
    assert "abc12345" in result.system_message
    assert "State File:" in result.system_message
    assert "/tmp/gemini/sessions/20260201-16-abc12345.json" in result.system_message
    assert f"Version: {state.version}" in result.system_message


# TODO: The following tests need to be rewritten for the current gate architecture
# def test_session_start_ignored_for_other_events():
# def test_session_start_fails_fast_on_write_error():
# def test_session_start_fails_fast_when_file_not_created():
