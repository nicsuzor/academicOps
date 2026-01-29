"""Test SessionStart gate functionality."""

import json
import pytest
from unittest.mock import MagicMock, patch
from hooks.gate_registry import check_session_start_gate, GateContext
from lib.gate_model import GateResult, GateVerdict


@patch("hooks.gate_registry.session_paths.get_session_status_dir")
@patch("hooks.gate_registry.session_paths.get_session_short_hash")
def test_session_start_message_generation(mock_get_hash, mock_get_status_dir):
    """Verify SessionStart gate generates the correct info message."""
    mock_get_hash.return_value = "abc12345"
    mock_get_status_dir.return_value = "/tmp/gemini/sessions"

    ctx = GateContext(
        session_id="session-123",
        event_name="SessionStart",
        input_data={"session_id": "session-123"},
    )

    result = check_session_start_gate(ctx)

    assert result is not None
    assert isinstance(result, GateResult)
    assert result.verdict == GateVerdict.ALLOW

    # Check message content
    msg = result.context_injection
    assert "Session Started: session-123" in msg
    assert "State File: /tmp/gemini/sessions" in msg
    assert "abc12345" in msg


def test_session_start_ignored_for_other_events():
    """Verify gate ignores non-SessionStart events."""
    ctx = GateContext(session_id="session-123", event_name="PreToolUse", input_data={})

    result = check_session_start_gate(ctx)
    assert result is None
